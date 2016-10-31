"""
Dumps tag information from a DICOM file using information in PS3.6.
For testing the dictionary only - there are better tools for this.
"""

import argparse
import json
import os

from pydicom import filereader

from dcm_spec_tools.spec_reader.part6_reader import Part6Reader


class DataElementDumper(object):
    dict_info = None

    def __init__(self, dict_info):
        self.__class__.dict_info = dict_info

    def print_dataset(self, dataset):
        dataset.walk(self.print_dataelement)

    @staticmethod
    def print_dataelement(dummy_dataset, dataelement):
        tag_id = '({:04X},{:04X})'.format(dataelement.tag.group, dataelement.tag.element)
        description = DataElementDumper.dict_info.get(tag_id)
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
    parser.add_argument('--json-path', '-json',
                        help='Path with the DICOM specs in JSON format')
    args = parser.parse_args()
    if args.json_path:
        with open(os.path.join(args.json_path, 'dict_info.json')) as info_file:
            dict_info = json.load(info_file)
    else:
        dict_info = Part6Reader(args.standard_path).data_elements()

    dataset = filereader.read_file(args.dicomfile, stop_before_pixels=True, force=True)
    DataElementDumper(dict_info).print_dataset(dataset)

    return 0


if __name__ == '__main__':
    exit(main())
