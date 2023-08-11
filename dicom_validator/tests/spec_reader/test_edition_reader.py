import os
import time
from pathlib import Path

import pytest

from dicom_validator import __version__
from dicom_validator.spec_reader.edition_reader import EditionReader

pytestmark = pytest.mark.usefixtures("fs")


class MemoryEditionReader(EditionReader):
    """Mock class that gets the file contents in constructor instead of
    downloading them. We test this class to avoid real download connections
    during the test.
    """

    def __init__(self, path, contents=""):
        super(MemoryEditionReader, self).__init__(path=path)
        self.html_contents = contents

    def retrieve(self, html_path):
        with open(html_path, "w") as html_file:
            html_file.write(self.html_contents)


@pytest.fixture
def base_path(fs):
    path = Path("user", "dicom-validator")
    path.mkdir(parents=True)
    yield path


@pytest.fixture
def edition_path(base_path):
    path = base_path / EditionReader.json_filename
    # if not path.exists():
    #     path.write_bytes(b'')
    yield path


@pytest.fixture
def create_edition_file(fs, edition_path, request):
    marker = request.node.get_closest_marker("edition_data")
    if marker is None:
        edition_data = "[]"
    else:
        edition_data = marker.args[0]
    fs.create_file(edition_path, contents=edition_data)


@pytest.fixture
def create_edition_file_over_a_month_old(create_edition_file, edition_path):
    file_time = time.time() - 32 * 24 * 60 * 60.0
    os.utime(edition_path, (file_time, file_time))


@pytest.fixture
def create_edition_file_less_than_a_month_old(create_edition_file, edition_path):
    file_time = time.time() - 27 * 24 * 60 * 60.0
    os.utime(edition_path, (file_time, file_time))


def test_empty_html(base_path, edition_path):
    reader = MemoryEditionReader(base_path, "")
    assert reader.get_editions() is None
    assert not edition_path.exists()


def test_no_html(base_path, edition_path):
    reader = MemoryEditionReader(base_path, "Not html")
    assert reader.get_editions() is None
    assert not edition_path.exists()


def test_no_editions(base_path, edition_path):
    reader = MemoryEditionReader(
        base_path, '<html><A HREF="/medical/dicom/2014a/">test</A><html>'
    )
    assert reader.get_editions() is None
    assert not edition_path.exists()


def test_valid_editions(base_path, edition_path):
    reader = MemoryEditionReader(
        base_path,
        '<html><A HREF="/bla/">2014a</A>'
        "2014b"
        '<a ref="foo">2015</a>'
        '<a ref="foo">2017e</a>',
    )
    assert reader.get_editions() == ["2014a", "2017e"]
    assert edition_path.exists()


@pytest.mark.edition_data('["2014a", "2014c"]')
def test_keep_old_version(base_path, create_edition_file_less_than_a_month_old):
    reader = MemoryEditionReader(base_path, '<html><A HREF="/bla/">2018a</A>')
    assert reader.get_editions() == ["2014a", "2014c"]


@pytest.mark.edition_data('["2014a", "2014c"]')
def test_replace_old_version(base_path, create_edition_file_over_a_month_old):
    reader = MemoryEditionReader(base_path, '<html><A HREF="/bla/">2018a</A>')
    assert reader.get_editions() == ["2018a"]


@pytest.mark.edition_data('["2014a", "2014c"]')
def test_keep_local_version(base_path, create_edition_file_over_a_month_old):
    reader = MemoryEditionReader(base_path, '<html><A HREF="/bla/">2018a</A>')
    assert reader.get_editions(update=False) == ["2014a", "2014c"]


def test_update_if_no_local_version_exists(
    base_path, create_edition_file_over_a_month_old
):
    reader = MemoryEditionReader(base_path, '<html><A HREF="/bla/">2018a</A>')
    assert reader.get_editions(update=False) == ["2018a"]


def test_get_existing_revision(base_path):
    reader = MemoryEditionReader(
        base_path, '<html><A HREF="/bla/">2014a</A>' '<a ref="foo">2014e</a>'
    )
    assert reader.get_edition("2014a") == "2014a"


def test_non_existing_revision(base_path):
    reader = MemoryEditionReader(
        base_path, '<html><A HREF="/bla/">2014a</A>' '<a ref="foo">2014e</a>'
    )
    assert reader.get_edition("2015a") is None


