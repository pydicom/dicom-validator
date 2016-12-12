import argparse
import json
import logging
import os

from dcm_spec_tools.validator.dicom_file_validator import DicomFileValidator
from spec_reader.edition_reader import EditionReader


def main():
    parser = argparse.ArgumentParser(
        description='Validates DICOM file IODs')
    parser.add_argument('dicomfiles', help='Path(s) of DICOM files or directories to validate',
                        nargs='+')
    parser.add_argument('--standard-path', '-src',
                        help='Base path with the DICOM specs in docbook and json format',
                        default=os.path.join(os.path.expanduser("~"), 'dcm-spec-tools'))
    parser.add_argument('--revision', '-r',
                        help='Standard revision (e.g. "2014c"), year of revision, or "current"',
                        default='current')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Outputs diagnostic information')
    args = parser.parse_args()

    _, base_path = EditionReader.get_revision(args.revision, args.standard_path)
    if base_path is None:
        print('DICOM revision {} not found - use get_dcm_specs to download it.'.format(args.revision))
        return 1

    json_path = os.path.join(base_path, 'json')
    with open(os.path.join(json_path, 'dict_info.json')) as info_file:
        dict_info = json.load(info_file)
    with open(os.path.join(json_path, 'iod_info.json')) as info_file:
        iod_info = json.load(info_file)
    with open(os.path.join(json_path, 'module_info.json')) as info_file:
        module_info = json.load(info_file)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    validator = DicomFileValidator(iod_info, module_info, dict_info, log_level)
    return sum(len(validator.validate(dicom_path)) for dicom_path in args.dicomfiles)


if __name__ == '__main__':
    exit(main())
