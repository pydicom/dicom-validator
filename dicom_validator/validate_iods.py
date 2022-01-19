import argparse
import logging
import os

from dicom_validator.spec_reader.edition_reader import EditionReader
from dicom_validator.validator.dicom_file_validator import DicomFileValidator


def validate(args, base_path):
    json_path = os.path.join(base_path, 'json')
    dict_info = EditionReader.load_dict_info(json_path)
    iod_info = EditionReader.load_iod_info(json_path)
    module_info = EditionReader.load_module_info(json_path)
    log_level = logging.DEBUG if args.verbose else logging.INFO
    validator = DicomFileValidator(iod_info, module_info, dict_info, log_level, args.force_read)
    error_nr = 0
    for dicom_path in args.dicomfiles:
        error_nr += sum(len(error) for error in
                        list(validator.validate(dicom_path).values()))
    return error_nr


def main(args=None):
    parser = argparse.ArgumentParser(
        description='Validates DICOM file IODs')
    parser.add_argument('dicomfiles',
                        help='Path(s) of DICOM files or directories '
                             'to validate',
                        nargs='+')
    parser.add_argument('--standard-path', '-src',
                        help='Base path with the DICOM specs in docbook '
                             'and json format',
                        default=os.path.join(os.path.expanduser("~"),
                                             'dicom-validator'))
    parser.add_argument('--revision', '-r',
                        help='Standard revision (e.g. "2014c"), year of '
                             'revision, "current" or "local" (latest '
                             'locally installed)',
                        default='current')
    parser.add_argument('--force-read', action='store_true',
                        help='Force-read DICOM files without header',
                        default=False)
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Outputs diagnostic information')
    args = parser.parse_args(args)

    edition_reader = EditionReader(args.standard_path)
    destination = edition_reader.get_revision(args.revision)
    if destination is None:
        print(
            'Failed to get DICOM edition {} - aborting'.format(args.revision))
        return 1

    return validate(args, destination)


if __name__ == '__main__':
    exit(main())
