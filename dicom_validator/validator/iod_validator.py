import json
import logging
import sys

from dicom_validator.spec_reader.condition import Condition
from dicom_validator.tag_tools import tag_name_from_id


class InvalidParameterError(Exception):
    pass


class IODValidator(object):
    def __init__(self, dataset, iod_info, module_info, dict_info=None,
                 log_level=logging.INFO):
        self._dataset = dataset
        self._iod_info = iod_info
        self._module_info = module_info
        self._dict_info = dict_info
        self.errors = {}
        self.logger = logging.getLogger()
        self.logger.level = log_level
        if not self.logger.handlers:
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
        for module_name, module in iod_info['modules'].items():
            errors = self._validate_module(module, module_name)
            if errors:
                self.errors[module_name] = errors

    def _validate_module(self, module, module_name):
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

        has_module = self._has_module(module_info)
        if not required and not has_module:
            return errors

        if not allowed and has_module:
            for tag_id_string, attribute in module_info.items():
                tag_id = self._tag_id(tag_id_string)
                if tag_id in self._dataset:
                    message = self._incorrect_tag_message(tag_id,
                                                          'not allowed', None)
                    errors.setdefault(message, []).append(tag_id_string)
        else:
            for tag_id_string, attribute in module_info.items():
                result = self._validate_attribute(self._tag_id(tag_id_string),
                                                  attribute)
                if result is not None:
                    errors.setdefault(result, []).append(tag_id_string)
        return errors

    def _log_module_required(self, module_name, required, allowed,
                             condition_dict):
        msg = 'Module "' + module_name + '" is '
        msg += ('required' if required
                else 'optional' if allowed else 'not allowed')
        if condition_dict:
            condition = Condition.read_condition(condition_dict)
            if condition.type != 'U':
                msg += ' due to condition:\n  '
                msg += condition.to_string(self._dict_info)
        self.logger.debug(msg)

    def _incorrect_tag_message(self, tag_id, error_kind, condition_dict):
        msg = 'Tag {} is {}'.format(tag_name_from_id(tag_id, self._dict_info),
                                    error_kind)
        if condition_dict:
            condition = Condition.read_condition(condition_dict)
            if condition.type != 'U':
                msg += ' due to condition:\n  '
                msg += condition.to_string(self._dict_info)
        return msg

    def _validate_attribute(self, tag_id, attribute):
        attribute_type = attribute['type']
        # ignore image data and larger tags for now - we don't read them
        if tag_id >= 0x7FE00010:
            return
        has_tag = tag_id in self._dataset
        value_required = attribute_type in ('1', '1C')
        condition_dict = None
        if attribute_type in ('1', '2'):
            tag_required, tag_allowed = True, True
        elif attribute_type in ('1C', '2C'):
            if 'cond' in attribute:
                condition_dict = attribute['cond']
                tag_required, tag_allowed = (
                    self._object_is_required_or_allowed(condition_dict)
                )
            else:
                tag_required, tag_allowed = False, True
        else:
            tag_required, tag_allowed = False, True
        error_kind = None
        if not has_tag and tag_required:
            error_kind = 'missing'
        elif (tag_required and value_required and
              self._dataset[tag_id].value is None):
            error_kind = 'empty'
        elif has_tag and not tag_allowed:
            error_kind = 'not allowed'
        if error_kind is not None:
            msg = self._incorrect_tag_message(tag_id, error_kind,
                                              condition_dict)
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
            return tag_id in self._dataset
        elif operator == '-':
            return tag_id not in self._dataset
        elif tag_id in self._dataset:
            tag = self._dataset[tag_id]
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

    def _has_module(self, module_info):
        for tag_id_string, attribute in module_info.items():
            if attribute['type'] != '3':
                tag_id = self._tag_id(tag_id_string)
                # crude check - attribute could be also in another module
                if tag_id in self._dataset:
                    return True
        return False

    @staticmethod
    def _tag_id(tag_id_string):
        group, element = tag_id_string[1:-1].split(',')
        # workaround for repeating tags -> special handling needed
        if group.endswith('xx'):
            group = group[:2] + '00'
        return (int(group, 16) << 16) + int(element, 16)

    @staticmethod
    def _tag_matches(tag_value, operator, values):
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
        if 'include' in module_info:
            for ref in module_info['include']:
                module_info.update(self._get_module_info(ref))
            del module_info['include']
        if 'items' in module_info:
            module_info['items'] = self._expanded_module_info(
                module_info['items'])
        return module_info
