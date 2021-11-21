import os
import unittest

import pyfakefs.fake_filesystem_unittest

from dicom_validator.spec_reader.part3_reader import Part3Reader
from dicom_validator.spec_reader.spec_reader import (
    SpecReaderLookupError, SpecReaderParseError, SpecReaderFileError
)
from dicom_validator.tests.test_utils import spec_fixture_path


class ReadPart3Test(pyfakefs.fake_filesystem_unittest.TestCase):
    doc_contents = None

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(spec_fixture_path(),
                               'part03.xml'), 'rb') as spec_file:
            cls.doc_contents = spec_file.read()

    def setUp(self):
        super(ReadPart3Test, self).setUp()
        self.setUpPyfakefs()
        spec_path = os.path.join('dicom', 'specs')
        part3_path = os.path.join(spec_path, 'part03.xml')
        self.fs.create_file(part3_path, contents=self.doc_contents)
        self.reader = Part3Reader(spec_path)

    def test_read_empty_doc_file(self):
        spec_path = '/var/dicom/specs'
        os.makedirs(spec_path)
        self.fs.create_file(os.path.join(spec_path, 'part03.xml'))
        spec_reader = Part3Reader(spec_path)
        self.assertRaises(SpecReaderFileError,
                          spec_reader.iod_description, 'A.16')

    def test_read_invalid_doc_file(self):
        spec_path = '/var/dicom/specs'
        os.makedirs(spec_path)
        self.fs.create_file(os.path.join(spec_path, 'part03.xml'),
                            contents='Not an xml')
        spec_reader = Part3Reader(spec_path)
        self.assertRaises(SpecReaderFileError,
                          spec_reader.iod_description, 'A.6')

    def test_read_incomplete_doc_file(self):
        spec_path = '/var/dicom/specs'
        os.makedirs(spec_path)
        self.fs.create_file(os.path.join(
            spec_path, 'part03.xml'),
            contents='<book xmlns="http://docbook.org/ns/docbook">\n</book>')
        reader = Part3Reader(spec_path)
        self.assertRaises(SpecReaderParseError, reader.iod_description, 'A.6')

    def test_lookup_sop_class(self):
        self.assertRaises(SpecReaderLookupError,
                          self.reader.iod_description, 'A.0')
        description = self.reader.iod_description(chapter='A.3')
        self.assertIsNotNone(description)
        self.assertTrue('title' in description)
        self.assertEqual(description['title'], 'Computed Tomography Image IOD')

    def test_get_iod_modules(self):
        description = self.reader.iod_description(chapter='A.38.1')
        self.assertIn('modules', description)
        modules = description['modules']
        self.assertEqual(27, len(modules))
        self.assertIn('General Equipment', modules)
        module = modules['General Equipment']
        self.assertEqual('C.7.5.1', module['ref'])
        self.assertEqual('M', module['use'])

    def test_optional_iod_module(self):
        description = self.reader.iod_description(chapter='A.38.1')
        self.assertIn('modules', description)
        modules = description['modules']
        self.assertIn('Clinical Trial Subject', modules)
        module = modules['Clinical Trial Subject']
        self.assertEqual('C.7.1.3', module['ref'])
        self.assertEqual('U', module['use'])

    def test_iod_descriptions(self):
        descriptions = self.reader.iod_descriptions()
        self.assertEqual(4, len(descriptions))
        self.assertIn('A.3', descriptions)
        self.assertIn('A.18', descriptions)
        self.assertIn('A.38.1', descriptions)

    def test_module_description(self):
        self.assertRaises(SpecReaderLookupError,
                          self.reader.module_description, 'C.9.9.9')
        description = self.reader.module_description('C.7.1.3')
        self.assertEqual(9, len(description))
        self.assertIn('(0012,0031)', description)
        self.assertEqual('Clinical Trial Site Name',
                         description['(0012,0031)']['name'])
        self.assertEqual('2', description['(0012,0031)']['type'])

    def test_sequence_inside_module_description(self):
        description = self.reader.module_description('C.7.2.3')
        self.assertEqual(3, len(description))
        self.assertIn('(0012,0083)', description)
        self.assertIn('items', description['(0012,0083)'])
        sequence_description = description['(0012,0083)']['items']
        self.assertEqual(3, len(sequence_description))
        self.assertIn('(0012,0020)', sequence_description)
        self.assertEqual('Clinical Trial Protocol ID',
                         sequence_description['(0012,0020)']['name'])
        self.assertEqual('1C', sequence_description['(0012,0020)']['type'])

    def test_referenced_macro(self):
        # module has 2 directly included attributes
        # and 21 attribute in referenced table
        description = self.reader.module_description('C.7.6.3')
        self.assertEqual(3, len(description))
        self.assertIn('(0028,7FE0)', description)
        self.assertIn('include', description)
        self.assertIn('C.7-11b', description['include'])
        description = self.reader.module_description('C.7-11b')
        self.assertEqual(21, len(description))
        self.assertIn('(7FE0,0010)', description)

    def test_module_descriptions(self):
        descriptions = self.reader.module_descriptions()
        # 42 modules from 3 classes (20/23/26) with overlapping
        # common modules + 27 referenced macros
        self.assertEqual(69, len(descriptions))


if __name__ == '__main__':
    unittest.main()
