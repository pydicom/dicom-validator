from pathlib import Path

import pytest

from dicom_validator.spec_reader.part3_reader import Part3Reader
from dicom_validator.spec_reader.spec_reader import (
    SpecReaderLookupError, SpecReaderParseError, SpecReaderFileError
)


@pytest.fixture(scope="module")
def doc_contents(spec_fixture_path):
    with open(spec_fixture_path / 'part03.xml', 'rb') as spec_file:
        contents = spec_file.read()
    yield contents


@pytest.fixture
def reader(fs, doc_contents):
    spec_path = Path('dicom', 'specs')
    part3_path = spec_path / 'part03.xml'
    fs.create_file(part3_path, contents=doc_contents)
    yield Part3Reader(spec_path)


@pytest.mark.usefixtures("fs")
class TestReadPart3:

    def test_read_empty_doc_file(self, fs):
        spec_path = Path('/var/dicom/specs')
        spec_path.mkdir(parents=True)
        fs.create_file(spec_path / 'part03.xml')
        spec_reader = Part3Reader(spec_path)
        with pytest.raises(SpecReaderFileError):
            spec_reader.iod_description('A.16')

    def test_read_invalid_doc_file(self, fs):
        spec_path = Path('/var/dicom/specs')
        spec_path.mkdir(parents=True)
        fs.create_file(spec_path / 'part03.xml',
                       contents='Not an xml')
        spec_reader = Part3Reader(spec_path)
        with pytest.raises(SpecReaderFileError):
            spec_reader.iod_description('A.6')

    def test_read_incomplete_doc_file(self, fs):
        spec_path = Path('/var/dicom/specs')
        spec_path.mkdir(parents=True)
        fs.create_file(
            spec_path / 'part03.xml',
            contents='<book xmlns="http://docbook.org/ns/docbook">\n</book>')
        reader = Part3Reader(spec_path)
        with pytest.raises(SpecReaderParseError):
            reader.iod_description('A.6')

    def test_lookup_sop_class(self, reader):
        with pytest.raises(SpecReaderLookupError):
            reader.iod_description('A.0')
        description = reader.iod_description(chapter='A.3')
        assert description is not None
        assert 'title' in description
        assert description['title'] == 'Computed Tomography Image IOD'

    def test_get_iod_modules(self, reader):
        description = reader.iod_description(chapter='A.38.1')
        assert 'modules' in description
        modules = description['modules']
        assert len(modules) == 27
        assert 'General Equipment' in modules
        module = modules['General Equipment']
        assert module['ref'] == 'C.7.5.1'
        assert module['use'] == 'M'

    def test_optional_iod_module(self, reader):
        description = reader.iod_description(chapter='A.38.1')
        assert 'modules' in description
        modules = description['modules']
        assert 'Clinical Trial Subject' in modules
        module = modules['Clinical Trial Subject']
        assert module['ref'] == 'C.7.1.3'
        assert module['use'] == 'U'

    def test_iod_descriptions(self, reader):
        descriptions = reader.iod_descriptions()
        assert len(descriptions) == 4
        assert 'A.3' in descriptions
        assert 'A.18' in descriptions
        assert 'A.38.1' in descriptions

    def test_module_description(self, reader):
        with pytest.raises(SpecReaderLookupError):
            reader.module_description('C.9.9.9')
        description = reader.module_description('C.7.1.3')
        assert len(description) == 9
        assert '(0012,0031)' in description
        assert description['(0012,0031)']['name'] == 'Clinical Trial Site Name'
        assert description['(0012,0031)']['type'] == '2'

    def test_sequence_inside_module_description(self, reader):
        description = reader.module_description('C.7.2.3')
        assert len(description) == 3
        assert '(0012,0083)' in description
        assert 'items' in description['(0012,0083)']
        sequence_description = description['(0012,0083)']['items']
        assert len(sequence_description) == 3
        assert '(0012,0020)' in sequence_description
        assert sequence_description['(0012,0020)']['name'] == 'Clinical Trial Protocol ID'
        assert sequence_description['(0012,0020)']['type'] == '1C'

    def test_referenced_macro(self, reader):
        # module has 2 directly included attributes
        # and 21 attribute in referenced table
        description = reader.module_description('C.7.6.3')
        assert len(description) == 3
        assert '(0028,7FE0)' in description
        assert 'include' in description
        assert 'C.7-11b' in description['include']
        description = reader.module_description('C.7-11b')
        assert len(description) == 21
        assert '(7FE0,0010)' in description

    def test_module_descriptions(self, reader):
        descriptions = reader.module_descriptions()
        # 42 modules from 3 classes (20/23/26) with overlapping
        # common modules + 27 referenced macros
        assert len(descriptions) == 69
