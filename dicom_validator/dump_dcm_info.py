"""
Dumps tag information from a DICOM file using information in PS3.6.
"""

import argparse
import os
import re
from pathlib import Path
import sys

from pydicom import config, dcmread
from pydicom.errors import InvalidDicomError

from dicom_validator.spec_reader.edition_reader import EditionReader


class DataElementDumper:
    tag_regex = re.compile(r"(\(?[\dabcdefABCDEF]{4}), *([\dabcdefABCDEF]{4})\)?")

    def __init__(self, dicom_info, max_value_len, show_image_data, tags):
        self.dicom_info = dicom_info
        self.max_value_len = max_value_len
        self.level = 0
        self.show_image_data = show_image_data

        self.uid_info = {}
        for uid_dict in dicom_info.dictionary.values():
            self.uid_info.update(uid_dict)

        tags = tags or []
        self.tags = []
        for tag in tags:
            match = self.tag_regex.match(tag)
            if match:
                self.tags.append(f"({match.group(1)},{match.group(2)})")
            else:
                matching = [
                    tag_id
                    for tag_id in dicom_info.dictionary
                    if dicom_info.dictionary[tag_id]["name"].replace(" ", "") == tag
                ]
                if matching:
                    self.tags.append(matching[0])
                else:
                    print(f"{tag} is not a valid tag expression - ignoring")

    def print_dataset(self, dataset):
        dataset.walk(
            lambda data_set, data_elem: self.print_dataelement(data_set, data_elem)
        )

    def print_element(self, tag_id, name, vr, prop, value):
        if self.tags and tag_id not in self.tags:
            return False
        vm = 1 if value else 0
        if isinstance(value, list):
            vm = len(value)
            value = "\\".join([str(element) for element in value])
        if isinstance(value, bytes):
            value = str(value)[2:-1]
        if isinstance(value, str) and len(value) > self.max_value_len:
            value = value[: self.max_value_len] + "..."

        indent = 2 * self.level
        format_string = "{{}}{{}} {{:{}}} {{}} {{:4}} {{}} [{{}}]".format(40 - indent)
        print(
            format_string.format(
                " " * indent, tag_id, name[: 40 - indent], vr, vm, prop, value
            )
        )
        return True

    def print_dataelement(self, _, dataelement):
        tag_id = f"({dataelement.tag.group:04X},{dataelement.tag.element:04X})"
        description = self.dicom_info.dictionary.get(tag_id)
        if description is None:
            name = "[Unknown]"
            vr = dataelement.VR
            prop = ""
        else:
            vr = description["vr"]
            name = description["name"]
            prop = description["prop"]
        value = dataelement.value
        if vr == "UI":
            # do not rely on pydicom here - we want to use the
            # currently loaded DICOM spec
            value = repr(value)[1:-1]
            value = self.uid_info.get(value, value)
        if vr == "SQ":
            if self.print_element(
                tag_id, name, vr, prop, f"Sequence with {len(value)} item(s)"
            ):
                self.level += 1
                self.print_sequence(dataelement)
                self.level -= 1
        else:
            self.print_element(tag_id, name, vr, prop, value)

    def print_sequence(self, sequence):
        indent = 2 * self.level
        format_string = "{{}}Item {{:<{}}} [Dataset with {{}} element(s)]".format(
            56 - indent
        )
        for i, dataset in enumerate(sequence):
            print(format_string.format(" " * indent, i + 1, len(dataset)))
            self.level += 1
            dataset.walk(
                lambda data_set, data_elem: self.print_dataelement(data_set, data_elem)
            )
            self.level -= 1

    def dump_file(self, file_path):
        try:
            # dcmread calls validate_value by default. If values don't match
            # required VR (value representation), it emits a warning but
            # does not provide the tag and value that caused the warning.
            # There is no point in warning the user when dumping the tags.
            # The validate_iods.py script handles these separately.
            config.settings.reading_validation_mode = config.IGNORE
            print("\n" + file_path)
            dataset = dcmread(
                file_path, stop_before_pixels=self.show_image_data, force=True
            )
            self.print_dataset(dataset)
        except (InvalidDicomError, KeyError):
            print(f"{file_path} is not a valid DICOM file - skipping.")

    def dump_directory(self, dir_path):
        for root, _, names in os.walk(dir_path):
            for name in names:
                self.dump_file(os.path.join(root, name))


def main():
    parser = argparse.ArgumentParser(
        description="Dumps DICOM information dictionary from " "DICOM file using PS3.6"
    )
    parser.add_argument(
        "dicomfiles", help="Path(s) of DICOM files or directories to parse", nargs="+"
    )
    parser.add_argument(
        "--standard-path",
        "-src",
        help="Path with the DICOM specs in docbook " "and json format",
        default=str(Path.home() / "dicom-validator"),
    )
    parser.add_argument(
        "--revision",
        "-r",
        help='Standard revision (e.g. "2014c"), year of '
        'revision, "current" or "local" (latest '
        "locally installed)",
        default="current",
    )
    parser.add_argument(
        "--max-value-len",
        "-ml",
        help="Maximum string length of displayed values",
        type=int,
        default=80,
    )
    parser.add_argument(
        "--show-tags",
        "-t",
        help="Show only output for the searched tags. "
        "Tags can be in the format ####,#### or as the "
        'dictionary name (e.g. "PatientName").',
        nargs="*",
    )
    parser.add_argument(
        "--show-image-data",
        "-id",
        action="store_false",
        help="Also show the image data tag (slower)",
    )
    parser.add_argument(
        "--recreate-json",
        action="store_true",
        help="Force recreating the JSON information from the DICOM specs",
        default=False,
    )
    args = parser.parse_args()

    edition_reader = EditionReader(args.standard_path)
    destination = edition_reader.get_revision(args.revision, args.recreate_json)
    if destination is None:
        print(f"Failed to get DICOM edition {args.revision} - aborting")
        return 1

    json_path = destination / "json"
    dicom_info = EditionReader.load_dicom_info(json_path)
    dumper = DataElementDumper(
        dicom_info, args.max_value_len, args.show_image_data, args.show_tags
    )
    for dicom_path in args.dicomfiles:
        if not os.path.exists(dicom_path):
            print('\n"%s" does not exist - skipping', dicom_path)
        else:
            if os.path.isdir(dicom_path):
                dumper.dump_directory(dicom_path)
            else:
                dumper.dump_file(dicom_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
