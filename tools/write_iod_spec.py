import argparse
import json

from spec_reader.part3_reader import Part3Reader
from spec_reader.part4_reader import Part4Reader


def main():
    parser = argparse.ArgumentParser(
        description='Writes IOD description from DICOM standard in JSON format')
    parser.add_argument('--filename', '-f', help='Filepath to write to, defaults to std out')
    parser.add_argument('--sop-class-uid', '-su', help='')
    parser.add_argument('--sop-class', '-sc', help='')
    parser.add_argument('--standard-path', '-src', help='', default='./DICOM')
    args = parser.parse_args()
    chapter3reader = Part3Reader(args.standard_path)
    chapter4reader = Part4Reader(args.standard_path)
    sop_class_uid = None
    if args.sop_class is not None:
        pass
    else:
        sop_class_uid = args.sop_class_uid
    if sop_class_uid is not None:
        definition = chapter3reader.iod_description(chapter4reader.iod_chapter(sop_class_uid=sop_class_uid))
    else:
        # todo
        definition = None
    if definition is not None:
        if args.filename is not None:
            with open(args.filename, 'w') as f:
                f.write(json.dumps(definition))
        else:
            print(json.dumps(definition))
    return 0


if __name__ == '__main__':
    exit(main())
