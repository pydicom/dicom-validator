import argparse
import json

from part6_reader import Part6Reader
from spec_reader.part3_reader import Part3Reader
from spec_reader.part4_reader import Part4Reader


def main():
    parser = argparse.ArgumentParser(
        description='Writes IOD description from DICOM standard in JSON format')
    parser.add_argument('--filename', '-f', help='Filepath to write to, defaults to std out')
    parser.add_argument('--sop-class-uid', '-su', help='Write description only for this SOP Class UID')
    parser.add_argument('--sop-class', '-sc', help='Write description only for this SOP Class')
    parser.add_argument('--standard-path', '-src', help='', default='./DICOM')
    args = parser.parse_args()
    chapter3reader = Part3Reader(args.standard_path)
    chapter4reader = Part4Reader(args.standard_path)
    if args.sop_class is not None:
        chapter6reader = Part6Reader(args.standard_path)
        sop_class_uid = chapter6reader.sop_class_uid(args.sop_class)
    else:
        sop_class_uid = args.sop_class_uid
    if sop_class_uid is not None:
        definition = chapter3reader.iod_description(
            chapter4reader.iod_chapter(sop_class_uid=sop_class_uid))
    else:
        iod_info = chapter3reader.iod_descriptions()
        chapter_info = chapter4reader.iod_chapters()
        definition = {chapter_info[chapter]: iod_info[chapter]
                      for chapter in iod_info if chapter in chapter_info}

    if definition is not None:
        if args.filename is not None:
            with open(args.filename, 'w') as f:
                f.write(json.dumps(definition))
        else:
            print(json.dumps(definition))
    return 0


if __name__ == '__main__':
    exit(main())
