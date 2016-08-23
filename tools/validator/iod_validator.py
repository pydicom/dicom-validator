import logging


class IODValidator(object):
    def __init__(self, dataset, iod_info, module_info):
        self._dataset = dataset
        self._iod_info = iod_info
        self._module_info = module_info
        self.errors = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate(self):
        self.errors = {}
        if 'SOPClassUID' not in self._dataset:
            self.errors['fatal'] = ['Missing SOPClassUID']
        else:
            sop_class_uid = self._dataset.SOPClassUID
            if sop_class_uid not in self._iod_info:
                self.errors['fatal'] = ['Unknown SOPClassUID']
            else:
                self._validate_sop_class(sop_class_uid)
        if 'fatal' in self.errors:
            self.logger.error('%s - aborting', self.errors['fatal'])
        else:
            for error, tag_ids in self.errors.items():
                self.logger.warning('Tag(s) %s:', error)
                for tag_id in tag_ids:
                    self.logger.warning(tag_id)
        return self.errors

    def add_errors(self, errors):
        for key, value in errors.items():
            self.errors.setdefault(key, []).extend(value)

    def _validate_sop_class(self, sop_class_uid):
        iod_info = self._iod_info[sop_class_uid]
        for module in iod_info['modules'].values():
            self.add_errors(self._validate_module(module))

    def _validate_module(self, module):
        errors = {}
        usage = module['use']
        module_info = self._module_info[module['ref']]

        allowed = True
        if usage == 'M':
            required = True
        elif usage == 'U':
            required = False
        else:
            required, allowed = self._object_is_required_or_allowed(module['cond'])
        has_module = self._has_module(module_info)
        if not required and not has_module:
            return errors

        if not allowed and has_module:
            for tag_id_string, attribute in module_info.items():
                if self._tag_id(tag_id_string) in self._dataset:
                    errors.setdefault('not allowed', []).append(tag_id_string)
        else:
            for tag_id_string, attribute in module_info.items():
                result = self._validate_attribute(self._tag_id(tag_id_string), attribute)
                if result is not None:
                    errors.setdefault(result, []).append(tag_id_string)
        return errors

    def _validate_attribute(self, tag_id, attribute):
        attribute_type = attribute['type']
        has_tag = tag_id in self._dataset
        value_required = attribute_type in ('1', '1C')
        if attribute_type in ('1', '2'):
            tag_required, tag_allowed = True, True
        elif attribute_type in ('1C', '2C'):
            if 'cond' in attribute:
                tag_required, tag_allowed = self._object_is_required_or_allowed(attribute['cond'])
            else:
                tag_required, tag_allowed = False, True
        else:
            tag_required, tag_allowed = False, True
        if not has_tag and tag_required:
            return 'missing'
        if tag_required and value_required and self._dataset[tag_id].value is None:
            return 'empty'

    def _object_is_required_or_allowed(self, condition):
        if condition['type'] == 'U':
            return True, True
        tag_id = self._tag_id(condition['tag'])
        tag_value = None
        condition_fulfilled = tag_id in self._dataset
        if condition_fulfilled:
            tag = self._dataset[tag_id]
            index = condition['index']
            if index > 0:
                if index <= tag.VM:
                    tag_value = tag.value[index - 1]
            elif tag.VM > 1:
                tag_value = tag.value[0]
            else:
                tag_value = tag.value
            if tag_value is not None:
                condition_fulfilled = self._tag_matches(tag_value, condition['op'], condition['values'])
        if condition_fulfilled:
            return True, True
        return False, condition['type'] == 'MU'

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
        if operator == '=':
            return tag_value in values
        if operator == '>':
            return tag_value > values[0]
        if operator == '<':
            return tag_value < values[0]
        return False
