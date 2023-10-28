import argparse

from dicom_validator.spec_reader.edition_reader import EditionReader


def get_revision(revision, path):
    reader = EditionReader(path)
    # we want to recreate the json files for each test run
    # so we don't want them cached
    reader.get_revision(revision, create_json=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Downloads a revision of the DICOM standard"
    )
    parser.add_argument(
        "revision",
        help="Standard revision",
    )
    parser.add_argument(
        "path",
        help="Path for the DICOM specs",
    )
    args = parser.parse_args()
    get_revision(args.revision, args.path)
