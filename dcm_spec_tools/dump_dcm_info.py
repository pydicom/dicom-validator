"""
Dumps tag information from a DICOM file using information in PS3.6.
"""

import argparse
import json
import os

try:
    from pydicom import filereader
except ImportError:
    from dicom import filereader


from dcm_spec_tools.spec_reader.edition_reader import EditionReader


class DataElementDumper(object):
    dict_info = None
    uid_info = {}
    level = 0

    def __init__(self, dict_info, uid_info):
        self.__class__.dict_info = dict_info
        for uid_dict in uid_info.values():
            self.__class__.uid_info.update(uid_dict)

    def print_dataset(self, dataset):
        dataset.walk(self.print_dataelement)

    @staticmethod
    def print_element(tag_id, description, value):
        vm = 1 if value else 0
        if isinstance(value, list):
            vm = len(value)
            value = '\\'.join([str(element) for element in value])
        indent = 2 * DataElementDumper.level
        format_string = '{{}}{{}} {{:{}}} {{}} {{:4}} {{}} [{{}}]'.format(40 - indent)
        print(format_string.format(' ' * indent,
                                   tag_id,
                                   description['name'][:40 - indent],
                                   description['vr'],
                                   vm,
                                   description['prop'],
                                   value))

    @staticmethod
    def print_dataelement(dummy_dataset, dataelement):
        tag_id = '({:04X},{:04X})'.format(dataelement.tag.group, dataelement.tag.element)
        description = DataElementDumper.dict_info.get(tag_id)
        if description is None:
            print('No dictionary entry found for {}'.format(tag_id))
        else:
            value = dataelement.value
            if description['vr'] == 'UI':
                # do not rely on pydicom here - we want to use the currently loaded DICOM spec
                value = repr(value)[1:-1]
                value = DataElementDumper.uid_info.get(value, value)
            if description['vr'] == 'SQ':
                DataElementDumper.print_element(tag_id, description,
                                                'Sequence with {} item(s)'.format(len(value)))
                DataElementDumper.level += 1
                DataElementDumper.print_sequence(dataelement)
                DataElementDumper.level -= 1
            else:
                DataElementDumper.print_element(tag_id, description, value)

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
    args = parser.parse_args()

    _, base_path = EditionReader.get_revision(args.revision, args.standard_path)
    if base_path is None:
        print('DICOM revision {} not found - use get_dcm_specs to download it.'.format(args.revision))
        return 1

    json_path = os.path.join(base_path, 'json')
    with open(os.path.join(json_path, 'dict_info.json')) as info_file:
        dict_info = json.load(info_file)
    with open(os.path.join(json_path, 'uid_info.json')) as info_file:
        uid_info = json.load(info_file)

    dataset = filereader.read_file(args.dicomfile, stop_before_pixels=True, force=True)
    DataElementDumper(dict_info, uid_info).print_dataset(dataset)

    return 0


if __name__ == '__main__':
    exit(main())
