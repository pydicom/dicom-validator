"""
Dumps tag information from a DICOM file using information in PS3.6.
For testing the dictionary only - there are better tools for this.
"""

import argparse

from pydicom import filereader

from spec_reader.part6_reader import Part6Reader

DATA_DEFINITIONS = {}


def print_dataelement(dummy_dataset, dataelement):
    tag_id = '({:04X},{:04X})'.format(dataelement.tag.group, dataelement.tag.element)
    description = DATA_DEFINITIONS.get(tag_id)
    if description is None:
        print('No dictionary entry found for {}'.format(tag_id))
    else:
        print('{} {:35} {} {:4} {} [{}]'.format(tag_id,
                                                description['name'][:35], description['vr'],
                                                description['vm'], description['prop'], dataelement.value))


def main():
    parser = argparse.ArgumentParser(
        description='Dumps DICOM information dictionary from DICOM file using PS3.6')
    parser.add_argument('dicomfile', help='Path of DICOM file to parse')
    parser.add_argument('--standard-path', '-src',
                        help='Path with the DICOM specs in docbook format',
                        default='./DICOM')
    args = parser.parse_args()

    global DATA_DEFINITIONS
    DATA_DEFINITIONS = Part6Reader(args.standard_path).data_elements()

    dataset = filereader.read_file(args.dicomfile, stop_before_pixels=True, force=True)
    dataset.walk(print_dataelement)

    return 0


if __name__ == '__main__':
    exit(main())
