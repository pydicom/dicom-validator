import json
import logging
from pathlib import Path

import pytest

from dicom_validator.spec_reader.edition_reader import EditionReader

CURRENT_REVISION = "2021d"


@pytest.fixture(scope="session")
def fixture_path():
    yield Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def spec_fixture_path(fixture_path):
    yield fixture_path / CURRENT_REVISION / "docbook"


@pytest.fixture(scope="session")
def json_fixture_path(fixture_path):
    yield fixture_path / CURRENT_REVISION / "json"


@pytest.fixture(scope="session")
def dicom_fixture_path(fixture_path):
    return fixture_path / "dicom"


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


@pytest.fixture(scope="module")
def disable_logging():
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.DEBUG)
