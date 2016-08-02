import argparse
import json

from part6_reader import Part6Reader


def main():
    parser = argparse.ArgumentParser(
        description='Writes DICOM dictionary from DICOM standard in JSON format')
    parser.add_argument('--filename', '-f', help='Filepath to write to, defaults to std out')
    parser.add_argument('--standard-path', '-src', help='', default='./DICOM')
    args = parser.parse_args()
    reader = Part6Reader(args.standard_path)
    definitions = {'{:04x},{:04x}'.format(entry[0][0], entry[0][1]): entry[1] for entry in
                   reader.data_elements().items()}

    if definitions:
        if args.filename is not None:
            with open(args.filename, 'w') as f:
                f.write(json.dumps(definitions))
        else:
            print(json.dumps(definitions))
    return 0


if __name__ == '__main__':
    exit(main())
