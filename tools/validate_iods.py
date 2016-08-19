import argparse

from pydicom import filereader

from tools.spec_reader.part6_reader import Part6Reader
from tools.spec_reader.part3_reader import Part3Reader
from tools.spec_reader.part4_reader import Part4Reader
from tools.validator.iod_validator import IODValidator


def main():
    parser = argparse.ArgumentParser(
        description='Validates DICOM file IODs')
    parser.add_argument('dicomfile', help='Path of DICOM file to validate')
    parser.add_argument('--standard-path', '-src', help='', default='./DICOM')
    args = parser.parse_args()
    chapter6reader = Part6Reader(args.standard_path)
    dict_info = chapter6reader.data_elements()
    chapter3reader = Part3Reader(args.standard_path, dict_info)
    chapter4reader = Part4Reader(args.standard_path)

    iod_per_chapter_info = chapter3reader.iod_descriptions()
    chapter_info = chapter4reader.iod_chapters()
    iod_info = {chapter_info[chapter]: iod_per_chapter_info[chapter]
                for chapter in iod_per_chapter_info if chapter in chapter_info}
    data_set = filereader.read_file(args.dicomfile, stop_before_pixels=True, force=True)
    return len(IODValidator(data_set, iod_info).validate())


if __name__ == '__main__':
    exit(main())