def test_last_revision_in_year(base_path):
    reader = MemoryEditionReader(
        base_path,
        '<html><A HREF="/bla/">2014a</A>'
        '<a ref="foo">2014c</a>'
        '<a ref="foo">2015e</a>',
    )
    assert reader.get_edition("2014") == "2014c"


def test_current_revision(base_path):
    reader = MemoryEditionReader(
        base_path,
        '<html><A HREF="/bla/">2014a</A>'
        '<a ref="foo">2014c</a>'
        '<a ref="foo">2015e</a>',
    )
    assert reader.get_edition("current") == "2015e"


def test_check_none_revision():
    reader = MemoryEditionReader("/foo/bar", "")
    revision, path = reader.check_revision("none")
    assert revision is None
    assert path == Path("/", "foo", "bar")


def test_check_revision_existing(fs):
    base_path = Path("base")
    reader = MemoryEditionReader(base_path, "")
    json_path = base_path / EditionReader.json_filename
    fs.create_file(json_path, contents='["2014a", "2014c", "2015a"]')
    revision, path = reader.check_revision("2014")
    assert revision == "2014c"
    assert path == base_path / "2014c"


def test_check_revision_nonexisting(fs):
    base_path = Path("/foo/bar")
    reader = MemoryEditionReader(base_path, "")
    json_path = base_path / EditionReader.json_filename
    fs.create_file(json_path, contents='["2014a", "2014c", "2015a"]')
    revision, path = reader.check_revision("2016")
    assert revision is None
    assert path is None


def test_is_current(base_path):
    reader = MemoryEditionReader(
        base_path,
        "<html>"
        '<a ref="foo">2014a</a>'
        '<a ref="foo">2014c</a>'
        '<a ref="foo">2015a</a>'
        '<a ref="foo">2015e</a>',
    )
    assert reader.is_current("2015e")
    assert reader.is_current("2015")
    assert not reader.is_current("2015a")
    assert not reader.is_current("2015f")
    assert not reader.is_current("2014")
    assert not reader.is_current("2016")
    assert reader.is_current("current")
    assert reader.is_current(None)


def test_is_current_version(fs, edition_path):
    assert not EditionReader.is_current_version(edition_path)
    version_path = edition_path / "version"
    fs.create_file(version_path, contents="0.2.1")
    assert not EditionReader.is_current_version(edition_path)
    version_path.unlink()
    fs.create_file(version_path, contents=__version__)
    assert EditionReader.is_current_version(edition_path)


def test_write_current_version(fs, edition_path):
    assert not EditionReader.is_current_version(edition_path)
    fs.create_dir(edition_path)
    assert not EditionReader.is_current_version(edition_path)
    EditionReader.write_current_version(edition_path)
    assert EditionReader.is_current_version(edition_path)


def test_recreate_json_if_needed(fs, base_path, edition_path):
    create_json_files_called = 0

    def create_json_files(cls, docbook_path, json_path):
        nonlocal create_json_files_called
        create_json_files_called += 1
        for name in (
            "dict_info.json",
            "iod_info.json",
            "module_info.json",
            "uid_info.json",
        ):
            path = os.path.join(json_path, name)
            if not os.path.exists(path):
                fs.create_file(path)

    docbook_path = base_path / "2014a" / "docbook"
    for chapter_name in ("part03.xml", "part04.xml", "part06.xml"):
        fs.create_file(docbook_path / chapter_name)
    orig_create_json_files = MemoryEditionReader.create_json_files
    try:
        MemoryEditionReader.create_json_files = create_json_files
        reader = MemoryEditionReader(base_path, "")
        fs.create_file(edition_path, contents='["2014a", "2014c", "2015a"]')
        reader.get_revision("2014a")
        assert create_json_files_called == 1
        reader.get_revision("2014a")
        assert create_json_files_called == 2
        json_path = base_path / "2014a" / "json"
        EditionReader.write_current_version(json_path)
        reader.get_revision("2014a")
        assert create_json_files_called == 2
        reader.get_revision("2014a", recreate_json=True)
        assert create_json_files_called == 3
    finally:
        MemoryEditionReader.create_json_files = orig_create_json_files
