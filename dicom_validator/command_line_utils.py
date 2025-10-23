import argparse
import os
import warnings
from pathlib import Path

from dicom_validator.spec_reader.edition_reader import EditionReader
from dicom_validator.validator.dicom_info import DicomInfo


def add_edition_args(parser: argparse.ArgumentParser) -> None:
    """Add edition related arguments to argument parser."""
    parser.add_argument(
        "--standard-path",
        "-src",
        help="Base path with the DICOM specs in docbook and json format",
        default=str(Path.home() / "dicom-validator"),
    )
    parser.add_argument(
        "--edition",
        "-e",
        help='Standard edition (e.g. "2014c"), year of '
        'edition, "current" or "local" (latest '
        "locally installed)",
        default="current",
    )
    parser.add_argument(
        "--revision",
        "-r",
        help="Standard edition - deprecated, use --edition instead",
    )


def dicom_info_from_args(args: argparse.Namespace) -> DicomInfo | None:
    """Retrieve DICOM info using edition related parser arguments."""
    if not os.path.exists(args.standard_path):
        print(f"Invalid standard path {args.standard_path} - aborting")
    if args.revision:
        edition_str = args.revision
        warnings.warn(
            "--revision is deprecated, use --edition instead", DeprecationWarning
        )
    else:
        edition_str = args.edition
    edition_reader = EditionReader(args.standard_path)
    edition = edition_reader.get_edition(edition_str)
    if edition is None:
        print(f"Invalid DICOM edition {edition_str} - aborting")
        return None
    destination = edition_reader.get_edition_path(edition, args.recreate_json)
    if destination is None:
        print(f"Failed to get DICOM edition {edition_str} - aborting")
        return None
    return edition_reader.load_dicom_info(edition)
