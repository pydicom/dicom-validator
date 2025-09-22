import json
import logging
import sys
from dataclasses import dataclass

from pydicom import config, Sequence, Dataset
from pydicom.multival import MultiValue
from pydicom.valuerep import validate_value

from dicom_validator.spec_reader.condition import (
    ConditionType,
    ConditionOperator,
)
from dicom_validator.validator.dicom_info import DicomInfo
from dicom_validator.validator.error_handler import (
    LoggingResultHandler,
    ValidationResultHandler,
)
from dicom_validator.validator.validation_result import (
    ValidationResult,
    Status,
    TagErrors,
    ErrorCode,
    TagError,
    TagType,
    ErrorScope,
    DicomTag,
)


class DatasetStackItem:
    def __init__(
        self, dataset: Dataset, tag: int | None = None, stack: list[int] | None = None
    ):
        self.dataset = dataset
        self.tag = tag
        self.stack = stack
        if tag is not None:
            if stack is None:
                self.stack = [tag]
            else:
                self.stack = stack[:] + [tag]
        self.unexpected_tags = {
            DicomTag(d.tag, self.stack) for d in dataset if not d.tag.is_private
        }


@dataclass
class FunctionalGroupInfo:
    """Contains information about the currently validated functional groups.
    Contrary to other checks, we have to check both Shared and PerFrame functional
    groups before being able to do the validation.
    """

    shared_results: dict  # the result of the shared group validation
    checked_modules: set  # the names of already validated macro modules

    def clear(self):
        self.shared_results.clear()
        self.checked_modules.clear()

    def combined(
        self, module_name: str, seq_tag: DicomTag, per_frame: TagErrors
    ) -> TagErrors:
        """Return the combined error for errors from shared and per-frame groups
        for the given module.

        Parameters
        ----------
        module_name : str
            The name of the validated macro module.
        seq_tag : DicomTag
            The tag ID of the top-level-sequence tag in the macro
        per_frame : TagErrors
            The errors from validation of the module in the per-frame group.
        """
        result = {}
        shared = self.shared_results.get(module_name, {})
        if not shared and not per_frame:
            # the module is present in both shared and per-frame groups
            # this is an error
            return {
                seq_tag: TagError(
                    code=ErrorCode.TagNotAllowed, scope=ErrorScope.BothFuncGroups
                )
            }
        for tag, error in shared.items():
            # similar tags differ by the functional group parent tag
            per_frame_tag = DicomTag(tag.tag, [0x5200_9230] + tag.parents[1:])
            if per_frame.get(per_frame_tag) == error:
                # if the error appears in both sequences, it is real
                result[tag] = shared[tag]
                del per_frame[per_frame_tag]
            elif error.code == ErrorCode.TagMissing:
                # for missing tags, we also have to check if the error does not appear
                # in the per-frame group because it is part of a missing sequence
                for per_frame_tag in per_frame:
                    if per_frame_tag.tag in [t.tag for t in shared]:
                        result[per_frame_tag] = per_frame[per_frame_tag]
                        del per_frame[per_frame_tag]
                        break
            else:
                # other errors (unexpected tag, missing value) shall always remain
                result[tag] = shared[tag]

        for tag, error in per_frame.items():
            if error.code == ErrorCode.TagMissing:
                # same check as above
                for shared_tag in shared:
                    if shared_tag.tag in [t.tag for t in per_frame]:
                        result[shared_tag] = shared[shared_tag]
                        del shared[shared_tag]
                        break
            else:
                result[tag] = per_frame[tag]
        return result


class InvalidParameterError(Exception):
    pass


