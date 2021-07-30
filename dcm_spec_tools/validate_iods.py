import argparse
import json
import logging
import os

from dcm_spec_tools.validator.dicom_file_validator import DicomFileValidator
from dcm_spec_tools.spec_reader.edition_reader import EditionReader


def validate(args, base_path):
    json_path = os.path.join(base_path, 'json')
    with open(os.path.join(json_path, EditionReader.dict_info_json)) as info_file:
        dict_info = json.load(info_file)
    with open(os.path.join(json_path, EditionReader.iod_info_json)) as info_file:
        iod_info = json.load(info_file)
    with open(os.path.join(json_path, EditionReader.module_info_json)) as info_file:
        module_info = json.load(info_file)
    log_level = logging.DEBUG if args.verbose else logging.INFO
    validator = DicomFileValidator(iod_info, module_info, dict_info, log_level)
    error_nr = 0
    for dicom_path in args.dicomfiles:
        error_nr += sum(len(error) for error in list(validator.validate(dicom_path).values()))
    return error_nr


def main():
    parser = argparse.ArgumentParser(
        description='Validates DICOM file IODs')
    parser.add_argument('dicomfiles', help='Path(s) of DICOM files or directories to validate',
                        nargs='+')
    parser.add_argument('--standard-path', '-src',
                        help='Base path with the DICOM specs in docbook and json format',
                        default=os.path.join(os.path.expanduser("~"), 'dicom-validator'))
    parser.add_argument('--revision', '-r',
                        help='Standard revision (e.g. "2014c"), year of '
                             'revision, "current" or "local" (latest '
                             'locally installed)',
                        default='current')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Outputs diagnostic information')
    args = parser.parse_args()

    edition_reader = EditionReader(args.standard_path)
    destination = edition_reader.get_revision(args.revision)
    if destination is None:
        print('Failed to get DICOM edition {} - aborting'.format(args.revision))
        return 1

    return validate(args, destination)


if __name__ == '__main__':
    exit(main())
