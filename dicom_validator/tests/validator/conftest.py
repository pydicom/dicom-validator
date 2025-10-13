import json
import logging
from pathlib import Path

import pydicom
import pytest
from pydicom import (
    dcmread,
    dcmwrite,
    FileMetaDataset,
    DataElement,
    Sequence,
    Dataset,
    uid,
)
from pydicom.datadict import dictionary_VR
from pydicom.filebase import DicomBytesIO
from pydicom.tag import Tag

from dicom_validator.spec_reader.edition_reader import EditionReader
from dicom_validator.validator.dicom_info import DicomInfo
from dicom_validator.validator.iod_validator import IODValidator

CURRENT_EDITION = "2025d"


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
def standard_path():
    yield Path(__file__).parent.parent / "fixtures" / "standard"


@pytest.fixture(scope="session")
def json_fixture_path(standard_path):
    yield standard_path / CURRENT_EDITION / "json"


@pytest.fixture(scope="session")
def iod_info(json_fixture_path):
    with open(
        json_fixture_path / EditionReader.iod_info_json, encoding="utf8"
    ) as info_file:
        info = json.load(info_file)
    yield info


@pytest.fixture(scope="session")
def dict_info(json_fixture_path):
    with open(
        json_fixture_path / EditionReader.dict_info_json, encoding="utf8"
    ) as info_file:
        info = json.load(info_file)
    yield info


@pytest.fixture(scope="session")
def module_info(json_fixture_path):
    with open(
        json_fixture_path / EditionReader.module_info_json, encoding="utf8"
    ) as info_file:
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


def new_data_set(tags, *, top_level: bool = True):
    """Create a DICOM data set with the given attributes"""
    tags = tags or {}
    data_set = Dataset()
    if not tags:
        return data_set
    for tag, value in tags.items():
        tag = Tag(tag)  # raises for invalid tag
        try:
            vr = dictionary_VR(tag)
        except KeyError:
            vr = "LO"
        if vr == "SQ":
            items = []
            for item_tags in value:
                items.append(new_data_set(item_tags, top_level=False))
            value = Sequence(items)
        data_set[tag] = DataElement(tag, vr, value)
    if not top_level:
        # this is a sequence item
        return data_set

    # write the dataset into a file and read it back to ensure the real behavior
    if "SOPInstanceUID" not in data_set:
        data_set.SOPInstanceUID = "1.2.3"
    data_set.file_meta = FileMetaDataset()
    data_set.file_meta.TransferSyntaxUID = uid.ExplicitVRLittleEndian
    fp = DicomBytesIO()
    kwargs = (
        {"write_like_original": False}
        if int(pydicom.__version_info__[0]) < 3
        else {"enforce_file_format": True}
    )
    dcmwrite(fp, data_set, **kwargs)
    fp.seek(0)
    return dcmread(fp)


@pytest.fixture
def validator(dicom_info, request):
    marker = request.node.get_closest_marker("tag_set")
    if marker is None:
        tag_set = {}
    else:
        tag_set = marker.args[0]
    data_set = new_data_set(tag_set)
    return IODValidator(data_set, dicom_info, log_level=logging.WARNING)
