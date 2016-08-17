import argparse
import json
import os

from spec_reader.part3_reader import Part3Reader
from spec_reader.part4_reader import Part4Reader
from spec_reader.part6_reader import Part6Reader


def main():
    parser = argparse.ArgumentParser(
        description='Writes descriptions taken from DICOM standard in JSON format')
    parser.add_argument('destination', help='Directory to write the specs to')
    parser.add_argument('--standard-path', '-src', help='', default='./DICOM')
    args = parser.parse_args()

    if not os.path.exists(args.destination):
        os.makedirs(args.destination)
    elif not os.path.isdir(args.destination):
        print('A file exists with the name of the target directory - aborting')
        exit(1)

    part3reader = Part3Reader(args.standard_path)
    part4reader = Part4Reader(args.standard_path)
    part6reader = Part6Reader(args.standard_path)

    iod_info = part3reader.iod_descriptions()
    chapter_info = part4reader.iod_chapters()
    definition = {chapter_info[chapter]: iod_info[chapter]
                  for chapter in iod_info if chapter in chapter_info}
    with open(os.path.join(args.destination, 'iod_info.json'), 'w') as f:
        f.write(json.dumps(definition))

    with open(os.path.join(args.destination, 'module_info.json'), 'w') as f:
        f.write(json.dumps(part3reader.module_descriptions()))

    with open(os.path.join(args.destination, 'dict_info.json'), 'w') as f:
        f.write(json.dumps(part6reader.data_elements()))

    return 0


if __name__ == '__main__':
    exit(main())
