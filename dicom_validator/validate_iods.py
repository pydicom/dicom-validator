import argparse
import logging
from pathlib import Path
import sys

from dicom_validator.spec_reader.edition_reader import EditionReader
from dicom_validator.validator.dicom_file_validator import DicomFileValidator


from collections.abc import Sequence


def validate(args: argparse.Namespace, base_path: str | Path) -> int:
    json_path = Path(base_path, "json")
    dicom_info = EditionReader.load_dicom_info(json_path)
    log_level = logging.DEBUG if args.verbose else logging.INFO
    validator = DicomFileValidator(
        dicom_info, log_level, args.force_read, args.suppress_vr_warnings
    )
    error_nr = 0
    for dicom_path in args.dicomfiles:
        error_nr += sum(
            len(error) for error in list(validator.validate(dicom_path).values())
        )
    return int(error_nr)


def main(args: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validates DICOM file IODs")
    parser.add_argument(
        "dicomfiles",
        help="Path(s) of DICOM files or directories " "to validate",
        nargs="+",
    )
    parser.add_argument(
        "--standard-path",
        "-src",
        help="Base path with the DICOM specs in docbook " "and json format",
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
        "--force-read",
        action="store_true",
        help="Force-read DICOM files without DICOM header",
        default=False,
    )
    parser.add_argument(
        "--recreate-json",
        action="store_true",
        help="Force recreating the JSON information from the DICOM specs",
        default=False,
    )
    parser.add_argument(
        "--suppress-vr-warnings",
        "-svr",
        action="store_true",
        help="Suppress warnings for values not matching value representation (VR)",
        default=False,
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Outputs diagnostic information"
    )
    parsed_args = parser.parse_args(args)

    edition_reader = EditionReader(parsed_args.standard_path)
    destination = edition_reader.get_revision(
        parsed_args.revision, parsed_args.recreate_json
    )
    if destination is None:
        print(f"Failed to get DICOM edition {parsed_args.revision} - aborting")
        return 1

    return validate(parsed_args, destination)


if __name__ == "__main__":
    sys.exit(main())
