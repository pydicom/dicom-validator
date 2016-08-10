import logging


class IODValidator(object):
    def __init__(self, dataset, iod_info):
        self._dataset = dataset
        self._iod_info = iod_info
        self.logger = logging.getLogger(self.__class__.__name__)

    def validate(self):
        errors = {}
        if 'SOPClassUID' not in self._dataset:
            errors['fatal'] = ['Missing SOPClassUID']
        else:
            sop_class_uid = self._dataset.SOPClassUID
            if not sop_class_uid in self._iod_info:
                errors['fatal'] = ['Unknown SOPClassUID']
            else:
                errors = self._validate_sop_class(sop_class_uid)
        if 'fatal' in errors:
            self.logger.error('{} - aborting'.format(errors['fatal']))
        return errors

    def _validate_sop_class(self, sop_class_uid):
        errors = {}
        iod_info = self._iod_info[sop_class_uid]
        for module in iod_info['modules']:
            errors.update(self._validate_module(module))
        return errors

    def _validate_module(self, module):
        errors = {}
        # todo
        return errors
