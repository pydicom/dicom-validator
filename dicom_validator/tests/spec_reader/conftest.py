import json
from pathlib import Path

import pytest

CURRENT_REVISION = "2024c"


def pytest_configure(config):
    """Register the markers used in tests."""
    config.addinivalue_line(
        "markers", "edition_data: provide edition data for edition reader testing."
    )


@pytest.fixture(scope="session")
def fixture_path():
    yield Path(__file__).parent.parent / "fixtures"


@pytest.fixture(scope="session")
def standard_path(fixture_path):
    yield fixture_path / "standard"


@pytest.fixture(scope="session")
def revision(request):
    if hasattr(request, "param"):
        revision = request.param
    else:
        revision = CURRENT_REVISION
    yield revision


@pytest.fixture(scope="session")
def revision_path(standard_path, revision):
    yield standard_path / revision


@pytest.fixture(scope="session")
def spec_fixture_path(revision_path):
    yield revision_path / "docbook"


@pytest.fixture(scope="session")
def dict_info(revision_path):
    from dicom_validator.spec_reader.edition_reader import EditionReader

    json_fixture_path = revision_path / "json"
    with open(
        json_fixture_path / EditionReader.dict_info_json, encoding="utf8"
    ) as info_file:
        info = json.load(info_file)
    yield info


@pytest.fixture(scope="module")
def spec_path(fs_module, spec_fixture_path):
    if not fs_module.exists(spec_fixture_path):
        fs_module.add_real_directory(spec_fixture_path)
    yield spec_fixture_path


@pytest.fixture
def dict_reader(spec_path):
    from dicom_validator.spec_reader.part6_reader import Part6Reader

    yield Part6Reader(spec_path)
