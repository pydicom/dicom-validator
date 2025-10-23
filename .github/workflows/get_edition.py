import argparse

from dicom_validator.spec_reader.edition_reader import EditionReader


def get_edition(edition, path):
    reader = EditionReader(path)
    # we want to recreate the json files for each test run,
    # so we don't need them cached
    reader.get_edition_path(edition, create_json=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Downloads an edition of the DICOM standard"
    )
    parser.add_argument(
        "edition",
        help="Standard edition",
    )
    parser.add_argument(
        "path",
        help="Path for the DICOM specs",
    )
    args = parser.parse_args()
    get_edition(args.edition, args.path)
