import json
import logging
import sys
import pydicom


from dicom_validator.spec_reader.condition import Condition
from dicom_validator.tag_tools import tag_name_from_id


class DatasetStackItem:
    def __init__(self, dataset, name):
        self.dataset = dataset
        self.name = name
        self.unexpected_tags = { int(d.tag) for d in dataset }


class InvalidParameterError(Exception):
    pass


class IODValidator(object):
    def __init__(self, dataset, iod_info, module_info, dict_info=None,
                 log_level=logging.INFO):
        self._dataset = dataset
        self._dataset_stack = [
            DatasetStackItem(self._dataset, None)
        ]
        self._iod_info = iod_info
        self._module_info = module_info
        self._dict_info = dict_info
        self.errors = {}
        self.logger = logging.getLogger('validator')
        self.logger.level = log_level
        if not self.logger.hasHandlers():
            self.logger.addHandler(logging.StreamHandler(sys.stdout))

    def validate(self):
        self.errors = {}
        if 'SOPClassUID' not in self._dataset:
            self.errors['fatal'] = 'Missing SOPClassUID'
        else:
            sop_class_uid = self._dataset.SOPClassUID
            if sop_class_uid not in self._iod_info:
                self.errors['fatal'] = (f'Unknown SOPClassUID '
                                        f'(probably retired): {sop_class_uid}')
            else:
                self._validate_sop_class(sop_class_uid)
        if 'fatal' in self.errors:
            self.logger.error('%s - aborting', self.errors['fatal'])
        else:
            if self.errors:
                self.logger.info('\nErrors\n======')
                for module_name, errors in self.errors.items():
                    self.logger.warning('Module "{}":'.format(module_name))
                    for error_msg in errors:
                        self.logger.warning(error_msg)
        return self.errors

    def add_errors(self, errors):
        for key, value in errors.items():
            self.errors.setdefault(key, []).extend(value)

    def _validate_sop_class(self, sop_class_uid):
        iod_info = self._iod_info[sop_class_uid]

        self.logger.info('SOP class is "%s" (%s)', sop_class_uid,
                         iod_info['title'])
        self.logger.debug('Checking modules for SOP Class')
        self.logger.debug('------------------------------')

        maybe_existing_modules = self._get_maybe_existing_modules(iod_info)
        
        for module_name, module in iod_info['modules'].items():
            self._dataset_stack[-1].name = module_name
            errors = self._validate_module(module, module_name, maybe_existing_modules)
            if errors:
                self.errors[module_name] = errors

        if len(self._dataset_stack[-1].unexpected_tags) != 0:
            self.errors["Root"] = self._unexpected_tag_errors()

    def _validate_module(self, module, module_name, maybe_existing_modules):
        errors = {}
        usage = module['use']
        module_info = self._get_module_info(module['ref'])
        condition = module['cond'] if 'cond' in module else None

        allowed = True
        if usage == 'M':
            required = True
        elif usage == 'U':
            required = False
        else:
            required, allowed = self._object_is_required_or_allowed(condition)
        self._log_module_required(module_name, required, allowed, condition)

        if required:
            # Always validate required modules.
            # If the module is missing from the dataset the validation
            # should report it as an error.
            errors.update(self._validate_attributes(module_info, False))
            return errors

        if module['ref'] not in maybe_existing_modules:
            # The module is not present at all in the dataset.
            # No validation is needed.
            return errors
        
        # At this point the module is __not required__ but it __may be existing__
        # in the dataset.
        # Just "maybe" because multiple modules may have overlapping attributes.
        # So, let's see if it exists "strongly" enough to be considered for further checks.
        if not self._does_module_strongly_exist(module['ref'], maybe_existing_modules):
            return errors

        if not allowed:
            for tag_id_string, attribute in module_info.items():
                tag_id = self._tag_id(tag_id_string)
                if tag_id in self._dataset:
                    message = self._incorrect_tag_message(tag_id,
                                                          'not allowed')
                    errors.setdefault(message, []).append(tag_id_string)
            return errors
        
        errors.update(self._validate_attributes(module_info, False))
        return errors

    def _validate_attributes(self, attributes, report_unexpected_tags):
        errors = {}

        for tag_id_string, attribute in attributes.items():
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
                for i, sq_item_dataset in enumerate(data_elem.value):
                    self._dataset_stack.append(
                        DatasetStackItem(sq_item_dataset, tag_id_string))
                    errors.update(self._validate_attributes(attribute["items"], True))
                    self._dataset_stack.pop()

        if report_unexpected_tags:
            errors.update(self._unexpected_tag_errors())

        return errors

    def _validate_attribute(self, tag_id, attribute):
        attribute_type = attribute['type']
        # ignore image data and larger tags for now - we don't read them
        if tag_id >= 0x7FE00010:
            return
        has_tag = tag_id in self._dataset_stack[-1].dataset
        value_required = attribute_type in ('1', '1C')
        condition_dict = None
        if attribute_type in ('1', '2'):
            tag_required, tag_allowed = True, True
        elif attribute_type in ('1C', '2C'):
            if 'cond' in attribute:
                condition_dict = attribute['cond']
                tag_required, tag_allowed = self._object_is_required_or_allowed(condition_dict)
            else:
                tag_required, tag_allowed = False, True
        else:
            tag_required, tag_allowed = False, True
        error_kind = None
        if not has_tag and tag_required:
            error_kind = 'missing'
        elif (tag_required and value_required and
              self._dataset_stack[-1].dataset[tag_id].value is None):
            error_kind = 'empty'
        elif has_tag and not tag_allowed:
            error_kind = 'not allowed'
        if error_kind is not None:
            msg = self._incorrect_tag_message(
                tag_id, error_kind, self._conditon_message(condition_dict))
            return msg

    def _object_is_required_or_allowed(self, condition):
        if isinstance(condition, str):
            condition = json.loads(condition)
        if condition['type'] == 'U':
            return False, True
        required = self._composite_object_is_required(condition)
        if required:
            return True, True
        allowed = (condition['type'] == 'MU' or condition['type'] == 'MC' and
                   self._composite_object_is_required(condition['other_cond']))
        return False, allowed

    def _composite_object_is_required(self, condition):
        if 'and' in condition:
            required = all(self._composite_object_is_required(cond)
                           for cond in condition['and'])
        elif 'or' in condition:
            required = any(self._composite_object_is_required(cond)
                           for cond in condition['or'])
        else:
            required = self._object_is_required(condition)
        return required

    def _object_is_required(self, condition):
        tag_id = self._tag_id(condition['tag'])
        tag_value = None
        operator = condition['op']
        if operator == '+':
            return self._tag_exists(tag_id)
        elif operator == '-':
            return not self._tag_exists(tag_id)
        elif self._tag_exists(tag_id):
            tag = self._lookup_tag(tag_id)
            index = condition['index']
            if index > 0:
                if index <= tag.VM:
                    tag_value = tag.value[index - 1]
            elif tag.VM > 1:
                tag_value = tag.value[0]
            else:
                tag_value = tag.value
            if tag_value is None:
                return False
            if operator == '++':
                return True
            return self._tag_matches(tag_value, operator, condition['values'])
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
    def _get_maybe_existing_modules(self, iod_info):
        maybe_existing_modules = {}
        for module in iod_info['modules'].values():
            module_info = self._get_module_info(module['ref'])
            existing_tags = self._get_existing_tags_of_module(module_info)
            if len(existing_tags) != 0:
                maybe_existing_modules[module['ref']] = existing_tags
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
            if tag_id in self._dataset:
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
        group, element = tag_id_string[1:-1].split(',')
        # workaround for repeating tags -> special handling needed
        if group.endswith('xx'):
            group = group[:2] + '00'
        return (int(group, 16) << 16) + int(element, 16)

    @staticmethod
    def _tag_id_string(tag_id):
        tag = pydicom.tag.Tag(tag_id)
        return str(tag).replace(' ', '')

    @staticmethod
    def _tag_matches(tag_value, operator, values):
        # TODO: These fix-ups should be done in ConditionParser:
        if "non-zero" in values:
            operator = '!='
            values = [ '0' ]
        if "zero" in values:
            values = [ '0' ]

        values = [type(tag_value)(value) for value in values]
        if operator == '=':
            return tag_value in values
        if operator == '!=':
            return tag_value not in values
        if operator == '>':
            return tag_value > values[0]
        if operator == '<':
            return tag_value < values[0]
        if operator == '=>':
            return tag_value in values
        return False

    def _get_module_info(self, module_ref):
        return self._expanded_module_info(self._module_info[module_ref])

    def _expanded_module_info(self, module_info):
        expanded_mod_info = {}
        for k, v in module_info.items():
            if k == 'include':
                for ref in module_info['include']:
                    expanded_mod_info.update(self._get_module_info(ref))
            elif isinstance(v, dict) :
                expanded_mod_info[k] = self._expanded_module_info(v)
            else:
                expanded_mod_info[k] = v
        return expanded_mod_info

    def _log_module_required(self, module_name, required, allowed,
                             condition_dict):
        msg = 'Module "' + module_name + '" is '
        msg += ('required' if required
                else 'optional' if allowed else 'not allowed')
        if condition_dict:
            msg += self._conditon_message(condition_dict)
        self.logger.debug(msg)

    def _unexpected_tag_errors(self):
        errors = {}
        for tag_id in self._dataset_stack[-1].unexpected_tags:
            message = self._incorrect_tag_message(
                tag_id, 'unexpected', self._tag_context_message())
            errors.setdefault(message, []).append(self._tag_id_string(tag_id))
        return errors

    def _tag_context_message(self):
        m = ' > '.join([item.name for item in self._dataset_stack])
        context = f"in\n  {m}"
        return context

    def _incorrect_tag_message(self, tag_id, error_kind, extra_message = ""):
        tag_name = tag_name_from_id(tag_id, self._dict_info)
        msg = f'Tag {tag_name} is {error_kind}'
        if len(extra_message) != 0:
            msg = f'{msg} {extra_message}'
        return msg
    
    def _conditon_message(self, condition_dict):
        if condition_dict is None:
            return ""
        msg = ""
        condition = Condition.read_condition(condition_dict)
        if condition.type != 'U':
            msg += 'due to condition:\n  '
            msg += condition.to_string(self._dict_info)
        return msg

    # For debugging
    def _dump_dict_as_json(self, name, d):
        print(f'{{')
        print(f'"{name}": ')
        print(json.dumps(d, indent=2))
        print(f'}}')
