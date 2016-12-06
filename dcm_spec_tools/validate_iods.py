import argparse
import json
import logging
import os

from dcm_spec_tools.spec_reader.part3_reader import Part3Reader
from dcm_spec_tools.spec_reader.part4_reader import Part4Reader
from dcm_spec_tools.spec_reader.part6_reader import Part6Reader
from dcm_spec_tools.validator.dicom_file_validator import DicomFileValidator


def main():
    parser = argparse.ArgumentParser(
        description='Validates DICOM file IODs')
    parser.add_argument('dicomfiles', help='Path(s) of DICOM files or directories to validate',
                        nargs='+')
    parser.add_argument('--standard-path', '-src',
                        help='Path with the DICOM specs in docbook format',
                        default='./DICOM')
    parser.add_argument('--json-path', '-json',
                        help='Path with the DICOM specs in JSON format')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Outputs diagnostic information')
    args = parser.parse_args()
    if args.json_path:
        with open(os.path.join(args.json_path, 'dict_info.json')) as info_file:
            dict_info = json.load(info_file)
        with open(os.path.join(args.json_path, 'iod_info.json')) as info_file:
            iod_info = json.load(info_file)
        with open(os.path.join(args.json_path, 'module_info.json')) as info_file:
            module_info = json.load(info_file)
    else:
        dict_info = Part6Reader(args.standard_path).data_elements()
        part3reader = Part3Reader(args.standard_path, dict_info)
        iod_per_chapter_info = part3reader.iod_descriptions()
        chapter_info = Part4Reader(args.standard_path).iod_chapters()
        iod_info = {chapter_info[chapter]: iod_per_chapter_info[chapter]
                    for chapter in iod_per_chapter_info if chapter in chapter_info}
        module_info = part3reader.module_descriptions()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    validator = DicomFileValidator(iod_info, module_info, dict_info, log_level)
    return sum(len(validator.validate(dicom_path)) for dicom_path in args.dicomfiles)


if __name__ == '__main__':
    exit(main())
