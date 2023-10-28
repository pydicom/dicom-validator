import json
import logging
import sys
from dataclasses import dataclass

from pydicom import Sequence
from pydicom.tag import Tag

from dicom_validator.spec_reader.condition import (
    Condition,
    ConditionType,
    ConditionOperator,
)
from dicom_validator.tag_tools import tag_name_from_id


class DatasetStackItem:
    def __init__(self, dataset, name):
        self.dataset = dataset
        self.name = name
        self.unexpected_tags = {int(d.tag) for d in dataset if not d.tag.is_private}


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

    def combined(self, module_name, seq_tag, per_frame):
        """Return the combined error for errors from shared and per-frame groups
        for the given module.

        Parameters
        ----------
        module_name : str
            The name of the validated macro module.
        seq_tag : str
            The tag ID string of the top-level-sequence tag in the macro
        per_frame : dict
            The errors from validation of the module in the per-frame group.
        """
        result = {}
        shared = self.shared_results.get(module_name)
        if not shared and not per_frame:
            # the module is present in both shared and per-frame groups
            # this is an error
            return {
                f"Tag {seq_tag} is present in both Shared and Per Frame "
                f"Functional Groups": [seq_tag]
            }
        for error in shared:
            # similar errors differ by the functional group tag
            per_frame_error = error.replace("(5200,9229)", "(5200,9230)")
            if per_frame_error in per_frame:
                # if the error appears in both sequences, it is real
                result[error] = shared[error]
                del per_frame[per_frame_error]
            elif "missing" in error:
                # for missing tags, we also have to check if the error does not appear
                # in the per-frame group because it is part of a missing sequence
                for per_frame_error in per_frame:
                    # the handling via the message is ugly and shall be replaced by
                    # more concise data structs later...
                    parts = per_frame_error.split(" > ")
                    if shared[error][0] in parts[1:]:
                        result[per_frame_error] = per_frame[per_frame_error]
                        del per_frame[per_frame_error]
                        break
            else:
                # other errors (unexpected tag, missing value) shall always remain
                result[error] = per_frame[error]

        for error in per_frame:
            if "missing" in error:
                # same check as above
                for shared_error in shared:
                    parts = shared_error.split(" > ")
                    if per_frame[error][0] in parts[1:]:
                        result[shared_error] = shared[shared_error]
                        del shared[shared_error]
                        break
            else:
                result[error] = per_frame[error]
        return result


@dataclass
class DicomInfo:
    dictionary: dict
    iods: dict
    modules: dict


class InvalidParameterError(Exception):
    pass


