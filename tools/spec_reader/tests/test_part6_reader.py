import os
import unittest

import pyfakefs.fake_filesystem_unittest

from part6_reader import Part6Reader


class Part6ReaderTest(pyfakefs.fake_filesystem_unittest.TestCase):
    doc_contents = None

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(os.path.dirname(__file__), 'fixtures', 'part06_excerpt.xml')) as f:
            cls.doc_contents = f.read()

    def setUp(self):
        super(Part6ReaderTest, self).setUp()
        self.setUpPyfakefs()
        spec_path = os.path.join('dicom', 'specs')
        part6_path = os.path.join(spec_path, 'part06.xml')
        self.fs.CreateFile(part6_path, contents=self.doc_contents)
        self.reader = Part6Reader(spec_path)

    def test_undefined_id(self):
        self.assertIsNone(self.reader.data_element(11, 11))

    def test_data_element(self):
        element = self.reader.data_element(0x0008, 0x0005)
        self.assertIsNotNone(element)
        self.assertEqual('Specific Character Set', element['name'])
        self.assertEqual('CS', element['vr'])
        self.assertEqual('1-n', element['vm'])

    def test_data_elements(self):
        elements = self.reader.data_elements()
        self.assertEqual(4, len(elements))


if __name__ == '__main__':
    unittest.main()
