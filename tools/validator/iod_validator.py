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
            self.logger.error('{} - aborting'.format(self.errors['fatal']))
        else:
            for error, tag_ids in self.errors.items():
                self.logger.warning('Tag(s) {}:'.format(error))
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

        if usage == 'M':
            required = True
        elif usage == 'U':
            required = False
        else:
            required = self._module_is_required(usage)
        if not required and not self._has_module(module_info):
            return errors
        for tag_id_string, attribute in module_info.items():
            result = self._validate_attribute(self._tag_id(tag_id_string), attribute)
            if result is not None:
                errors.setdefault(result, []).append(tag_id_string)
        return errors

    def _validate_attribute(self, tag_id, attribute):
        attribute_type = attribute['type']
        has_tag = tag_id in self._dataset
        if attribute_type in ('1C', '2C'):
            if self._attribute_is_required('dummy'):
                attribute_type = attribute_type[:1]
            elif has_tag:
                return 'missing'
        if not has_tag and attribute_type in ('1', '2'):
            return 'missing'
        if attribute_type == '1' and self._dataset[tag_id].value is None:
            return 'empty'

    def _module_is_required(self, usage):
        # todo: parse the condition and check if it is met if possible
        return False

    def _attribute_is_required(self, usage):
        # todo: parse the condition and check if it is met if possible
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
        # workaround for 60xx tags -> special handling needed
        if group.endswith('xx'):
            group = group[:2] + '00'
        return (int(group, 16) << 16) + int(element, 16)