class IODValidator:
    def __init__(self, dataset, dicom_info, log_level=logging.INFO):
        self._dataset = dataset
        self._dataset_stack = [DatasetStackItem(self._dataset, None)]
        self._dicom_info = dicom_info
        self._func_group_info = FunctionalGroupInfo({}, set())
        self.errors = {}
        self.logger = logging.getLogger("validator")
        self.logger.level = log_level
        if not self.logger.hasHandlers():
            self.logger.addHandler(logging.StreamHandler(sys.stdout))

    def validate(self):
        """Validates current dataset.
        All errors are shown in the console output, and are also contained
        in the `errors` dictionary after execution.
        """
        self.errors = {}
        if "SOPClassUID" not in self._dataset:
            self.errors["fatal"] = "Missing SOPClassUID"
        else:
            sop_class_uid = self._dataset.SOPClassUID
            if sop_class_uid not in self._dicom_info.iods:
                self.errors["fatal"] = (
                    f"Unknown SOPClassUID " f"(probably retired): {sop_class_uid}"
                )
            else:
                self._validate_sop_class(sop_class_uid)
        if "fatal" in self.errors:
            self.logger.error("%s - aborting", self.errors["fatal"])
        else:
            if self.errors:
                self.logger.info("\nErrors\n======")
                for module_name, errors in self.errors.items():
                    title = (
                        "General:"
                        if module_name == "Root"
                        else f'Module "{module_name}":'
                    )
                    self.logger.warning(title)
                    for error_msg in errors:
                        self.logger.warning(error_msg)
                    self.logger.warning("")
        return self.errors

    def _validate_sop_class(self, sop_class_uid):
        """Validate the dataset against the given SOP class.
        Record all errors in the `errors` attribute.

        Parameters
        ----------
        sop_class_uid : str
            The SOP Class UID of the dataset.
        """
        iod_info = self._dicom_info.iods[sop_class_uid]

        self.logger.info('SOP class is "%s" (%s)', sop_class_uid, iod_info["title"])
        self.logger.debug("Checking modules for SOP Class")
        self.logger.debug("------------------------------")

        maybe_existing_modules = self._get_maybe_existing_modules(iod_info["modules"])

        for module_name, module in iod_info["modules"].items():
            self._dataset_stack[-1].name = module_name
            errors = self._validate_module(
                module, module_name, maybe_existing_modules, iod_info["group_macros"]
            )
            if errors:
                self.errors[module_name] = errors

        if len(self._dataset_stack[-1].unexpected_tags) != 0:
            self.errors["Root"] = self._unexpected_tag_errors()

    def _validate_module(
        self, module, module_name, maybe_existing_modules, group_macros=None
    ):
        """Validate the given module.

        Parameters
        ----------
        module : dict
            Contains the module reference chapter ("ref"), the usage ("use"),
            and optionally the usage condition as a dictionary (see `Condition`).
        module_name : str
            The module name as listed in the standard.
        maybe_existing_modules : dict[set]
            List of module references with contained tags that may be present
            in the dataset. Due to the fact that the same tag may belong to
            different modules, the presence of the module is only guessed at this point,
            and some of them may not actually be present.
        group_macros : dict[dict]
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
        if condition and "F" in condition["type"] and is_shared:
            required, allowed = False, False
        elif condition and "S" in condition["type"] and is_per_frame:
            required, allowed = False, False
        elif usage[0] == "M":
            required = True
        elif usage[0] == ConditionType.UserDefined:
            required = False

        else:
            required, allowed = self._object_is_required_or_allowed(condition)
        if group_macros is not None:
            self._log_module_required(module_name, required, allowed, condition)

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
                    seq_tag = list(module_info.keys())[0]
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
                if tag_id in self._dataset_stack[-1].dataset:
                    message = self._incorrect_tag_message(tag_id, "not allowed")
                    errors.setdefault(message, []).append(tag_id_string)
            return errors
        return self._validate_attributes(module_info, False)

    @property
    def _in_per_frame_group(self):
        return self._dataset_stack[-1].name == "(5200,9230)"

    @property
    def _in_shared_group(self):
        return self._dataset_stack[-1].name == "(5200,9229)"

    def _validate_attributes(self, attributes, report_unexpected_tags):
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
        errors = {}

        for tag_id_string, attribute in attributes.items():
            if tag_id_string == "modules":
                self._validate_func_group_modules(attribute)
            else:
                tag_id = self._tag_id(tag_id_string)

                result = self._validate_attribute(tag_id, attribute)
                if result is not None:
                    errors.setdefault(result, []).append(tag_id_string)

                self._dataset_stack[-1].unexpected_tags.discard(tag_id)

                if "items" in attribute:
                    data_elem = self._dataset_stack[-1].dataset.get_item(tag_id)
                    if data_elem is None:
                        continue
                    if data_elem.VR != "SQ":
                        raise RuntimeError(f"Not a sequence: {data_elem}")
                    for sq_item_dataset in data_elem.value:
                        self._dataset_stack.append(
                            DatasetStackItem(sq_item_dataset, tag_id_string)
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
                self.errors.setdefault(module_name, {}).update(errors)

    def _validate_attribute(self, tag_id, attribute):
        """Validate a single DICOM attribute according to its type.

        Parameters
        ----------
        tag_id : int
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
        if tag_id >= 0x7FE00010:
            return
        has_tag = tag_id in self._dataset_stack[-1].dataset
        value_required = attribute_type in ("1", "1C")
        condition_dict = None
        if attribute_type in ("1", "2"):
            tag_required, tag_allowed = True, True
        elif attribute_type in ("1C", "2C"):
            if "cond" in attribute:
                condition_dict = attribute["cond"]
                tag_required, tag_allowed = self._object_is_required_or_allowed(
                    condition_dict
                )
            else:
                tag_required, tag_allowed = False, True
        else:
            tag_required, tag_allowed = False, True
        error_kind = None
        if not has_tag and tag_required:
            error_kind = "missing"
        elif has_tag and not tag_allowed:
            error_kind = "not allowed"
        elif has_tag and value_required:
            value = self._dataset_stack[-1].dataset[tag_id].value
            if value is None or isinstance(value, Sequence) and not value:
                error_kind = "empty"
        if error_kind is not None:
            msg = self._incorrect_tag_message(
                tag_id, error_kind, self._condition_message(condition_dict)
            )
            return msg

    def _object_is_required_or_allowed(self, condition):
        """Checks if an attribute is required or allowed in the current dataset,
         depending on the given condition.

        Parameters
        ----------
        condition : str | Condition
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
        if isinstance(condition, str):
            condition = json.loads(condition)
        if ConditionType(condition["type"]).user_defined:
            return False, True
        required = self._composite_object_is_required(condition)
        if required:
            return True, True
        allowed = (
            condition["type"] == ConditionType.MandatoryOrUserDefined
            or condition["type"] == ConditionType.MandatoryOrConditional
            and self._composite_object_is_required(condition["other_cond"])
        )
        return False, allowed

    def _composite_object_is_required(self, condition):
        """Checks if an attribute with a composite condition is required or allowed
         in the current dataset.

        Parameters
        ----------
        condition : dict
            The condition dict defining if the object shall be present.

        Returns
        -------
        bool
            `True` if the attribute is required in the dataset.
        """
        if "and" in condition:
            required = all(
                self._composite_object_is_required(cond) for cond in condition["and"]
            )
        elif "or" in condition:
            required = any(
                self._composite_object_is_required(cond) for cond in condition["or"]
            )
        else:
            required = self._object_is_required(condition)
        return required

    def _object_is_required(self, condition):
        """Checks if an attribute is required in the current dataset,
         depending on the given condition.

        Parameters
        ----------
        condition : dict
            The condition dict defining if the object shall be present.

        Returns
        -------
        bool
            `True` if the attribute is required in the dataset.
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
    def _get_maybe_existing_modules(self, modules):
        maybe_existing_modules = {}
        for module in modules.values():
            module_info = self._get_module_info(module["ref"])
            existing_tags = self._get_existing_tags_of_module(module_info)
            if len(existing_tags) != 0:
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

    def _get_existing_tags_of_module(self, module_info):
        existing_tag_ids = set()
        for tag_id_string in module_info:
            tag_id = self._tag_id(tag_id_string)
            if tag_id in self._dataset_stack[-1].dataset:
                existing_tag_ids.add(tag_id)
        return existing_tag_ids

    def _lookup_tag(self, tag_id):
        for stack_item in reversed(self._dataset_stack):
            if tag_id in stack_item.dataset:
                return stack_item.dataset[tag_id]
        return None

    def _tag_exists(self, tag_id):
        return self._lookup_tag(tag_id) is not None

    @staticmethod
    def _tag_id(tag_id_string):
        group, element = tag_id_string[1:-1].split(",")
        # workaround for repeating tags -> special handling needed
        if group.endswith("xx"):
            group = group[:2] + "00"
        return (int(group, 16) << 16) + int(element, 16)

    @staticmethod
    def _tag_id_string(tag_id):
        tag = Tag(tag_id)
        return str(tag).replace(" ", "")

    @staticmethod
    def _tag_matches(tag_value, operator, values):
        values = [type(tag_value)(value) for value in values]
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

    def _log_module_required(self, module_name, required, allowed, condition_dict):
        msg = f'Module "{module_name}" is '
        msg += "required" if required else "optional" if allowed else "not allowed"
        if condition_dict:
            msg += self._condition_message(condition_dict)
        self.logger.debug(msg)

    def _unexpected_tag_errors(self):
        errors = {}
        for tag_id in self._dataset_stack[-1].unexpected_tags:
            message = self._incorrect_tag_message(tag_id, "unexpected")
            errors.setdefault(message, []).append(self._tag_id_string(tag_id))
        return errors

    def _tag_context_message(self):
        if len(self._dataset_stack) > 1:
            m = " > ".join([item.name for item in self._dataset_stack])
            context = f" in  {m}"
            return context
        return ""

    def _incorrect_tag_message(self, tag_id, error_kind, extra_message=""):
        tag_name = tag_name_from_id(tag_id, self._dicom_info.dictionary)
        msg = f"Tag {tag_name} is {error_kind}{self._tag_context_message()}"
        if len(extra_message) != 0:
            msg = f"{msg} {extra_message}"
        return msg

    def _condition_message(self, condition_dict):
        if condition_dict is None:
            return ""
        msg = ""
        condition = Condition.read_condition(condition_dict)
        if condition.type != ConditionType.UserDefined:
            msg += (
                f"due to condition:\n  "
                f"'{condition.to_string(self._dicom_info.dictionary)}'"
            )
        return msg

    # For debugging
    @staticmethod
    def _dump_dict_as_json(name, d):
        print("{")
        print(f'"{name}": ')
        print(json.dumps(d, indent=2))
        print("}")