class IODValidator:
    def __init__(
        self,
        dataset: Dataset,
        dicom_info: DicomInfo,
        log_level: int = logging.INFO,
        suppress_vr_warnings: bool = False,
        error_handler: ValidationResultHandler | None = None,
    ):
        """Create an IODValidator instance.

        Parameters
        ----------
        dataset : Dataset
            The dataset to be validated.
        dicom_info : dict
            The DICOM information as extracted from the standard.
        log_level : int
            The log level of the used logger.
        suppress_vr_warnings : bool
            If True, skip the VR validation of DICOM tags.
        error_handler : ValidationResultHandler
            Handles errors found during validation.
            Defaults to a handler that logs all errors to the console.
        """
        self._dataset = dataset
        self._dataset_stack = [DatasetStackItem(self._dataset)]
        self._dicom_info = dicom_info
        self._func_group_info = FunctionalGroupInfo({}, set())
        self._suppress_vr_warnings = suppress_vr_warnings
        self.result = ValidationResult()
        self.logger = logging.getLogger("validator")
        self.logger.level = log_level
        if not self.logger.hasHandlers():
            self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.handler = error_handler or LoggingResultHandler(dicom_info, self.logger)

    def validate(self) -> ValidationResult:
        """Validates current dataset.
        All errors are contained in the `ValidationResult` object after execution.
        By default, e.g. if no other handler has been set, all errors are
        logged to the console.
        """
        self.result.reset()
        self.result.sop_class_uid = self._dataset.get("SOPClassUID")
        if not self.result.sop_class_uid:
            self.result.status = Status.MissingSOPClassUID
            self.result.errors = 1
        else:
            if self.result.sop_class_uid not in self._dicom_info.iods:
                self.result.status = Status.UnknownSOPClassUID
                self.result.errors = 1
            else:
                self._validate_sop_class()

        self.handler.handle_validation_result(self.result)
        return self.result

    def _validate_sop_class(self) -> None:
        """Validate the dataset against the current SOP class.
        Record all errors in the `errors` attribute.
        """
        self.handler.handle_validation_start(self.result)
        iod_info = self._dicom_info.iods[self.result.sop_class_uid]
        maybe_existing_modules = self._get_maybe_existing_modules(iod_info["modules"])

        for module_name, module in iod_info["modules"].items():
            self._dataset_stack[-1].tag = module_name
            errors = self._validate_module(
                module, module_name, maybe_existing_modules, iod_info["group_macros"]
            )
            if errors:
                self.result.add_tag_errors(module_name, errors)
                self.result.status = Status.Failed

        if len(self._dataset_stack[-1].unexpected_tags) != 0:
            self.result.add_tag_errors("General", self._unexpected_tag_errors())

    def _validate_module(
        self,
        module: dict[str, dict],
        module_name: str,
        maybe_existing_modules: dict[str, set[DicomTag]],
        group_macros=None,
    ) -> TagErrors:
        """Validate the given module.

        Parameters
        ----------
        module : dict[str, dict]
            Contains the module reference chapter ("ref"), the usage ("use"),
            and optionally the usage condition as a dictionary (see `Condition`).
        module_name : str
            The module name as listed in the standard.
        maybe_existing_modules : dict[str, set[DicomTag]]
            List of module references with contained tags that may be present
            in the dataset. Due to the fact that the same tag may belong to
            different modules, the presence of the module is only guessed at this point,
            and some of them may not actually be present.
        group_macros : dict[str, dict], optional
            The modules allowed in functional group sequences, if the given module
            contains them, otherwise an empty dictionary.
            The keys are the module names, the values the module dicts as described
            for `module`.
            None if `module` itself is a module in a functional group.

        Returns
        -------
        The dictionary of found errors.
        """
        usage = module["use"]
        module_info = self._get_module_info(module["ref"], group_macros)
        condition = module["cond"] if "cond" in module else None
        is_shared = False
        is_per_frame = False
        if group_macros is None:
            if module_name in self._func_group_info.checked_modules:
                # check only one per-frame item
                return {}
            is_shared = self._in_shared_group
            if not is_shared:
                is_per_frame = self._in_per_frame_group

        allowed = True
        scope = ErrorScope.General
        if condition and "F" in condition["type"] and is_shared:
            required, allowed = False, False
            scope = ErrorScope.SharedFuncGroup
        elif condition and "S" in condition["type"] and is_per_frame:
            required, allowed = False, False
            scope = ErrorScope.PerFrameFuncGroup
        elif usage[0] == "M":
            required = True
        elif usage[0] == ConditionType.UserDefined:
            required = False
        elif condition:
            required, allowed = self._object_is_required_or_allowed(condition)
        else:
            required = False

        if required:
            # Always validate required modules.
            # If the module is missing from the dataset the validation
            # should report it as an error.
            result = self._validate_attributes(module_info, False)
            if group_macros is not None:
                return result

            # for functional groups, we need to check both shared and per-frame groups
            # to get a result; a required module should be in only one of these
            if is_shared:
                # just save the result to check together with per-frame groups
                self._func_group_info.shared_results[module_name] = result
                return {}
            if is_per_frame:
                shared_result = self._func_group_info.shared_results.get(module_name)
                if shared_result is not None:
                    seq_tag = self._tag_id(list(module_info.keys())[0])
                    return self._func_group_info.combined(module_name, seq_tag, result)
                return result

        if module["ref"] not in maybe_existing_modules:
            # The module is not present at all in the dataset.
            # No validation is needed.
            return {}

        # At this point the module is __not required__ but it __may be existing__
        # in the dataset.
        # Just "maybe" because multiple modules may have overlapping attributes.
        # So, let's see if it exists "strongly" enough to be considered
        # for further checks.
        if maybe_existing_modules and not self._does_module_strongly_exist(
            module["ref"], maybe_existing_modules
        ):
            return {}

        if not allowed:
            # no special case for functional groups here
            errors = {}
            for tag_id_string in module_info:
                tag_id = self._tag_id(tag_id_string)
                if tag_id.tag in self._dataset_stack[-1].dataset:
                    errors[tag_id] = TagError(code=ErrorCode.TagNotAllowed, scope=scope)
                    self._dataset_stack[-1].unexpected_tags.discard(tag_id)
            return errors
        return self._validate_attributes(module_info, False)

    @property
    def _in_per_frame_group(self):
        return self._dataset_stack[-1].tag == 0x5200_9230

    @property
    def _in_shared_group(self):
        return self._dataset_stack[-1].tag == 0x5200_9229

    def _validate_attributes(self, attributes, report_unexpected_tags) -> TagErrors:
        """Validate the given attributes according to their type.
        Parameters
        ----------
        attributes : dict
            The attributes of a single module to be validated.
        report_unexpected_tags : bool
            If True, tags that are not expected are reported and placed into
            the `errors` dictionary.

        Returns
        -------
        The dictionary of found errors.
        """
        errors = TagErrors()

        for tag_id_string, attribute in attributes.items():
            if tag_id_string == "modules":
                self._validate_func_group_modules(attribute)
            else:
                tag_id = self._tag_id(tag_id_string)
                if (
                    tag_error := self._validate_attribute(tag_id, attribute)
                ) is not None:
                    errors[tag_id] = tag_error
                self._dataset_stack[-1].unexpected_tags.discard(tag_id)

                if "items" in attribute:
                    data_elem = self._dataset_stack[-1].dataset.get_item(tag_id.tag)
                    if data_elem is None:
                        continue
                    if data_elem.VR != "SQ":
                        raise RuntimeError(f"Not a sequence: {data_elem}")
                    for sq_item_dataset in data_elem.value:
                        self._dataset_stack.append(
                            DatasetStackItem(
                                sq_item_dataset,
                                tag_id.tag,
                                self._dataset_stack[-1].stack,
                            )
                        )
                        errors.update(
                            self._validate_attributes(attribute["items"], True)
                        )
                        self._dataset_stack.pop()

        if report_unexpected_tags:
            errors.update(self._unexpected_tag_errors())

        return errors

    def _validate_func_group_modules(self, modules):
        if self._in_shared_group:
            self._func_group_info.clear()
        maybe_existing_modules = self._get_maybe_existing_modules(modules)
        for module_name, module in modules.items():
            errors = self._validate_module(module, module_name, maybe_existing_modules)
            if errors:
                self.result.add_tag_errors(module_name, errors)

    def _validate_attribute(self, tag_id: DicomTag, attribute: dict) -> TagError | None:
        """Validate a single DICOM attribute according to its type.

        Parameters
        ----------
        tag_id : DicomTag
            The tag ID of the attribute.
        attribute : dict
            Contains the attribute type ("type"), and the optional condition ("cond")
            for the presence of the attribute (see `Condition`).

        Returns
        -------
        The dictionary of found errors.
        """
        attribute_type = attribute["type"]
        # ignore image data and larger tags for now - we don't read them
        if tag_id.tag >= 0x7FE00010:
            return None
        has_tag = tag_id.tag in self._dataset_stack[-1].dataset

        error = TagError(attribute_type, context={})
        value_required = attribute_type in ("1", "1C")
        if attribute_type in ("1", "2"):
            tag_required, tag_allowed = True, True
        elif "cond" in attribute:
            error.context = error.context or {}
            error.context["cond"] = attribute["cond"]
            tag_required, tag_allowed = self._object_is_required_or_allowed(
                error.context["cond"]
            )
        else:
            tag_required, tag_allowed = False, True
        if not has_tag and tag_required:
            error.code = ErrorCode.TagMissing
        elif has_tag and not tag_allowed:
            error.code = ErrorCode.TagNotAllowed
        elif has_tag:
            value = self._dataset_stack[-1].dataset[tag_id.tag].value
            vr = self._dataset_stack[-1].dataset[tag_id.tag].VR
            if value_required:
                if value is None or isinstance(value, (Sequence, str)) and not value:
                    error.code = ErrorCode.TagEmpty
            if value is not None and (not isinstance(value, str) or value):
                if not isinstance(value, (MultiValue, list)):
                    value = [value]
                for i, v in enumerate(value):
                    if "enums" in attribute:
                        for enums in attribute["enums"]:
                            # if an index is there, we only check the value for the
                            # correct index; otherwise there will only be one entry
                            if "index" in enums and int(enums["index"]) != i + 1:
                                continue
                            if v not in enums["val"]:
                                error.code = ErrorCode.EnumValueNotAllowed
                                error.context = error.context or {}
                                error.context.update(
                                    {"value": v, "allowed": enums["val"]}
                                )
                    if not self._suppress_vr_warnings and not error.is_error():
                        vv = str(v) if vr in ("DS", "IS") else v
                        try:
                            validate_value(vr, vv, config.RAISE)
                        except ValueError:
                            error.code = ErrorCode.InvalidValue
                            error.context = error.context or {}
                            error.context.update({"value": vv, "VR": vr})

        if error.is_error():
            return error
        return None

    def _object_is_required_or_allowed(self, condition: dict):
        """Checks if an attribute is required or allowed in the current dataset,
         depending on the given condition.

        Parameters
        ----------
        condition : dict
            The condition or serialized condition defining if the object shall or
            may be present.

        Returns
        -------
        tuple(bool, bool)
            The first attribute is `True` if the attribute is required,
            the second if it is allowed. Valid combinations are:
            True, True: the attribute is required
            False, True: the attribute is allowed but not required
            False, False: the attribute is not allowed.
        """
        condition_type = condition["type"]
        if ConditionType(condition_type).user_defined:
            return False, True
        matches = self._composite_object_matches_condition(condition)
        if matches:
            if condition_type == ConditionType.NotAllowedOrUserDefined:
                return False, False
            return True, True
        allowed = (
            condition_type == ConditionType.MandatoryOrUserDefined
            or condition_type == ConditionType.MandatoryOrConditional
            and self._composite_object_matches_condition(condition["other_cond"])
        )
        return False, allowed

    def _composite_object_matches_condition(self, condition):
        """Checks if an attribute matches the given composite condition.

        Parameters
        ----------
        condition : dict
            The condition dictionary.

        Returns
        -------
        bool
            `True` if the attribute matches the condition.
        """
        if "and" in condition:
            matches = all(
                self._composite_object_matches_condition(cond)
                for cond in condition["and"]
            )
        elif "or" in condition:
            matches = any(
                self._composite_object_matches_condition(cond)
                for cond in condition["or"]
            )
        else:
            matches = self._matches_condition(condition)
        return matches

    def _matches_condition(self, condition):
        """Checks if an attribute matches the given condition.

        Parameters
        ----------
        condition : dict
            The condition dict.

        Returns
        -------
        bool
            `True` if the attribute matches the condition in the dataset.
        """
        tag_id = self._tag_id(condition["tag"])
        tag_value = None
        operator = condition["op"]
        if operator == ConditionOperator.Present:
            return self._tag_exists(tag_id)
        elif operator == ConditionOperator.Absent:
            return not self._tag_exists(tag_id)
        elif self._tag_exists(tag_id):
            tag = self._lookup_tag(tag_id)
            index = condition["index"]
            if index > 0:
                if index <= tag.VM:
                    tag_value = tag.value[index - 1]
            elif tag.VM > 1:
                tag_value = tag.value[0]
            else:
                tag_value = tag.value
            if tag_value is None:
                return False
            if operator == ConditionOperator.NotEmpty:
                return True
            return self._tag_matches(tag_value, operator, condition["values"])
        return False

    #
    # Get all the modules that have at least one tag/attribute present
    # in the dataset.
    #
    # We consider these as maybe-existing (or maybe-present) in the dataset.
    # Only maybe, because a tag/attribute may belong to two different modules,
    # and we cannot be sure which of those two modules should be considered
    # as "existing/present" in the dataset.
    #
    # We return a dictionary, where the key is the module ref
    # and the value is the list of tags present in the dataset.
    #
    def _get_maybe_existing_modules(self, modules) -> dict[str, set[DicomTag]]:
        maybe_existing_modules = {}
        for module in modules.values():
            module_info = self._get_module_info(module["ref"])
            existing_tags = self._get_existing_tags_of_module(module_info)
            if existing_tags:
                maybe_existing_modules[module["ref"]] = existing_tags
        return maybe_existing_modules

    #
    # Check if a maybe-existing module is strongly-existing.
    # A module is strongly-existing if it has existing tags/attributes
    # that are not present in any of the other maybe-existing modules.
    #
    @staticmethod
    def _does_module_strongly_exist(a_module_ref, maybe_existing_modules):
        a_tags = maybe_existing_modules[a_module_ref]
        for b_ref, b_tags in maybe_existing_modules.items():
            if b_ref == a_module_ref:
                continue
            tags_only_in_a = a_tags - (a_tags & b_tags)
            if len(tags_only_in_a) == 0:
                return False
        return True

    def _get_existing_tags_of_module(self, module_info) -> set[DicomTag]:
        existing_tag_ids = set()
        for tag_id_string in module_info:
            tag_id = self._tag_id(tag_id_string)
            if tag_id.tag in self._dataset_stack[-1].dataset:
                existing_tag_ids.add(tag_id)
        return existing_tag_ids

    def _lookup_tag(self, tag_id):
        for stack_item in reversed(self._dataset_stack):
            if tag_id.tag in stack_item.dataset:
                return stack_item.dataset[tag_id.tag]
        return None

    def _tag_exists(self, tag_id):
        return self._lookup_tag(tag_id) is not None

    def _tag_id(self, tag_id_string) -> DicomTag:
        group, element = tag_id_string[1:-1].split(",")
        # workaround for repeating tags -> special handling needed
        if group.endswith("xx"):
            group = group[:2] + "00"

        parents = [(d.tag or 0) for d in self._dataset_stack[1:]] or None
        return DicomTag((int(group, 16) << 16) + int(element, 16), parents)

    def _tag_matches(self, tag_value, operator, values):
        try:
            values = [type(tag_value)(value) for value in values]
        except ValueError:
            self.logger.debug(f"type for '{values}' does not match '{tag_value}'")
            # the values are of the wrong type - ignore them
            return False
        if operator == ConditionOperator.EqualsValue:
            return tag_value in values
        if operator == ConditionOperator.NotEqualsValue:
            return tag_value not in values
        if operator == ConditionOperator.GreaterValue:
            return tag_value > values[0]
        if operator == ConditionOperator.LessValue:
            return tag_value < values[0]
        if operator == ConditionOperator.EqualsTag:
            return tag_value in values
        return False

    def _get_module_info(self, module_ref, group_macros=None):
        return self._expanded_module_info(
            self._dicom_info.modules[module_ref], group_macros
        )

    def _expanded_module_info(self, module_info, group_macros):
        expanded_mod_info = {}
        for k, v in module_info.items():
            if k == "include":
                for info in module_info["include"]:
                    ref = info["ref"]
                    if ref == "FuncGroup":
                        if group_macros is None:
                            continue
                        expanded_mod_info["modules"] = group_macros
                    else:
                        if "cond" in info:
                            if not self._object_is_required_or_allowed(info["cond"])[0]:
                                continue
                        expanded_mod_info.update(
                            self._get_module_info(ref, group_macros)
                        )
            elif isinstance(v, dict):
                expanded_mod_info[k] = self._expanded_module_info(v, group_macros)
            else:
                expanded_mod_info[k] = v
        return expanded_mod_info

    def _unexpected_tag_errors(self):
        errors = {}
        for tag_id in self._dataset_stack[-1].unexpected_tags:
            errors[tag_id] = TagError(TagType.Undefined, ErrorCode.TagUnexpected)
        return errors

    # For debugging
    @staticmethod
    def _dump_dict_as_json(name, d):
        print("{")
        print(f'"{name}": ')
        print(json.dumps(d, indent=2))
        print("}")
