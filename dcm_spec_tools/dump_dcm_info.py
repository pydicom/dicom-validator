"""
Dumps tag information from a DICOM file using information in PS3.6.
"""

import argparse
import json
import os
import string

import sys
from pydicom import filereader

from dcm_spec_tools.spec_reader.edition_reader import EditionReader

in_py2 = sys.version_info[0] == 2


class DataElementDumper(object):
    dict_info = None
    uid_info = {}
    level = 0
    max_value_len = 80

    def __init__(self, dict_info, uid_info, max_value_len):
        self.__class__.dict_info = dict_info
        self.__class__.max_value_len = max_value_len
        for uid_dict in uid_info.values():
            self.__class__.uid_info.update(uid_dict)

    def print_dataset(self, dataset):
        dataset.walk(self.print_dataelement)

    @staticmethod
    def print_element(tag_id, name, vr, prop, value):
        vm = 1 if value else 0
        if isinstance(value, list):
            vm = len(value)
            value = '\\'.join([str(element) for element in value])
        if not in_py2 and isinstance(value, bytes):
            value = str(value)[2:-1]
        if in_py2 and isinstance(value, str):
            value = ''.join([c if c in string.printable else r'\x{:02x}'.format(ord(c))
                             for c in value])
        if isinstance(value, str) and len(value) > DataElementDumper.max_value_len:
            value = value[:DataElementDumper.max_value_len] + '...'

        indent = 2 * DataElementDumper.level
        format_string = '{{}}{{}} {{:{}}} {{}} {{:4}} {{}} [{{}}]'.format(40 - indent)
        print(format_string.format(' ' * indent,
                                   tag_id,
                                   name[:40 - indent],
                                   vr,
                                   vm,
                                   prop,
                                   value))

    @staticmethod
    def print_dataelement(dummy_dataset, dataelement):
        tag_id = '({:04X},{:04X})'.format(dataelement.tag.group, dataelement.tag.element)
        description = DataElementDumper.dict_info.get(tag_id)
        if description is None:
            name = '[Unknown]'
            vr = dataelement.VR
            prop = ''
        else:
            vr = description['vr']
            name = description['name']
            prop = description['prop']
        value = dataelement.value
        if vr == 'UI':
            # do not rely on pydicom here - we want to use the currently loaded DICOM spec
            value = repr(value)[1:-1]
            value = DataElementDumper.uid_info.get(value, value)
        if vr == 'SQ':
            DataElementDumper.print_element(tag_id, name, vr, prop,
                                            'Sequence with {} item(s)'.format(len(value)))
            DataElementDumper.level += 1
            DataElementDumper.print_sequence(dataelement)
            DataElementDumper.level -= 1
        else:
            DataElementDumper.print_element(tag_id, name, vr, prop, value)

    @staticmethod
    def print_sequence(sequence):
        indent = 2 * DataElementDumper.level
        format_string = '{{}}Item {{:<{}}} [Dataset with {{}} element(s)]'.format(56 - indent)
        for i, dataset in enumerate(sequence):
            print(format_string.format(' ' * indent, i + 1, len(dataset)))
            DataElementDumper.level += 1
            dataset.walk(DataElementDumper.print_dataelement)
            DataElementDumper.level -= 1


def main():
    parser = argparse.ArgumentParser(
        description='Dumps DICOM information dictionary from DICOM file using PS3.6')
    parser.add_argument('dicomfile', help='Path of DICOM file to parse')
    parser.add_argument('--standard-path', '-src',
                        help='Path with the DICOM specs in docbook and json format',
                        default=os.path.join(os.path.expanduser("~"), 'dcm-spec-tools'))
    parser.add_argument('--revision', '-r',
                        help='Standard revision (e.g. "2014c"), year of revision, or "current"',
                        default='current')
    parser.add_argument('--max-value-len', '-ml',
                        help='Maximum string length of displayed values',
                        type=int,
                        default=80)
    args = parser.parse_args()

    edition_reader = EditionReader(args.standard_path)
    destination = edition_reader.get_revision(args.revision)
    if destination is None:
        print('Failed to get DICOM edition {} - aborting'.format(args.revision))
        return 1

    json_path = os.path.join(destination, 'json')
    with open(os.path.join(json_path, edition_reader.dict_info_json)) as info_file:
        dict_info = json.load(info_file)
    with open(os.path.join(json_path, edition_reader.uid_info_json)) as info_file:
        uid_info = json.load(info_file)

    dataset = filereader.read_file(args.dicomfile, stop_before_pixels=True, force=True)
    DataElementDumper(dict_info, uid_info, args.max_value_len).print_dataset(dataset)

    return 0


if __name__ == '__main__':
    exit(main())
