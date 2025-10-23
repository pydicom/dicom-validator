import argparse
import logging
import sys
from collections.abc import Sequence

from dicom_validator.command_line_utils import dicom_info_from_args, add_edition_args
from dicom_validator.validator.dicom_file_validator import DicomFileValidator


def validate(args: argparse.Namespace) -> int:
    dicom_info = dicom_info_from_args(args)
    if dicom_info is None:
        return 1
    log_level = logging.DEBUG if args.verbose else logging.INFO
    validator = DicomFileValidator(
        dicom_info, log_level, args.force_read, args.suppress_vr_warnings
    )
    error_nr = 0
    for dicom_path in args.dicomfiles:
        error_nr += sum(
            result.errors for result in list(validator.validate(dicom_path).values())
        )
    return int(error_nr)


def main(args: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validates DICOM file IODs")
    parser.add_argument(
        "dicomfiles",
        help="Path(s) of DICOM files or directories to validate",
        nargs="+",
    )
    add_edition_args(parser)
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
    return validate(parser.parse_args(args))


if __name__ == "__main__":
    sys.exit(main())
