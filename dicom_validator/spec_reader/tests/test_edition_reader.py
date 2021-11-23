import logging
import os
import time

import pyfakefs.fake_filesystem_unittest

from dicom_validator import __version__
from dicom_validator.spec_reader.edition_reader import EditionReader


class MemoryEditionReader(EditionReader):
    """Mock class that gets the file contents in constructor instead of
    downloading them. We test this class to avoid real download connections
    during the test.
    """

    def __init__(self, path, contents=''):
        super(MemoryEditionReader, self).__init__(path=path)
        self.html_contents = contents

    def retrieve(self, html_path):
        with open(html_path, 'w') as html_file:
            html_file.write(self.html_contents)


class EditionReaderTest(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        super(EditionReaderTest, self).setUp()
        self.setUpPyfakefs()
        self.base_path = os.path.join('user', 'dicom-validator')
        self.fs.create_dir(self.base_path)
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.DEBUG)

    def create_edition_file_over_a_month_old(self, contents):
        json_path = os.path.join(self.base_path, EditionReader.json_filename)
        self.fs.create_file(json_path, contents=contents)
        file_time = time.time() - 32 * 24 * 60 * 60.0
        os.utime(json_path, (file_time, file_time))

    def create_edition_file_less_than_a_month_old(self, contents):
        json_path = os.path.join(self.base_path, EditionReader.json_filename)
        self.fs.create_file(json_path, contents=contents)
        file_time = time.time() - 27 * 24 * 60 * 60.0
        os.utime(json_path, (file_time, file_time))

    def test_empty_html(self):
        reader = MemoryEditionReader(self.base_path, '')
        self.assertIsNone(reader.get_editions())
        self.assertFalse(
            os.path.exists(os.path.join(self.base_path, reader.json_filename)))

    def test_no_html(self):
        reader = MemoryEditionReader(self.base_path, 'Not html')
        self.assertIsNone(reader.get_editions())
        self.assertFalse(
            os.path.exists(os.path.join(self.base_path, reader.json_filename)))

    def test_no_editions(self):
        reader = MemoryEditionReader(
            self.base_path,
            '<html><A HREF="/medical/dicom/2014a/">test</A><html>')
        self.assertIsNone(reader.get_editions())
        self.assertFalse(
            os.path.exists(os.path.join(self.base_path, reader.json_filename)))

    def test_valid_editions(self):
        reader = MemoryEditionReader(
            self.base_path, '<html><A HREF="/bla/">2014a</A>'
                            '2014b'
                            '<a ref="foo">2015</a>'
                            '<a ref="foo">2017e</a>')
        self.assertEqual(['2014a', '2017e'], reader.get_editions())
        self.assertTrue(
            os.path.exists(os.path.join(self.base_path, reader.json_filename)))

    def test_keep_old_version(self):
        self.create_edition_file_less_than_a_month_old('["2014a", "2014c"]')
        reader = MemoryEditionReader(
            self.base_path, '<html><A HREF="/bla/">2018a</A>')
        self.assertEqual(['2014a', '2014c'], reader.get_editions())

    def test_replace_old_version(self):
        self.create_edition_file_over_a_month_old('["2014a", "2014c"]')
        reader = MemoryEditionReader(
            self.base_path, '<html><A HREF="/bla/">2018a</A>')
        self.assertEqual(['2018a'], reader.get_editions())

    def test_keep_local_version(self):
        self.create_edition_file_over_a_month_old('["2014a", "2014c"]')
        reader = MemoryEditionReader(
            self.base_path, '<html><A HREF="/bla/">2018a</A>')
        self.assertEqual(['2014a', '2014c'], reader.get_editions(update=False))

    def test_update_if_no_local_version_exists(self):
        self.create_edition_file_over_a_month_old('[]')
        reader = MemoryEditionReader(
            self.base_path, '<html><A HREF="/bla/">2018a</A>')
        self.assertEqual(['2018a'], reader.get_editions(update=False))

    def test_get_existing_revision(self):
        reader = MemoryEditionReader(
            self.base_path, '<html><A HREF="/bla/">2014a</A>'
                            '<a ref="foo">2014e</a>')
        self.assertEqual('2014a', reader.get_edition('2014a'))

    def test_non_existing_revision(self):
        reader = MemoryEditionReader(self.base_path,
                                     '<html><A HREF="/bla/">2014a</A>'
                                     '<a ref="foo">2014e</a>')
        self.assertIsNone(reader.get_edition('2015a'))

    def test_last_revision_in_year(self):
        reader = MemoryEditionReader(self.base_path,
                                     '<html><A HREF="/bla/">2014a</A>'
                                     '<a ref="foo">2014c</a>'
                                     '<a ref="foo">2015e</a>')
        self.assertEqual('2014c', reader.get_edition('2014'))

    def test_current_revision(self):
        reader = MemoryEditionReader(self.base_path,
                                     '<html><A HREF="/bla/">2014a</A>'
                                     '<a ref="foo">2014c</a>'
                                     '<a ref="foo">2015e</a>')
        self.assertEqual('2015e', reader.get_edition('current'))

    def test_check_none_revision(self):
        reader = MemoryEditionReader('/foo/bar', '')
        revision, path = reader.check_revision('none')
        self.assertIsNone(revision)
        self.assertEqual('/foo/bar', path)

    def test_check_revision_existing(self):
        base_path = 'base'
        reader = MemoryEditionReader(base_path, '')
        json_path = os.path.join(base_path, EditionReader.json_filename)
        self.fs.create_file(json_path, contents='["2014a", "2014c", "2015a"]')
        revision, path = reader.check_revision('2014')
        self.assertEqual('2014c', revision)
        self.assertEqual(os.path.join(base_path, '2014c'), path)

    def test_check_revision_nonexisting(self):
        base_path = '/foo/bar'
        reader = MemoryEditionReader(base_path, '')
        json_path = os.path.join(base_path, EditionReader.json_filename)
        self.fs.create_file(json_path, contents='["2014a", "2014c", "2015a"]')
        revision, path = reader.check_revision('2016')
        self.assertIsNone(revision)
        self.assertIsNone(path)

    def test_is_current(self):
        reader = MemoryEditionReader(self.base_path, '<html>'
                                                     '<a ref="foo">2014a</a>'
                                                     '<a ref="foo">2014c</a>'
                                                     '<a ref="foo">2015a</a>'
                                                     '<a ref="foo">2015e</a>')
        self.assertTrue(reader.is_current('2015e'))
        self.assertTrue(reader.is_current('2015'))
        self.assertFalse(reader.is_current('2015a'))
        self.assertFalse(reader.is_current('2015f'))
        self.assertFalse(reader.is_current('2014'))
        self.assertFalse(reader.is_current('2016'))
        self.assertTrue(reader.is_current('current'))
        self.assertTrue(reader.is_current(None))

    def test_is_current_version(self):
        json_path = os.path.join(self.base_path, EditionReader.json_filename)
        self.assertFalse(EditionReader.is_current_version(json_path))
        version_path = os.path.join(json_path, 'version')
        self.fs.create_file(version_path, contents='0.2.1')
        self.assertFalse(EditionReader.is_current_version(json_path))
        os.remove(version_path)
        self.fs.create_file(version_path, contents=__version__)
        self.assertTrue(EditionReader.is_current_version(json_path))

    def test_write_current_version(self):
        json_path = os.path.join(self.base_path, EditionReader.json_filename)
        self.fs.create_dir(json_path)
        self.assertFalse(EditionReader.is_current_version(json_path))
        EditionReader.write_current_version(json_path)
        self.assertTrue(EditionReader.is_current_version(json_path))

    def test_recreate_json_if_needed(self):
        self.create_json_files_called = 0

        def create_json_files(cls, docbook_path, json_path):
            self.create_json_files_called += 1
            for name in ('dict_info.json', 'iod_info.json',
                         'module_info.json', 'uid_info.json'):
                path = os.path.join(json_path, name)
                if not os.path.exists(path):
                    self.fs.create_file(path)

        docbook_path = os.path.join(self.base_path, '2014a', 'docbook')
        for chapter_name in ('part03.xml', 'part04.xml', 'part06.xml'):
            self.fs.create_file(os.path.join(docbook_path, chapter_name))
        orig_create_json_files = MemoryEditionReader.create_json_files
        try:
            MemoryEditionReader.create_json_files = create_json_files
            reader = MemoryEditionReader(self.base_path, '')
            json_path = os.path.join(self.base_path,
                                     EditionReader.json_filename)
            self.fs.create_file(json_path,
                                contents='["2014a", "2014c", "2015a"]')
            reader.get_revision("2014a")
            self.assertEqual(1, self.create_json_files_called)
            reader.get_revision("2014a")
            self.assertEqual(2, self.create_json_files_called)
            json_path = os.path.join(self.base_path, '2014a', 'json')
            EditionReader.write_current_version(json_path)
            reader.get_revision("2014a")
            self.assertEqual(2, self.create_json_files_called)
        finally:
            MemoryEditionReader.create_json_files = orig_create_json_files
