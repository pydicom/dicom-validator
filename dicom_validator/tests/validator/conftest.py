import json
import logging
from pathlib import Path

import pytest

from dicom_validator.spec_reader.edition_reader import EditionReader
from dicom_validator.validator.iod_validator import DicomInfo

CURRENT_REVISION = "2023c"


def pytest_configure(config):
    """Register the markers used in tests."""
    config.addinivalue_line(
        "markers", "tag_set: provide a list of tags for validator tests."
    )
    config.addinivalue_line(
        "markers", "per_frame_macros: defines tags in per-frame functional groups."
    )
    config.addinivalue_line(
        "markers", "shared_macros: defines tags in shared functional groups."
    )


@pytest.fixture(scope="session")
def json_fixture_path():
    yield Path(__file__).parent.parent / "fixtures" / CURRENT_REVISION / "json"


@pytest.fixture(scope="session")
def iod_info(json_fixture_path):
    with open(json_fixture_path / EditionReader.iod_info_json) as info_file:
        info = json.load(info_file)
    yield info


@pytest.fixture(scope="session")
def dict_info(json_fixture_path):
    with open(json_fixture_path / EditionReader.dict_info_json) as info_file:
        info = json.load(info_file)
    yield info


@pytest.fixture(scope="session")
def module_info(json_fixture_path):
    with open(json_fixture_path / EditionReader.module_info_json) as info_file:
        info = json.load(info_file)
    yield info


@pytest.fixture(scope="session")
def dicom_info(dict_info, module_info, iod_info):
    yield DicomInfo(dict_info, iod_info, module_info)


@pytest.fixture(scope="module")
def disable_logging():
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.DEBUG)
