import datetime
import html.parser as html_parser
import json
import logging
import re
import sys
from abc import ABC
from pathlib import Path
from urllib.request import urlretrieve

from dicom_validator import __version__
from dicom_validator.spec_reader.part3_reader import Part3Reader
from dicom_validator.spec_reader.part4_reader import Part4Reader
from dicom_validator.spec_reader.part6_reader import Part6Reader
from dicom_validator.spec_reader.serializer import DefinitionEncoder
from dicom_validator.validator.iod_validator import DicomInfo


class EditionParser(html_parser.HTMLParser, ABC):
    edition_re = re.compile(r"\d\d\d\d[a-h]")

    def __init__(self):
        html_parser.HTMLParser.__init__(self)
        self._in_anchor = False
        self.editions = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._in_anchor = True

    def handle_endtag(self, tag):
        if tag == "a":
            self._in_anchor = False

    def handle_data(self, data):
        if self._in_anchor and self.edition_re.match(data):
            self.editions.append(data)


class EditionReader:
    base_url = "https://dicom.nema.org/medical/dicom/"
    html_filename = "editions.html"
    json_filename = "editions.json"
    iod_info_json = "iod_info.json"
    module_info_json = "module_info.json"
    dict_info_json = "dict_info.json"
    uid_info_json = "uid_info.json"

    def __init__(self, path):
        self.path = Path(path)
        self.logger = logging.getLogger()
        if not self.logger.hasHandlers():
            self.logger.addHandler(logging.StreamHandler(sys.stdout))

    def update_edition(self):
        try:
            self.logger.info("Getting DICOM editions...")
            self.retrieve(self.path / self.html_filename)
            self.write_to_json()
        except BaseException as exception:
            self.logger.warning("Failed to get DICOM editions: %s", str(exception))

    def retrieve(self, html_path):
        html_path.parent.mkdir(exist_ok=True)
        urlretrieve(self.base_url, html_path)

    def get_editions(self, update=True):
        editions_path = self.path / self.json_filename
        if editions_path.exists():
            if update:
                today = datetime.datetime.today()
                modified_date = datetime.datetime.fromtimestamp(
                    editions_path.stat().st_mtime
                )
                # no need to update the edition dir more than once a month
                update = (today - modified_date).days > 30
            else:
                with open(editions_path, encoding="utf8") as f:
                    update = not json.load(f)
        else:
            update = True
        if update:
            self.update_edition()
        if editions_path.exists():
            with open(editions_path, encoding="utf8") as json_file:
                return json.load(json_file)

    def read_from_html(self):
        html_path = self.path / self.html_filename
        with open(html_path, encoding="utf8") as html_file:
            contents = html_file.read()
        parser = EditionParser()
        parser.feed(contents)
        parser.close()
        return parser.editions

    def write_to_json(self):
        editions = self.read_from_html()
        if editions:
            json_path = self.path / self.json_filename
            with open(json_path, "w", encoding="utf8") as json_file:
                json_file.write(json.dumps(editions))

    def get_edition(self, revision):
        """Get the edition matching the revision or None.
        The revision can be the edition name, the year of the edition,
        'current', or 'local'.
        """
        editions = sorted(self.get_editions(revision != "local"))
        if revision in editions:
            return revision
        if len(revision) == 4:
            for edition in reversed(editions):
                if edition.startswith(revision):
                    return edition
        if revision == "current" or revision == "local":
            return editions[-1]

    def is_current(self, revision):
        """Get the edition matching the revision or None.
        The revision can be the edition name, the year of the edition,
        or 'current'.
        """
        if revision is None:
            return True
        editions = sorted(self.get_editions(revision != "local"))
        if revision in editions:
            return revision == editions[-1]
        if len(revision) == 4:
            return editions[-1].startswith(revision)
        if revision == "current":
            return True
        return False

    def check_revision(self, revision):
        revision = self.get_edition(revision)
        if revision:
            return revision, self.path / revision
        return None, None

    def get_chapter(self, revision, chapter, destination, is_current):
        file_path = destination / f"part{chapter:02}.xml"
        if file_path.exists():
            return True
        revision_dir = "current" if is_current else revision
        url = "{0}{1}/source/docbook/part{2:02}/part{2:02}.xml".format(
            self.base_url, revision_dir, chapter
        )
        try:
            print(f"Downloading DICOM spec {revision} PS3.{chapter}...")
            urlretrieve(url, file_path)
            return True
        except BaseException as exception:
            self.logger.error(f"Failed to download {url}: {exception}")
            if file_path.exists():
                try:
                    file_path.unlink()
                except OSError:
                    self.logger.warning(
                        f"Failed to remove incomplete file {file_path}."
                    )
            return False

    @staticmethod
    def load_info(json_path, info_json):
        with open(json_path / info_json, encoding="utf8") as info_file:
            return json.load(info_file)

    @classmethod
    def load_dicom_info(cls, json_path):
        return DicomInfo(
            cls.load_info(json_path, cls.dict_info_json),
            cls.load_info(json_path, cls.iod_info_json),
            cls.load_info(json_path, cls.module_info_json),
        )

    @classmethod
    def json_files_exist(cls, json_path):
        for filename in (
            cls.dict_info_json,
            cls.module_info_json,
            cls.iod_info_json,
            cls.uid_info_json,
        ):
            if not (json_path / filename).exists():
                return False
        return True

    @classmethod
    def dump_description(cls, description):
        return json.dumps(description, sort_keys=True, indent=2, cls=DefinitionEncoder)

    @classmethod
    def create_json_files(cls, docbook_path, json_path):
        print("Creating JSON excerpts from docbook files...")
        part6reader = Part6Reader(docbook_path)
        dict_info = part6reader.data_elements()
        part3reader = Part3Reader(docbook_path, dict_info)
        part4reader = Part4Reader(docbook_path)
        iod_info = part3reader.iod_descriptions()
        chapter_info = part4reader.iod_chapters()
        definition = {}
        for chapter in iod_info:
            if chapter in chapter_info:
                for uid in chapter_info[chapter]:
                    definition[uid] = iod_info[chapter]
        with open(json_path / cls.iod_info_json, "w", encoding="utf8") as info_file:
            info_file.write(cls.dump_description(definition))
        with open(json_path / cls.module_info_json, "w", encoding="utf8") as info_file:
            info_file.write(cls.dump_description(part3reader.module_descriptions()))
        with open(json_path / cls.dict_info_json, "w", encoding="utf8") as info_file:
            info_file.write(cls.dump_description(dict_info))
        with open(json_path / cls.uid_info_json, "w", encoding="utf8") as info_file:
            info_file.write(cls.dump_description(part6reader.all_uids()))
        cls.write_current_version(json_path)
        print("Done!")

    def get_revision(self, revision, recreate_json=False, create_json=True):
        revision, destination = self.check_revision(revision)
        if destination is None:
            self.logger.error(f"DICOM revision {revision} not found.")
            return

        docbook_path = destination / "docbook"
        docbook_path.mkdir(parents=True, exist_ok=True)
        json_path = destination / "json"
        json_path.mkdir(parents=True, exist_ok=True)

        # download the docbook files
        for chapter in [3, 4, 6]:
            if not self.get_chapter(
                revision=revision,
                chapter=chapter,
                destination=docbook_path,
                is_current=self.is_current(revision),
            ):
                return

        if create_json and (
            not self.json_files_exist(json_path)
            or not self.is_current_version(json_path)
            or recreate_json
        ):
            self.create_json_files(docbook_path, json_path)
        print(f"Using DICOM revision {revision}")
        return destination

    @staticmethod
    def is_current_version(json_path):
        version_path = json_path / "version"
        if not version_path.exists():
            return False
        with open(version_path, encoding="utf8") as f:
            return f.read() >= __version__

    @staticmethod
    def write_current_version(json_path):
        version_path = json_path / "version"
        with open(version_path, "w", encoding="utf8") as f:
            f.write(__version__)
