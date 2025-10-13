import datetime
import html.parser as html_parser
import json
import logging
import re
import sys
import time
from abc import ABC
from pathlib import Path

from collections.abc import Iterable
from urllib.request import urlretrieve

from dicom_validator import __version__
from dicom_validator.spec_reader.part3_reader import Part3Reader
from dicom_validator.spec_reader.part4_reader import Part4Reader
from dicom_validator.spec_reader.part6_reader import Part6Reader
from dicom_validator.spec_reader.serializer import DefinitionEncoder
from dicom_validator.validator.dicom_info import DicomInfo


class EditionParser(html_parser.HTMLParser, ABC):
    edition_re = re.compile(r"\d\d\d\d[a-h]")

    def __init__(self) -> None:
        html_parser.HTMLParser.__init__(self)
        self._in_anchor: bool = False
        self.editions: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: Iterable[tuple[str, str | None]]
    ) -> None:
        if tag == "a":
            self._in_anchor = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._in_anchor = False

    def handle_data(self, data: str) -> None:
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

    def __init__(self, path: str | Path | None = None) -> None:
        if path is not None:
            self.path = Path(path)
        else:
            self.path = Path.home() / "dicom-validator"
        self.logger = logging.getLogger()
        if not self.logger.hasHandlers():
            self.logger.addHandler(logging.StreamHandler(sys.stdout))

    def editions_path(self) -> Path:
        return self.path / "editions.json"

    def docbook_path(self, edition: str) -> Path:
        return self.path / edition / "docbook"

    def json_path(self, edition: str) -> Path:
        return self.path / edition / "json"

    def version_path(self, edition: str) -> Path:
        return self.json_path(edition) / "version"

    def update_edition(self) -> None:
        try:
            self.logger.info("Getting DICOM editions...")
            self.retrieve(self.path / self.html_filename)
            self.write_to_json()
        except BaseException as exception:
            self.logger.warning("Failed to get DICOM editions: %s", str(exception))

    def retrieve(self, html_path: Path) -> None:
        html_path.parent.mkdir(exist_ok=True)
        urlretrieve(self.base_url, html_path)

    def get_editions(self, update: bool = True) -> list[str] | None:
        editions_path = self.editions_path()
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
        return None

    def read_from_html(self) -> list[str]:
        html_path = self.path / self.html_filename
        with open(html_path, encoding="utf8") as html_file:
            contents = html_file.read()
        parser = EditionParser()
        parser.feed(contents)
        parser.close()
        return parser.editions

    def write_to_json(self) -> None:
        editions = self.read_from_html()
        if editions:
            editions_path = self.editions_path()
            with open(editions_path, "w", encoding="utf8") as json_file:
                json_file.write(json.dumps(editions))

    def get_edition(self, edition_str: str) -> str | None:
        """Get the edition matching the edition or None.
        The edition can be the edition name, the year of the edition,
        'current', or 'local'.
        """
        editions_opt = self.get_editions(edition_str != "local")
        if not editions_opt:
            return None
        editions = sorted(editions_opt)
        if edition_str in editions:
            return edition_str
        if len(edition_str) == 4:
            for edition in reversed(editions):
                if edition.startswith(edition_str):
                    return edition
        if edition_str == "current" or edition_str == "local":
            return editions[-1]
        return None

    def is_current(self, edition_str: str) -> bool:
        """Get the edition matching the edition or None.
        The edition can be the edition name, the year of the edition,
        or 'current'.
        """
        if edition_str is None:
            return True
        editions_opt = self.get_editions(edition_str != "local")
        if not editions_opt:
            return False
        editions = sorted(editions_opt)
        if edition_str in editions:
            return edition_str == editions[-1]
        if len(edition_str) == 4:
            return editions[-1].startswith(edition_str)
        if edition_str == "current":
            return True
        return False

    def get_edition_and_path(self, edition_str: str) -> tuple[str | None, Path | None]:
        edition = self.get_edition(edition_str)
        if edition is not None:
            return edition, self.path / edition
        return None, None

    def get_chapter(self, edition: str, chapter: int) -> bool:
        file_path = self.docbook_path(edition) / f"part{chapter:02}.xml"
        if file_path.exists():
            return True
        edition_part = "current" if self.is_current(edition) else edition
        url = "{0}{1}/source/docbook/part{2:02}/part{2:02}.xml".format(
            self.base_url, edition_part, chapter
        )
        try:
            self.logger.info(f"Downloading DICOM spec {edition} PS3.{chapter}...")
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

    def load_info(self, edition: str, info_json: str) -> dict:
        json_path = self.json_path(edition)
        with open(json_path / info_json, encoding="utf8") as info_file:
            return json.load(info_file)

    def load_dicom_info(self, edition: str) -> DicomInfo:
        return DicomInfo(
            self.load_info(edition, self.dict_info_json),
            self.load_info(edition, self.iod_info_json),
            self.load_info(edition, self.module_info_json),
        )

    def json_files_exist(self, edition: str) -> bool:
        json_path = self.json_path(edition)
        for filename in (
            self.dict_info_json,
            self.module_info_json,
            self.iod_info_json,
            self.uid_info_json,
        ):
            if not (json_path / filename).exists():
                return False
        return True

    @staticmethod
    def dump_description(description: dict) -> str:
        return json.dumps(description, sort_keys=True, indent=2, cls=DefinitionEncoder)

    def create_json_files(self, edition: str) -> None:
        json_path = self.json_path(edition)
        docbook_path = self.docbook_path(edition)
        self.logger.info(
            "Creating JSON excerpts from docbook files - this may take a while..."
        )
        start_time = time.time()
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
        self.logger.info(
            f"Parsing docbooks took {time.time() - start_time:.1f} seconds."
        )
        start_time = time.time()
        with open(json_path / self.iod_info_json, "w", encoding="utf8") as info_file:
            info_file.write(self.dump_description(definition))
        with open(json_path / self.module_info_json, "w", encoding="utf8") as info_file:
            info_file.write(self.dump_description(part3reader.module_descriptions()))
        with open(json_path / self.dict_info_json, "w", encoding="utf8") as info_file:
            info_file.write(self.dump_description(dict_info))
        with open(json_path / self.uid_info_json, "w", encoding="utf8") as info_file:
            info_file.write(self.dump_description(part6reader.all_uids()))
        self.write_current_version(edition)
        self.logger.info(
            f"Writing json files took {time.time() - start_time:.1f} seconds."
        )
        self.logger.info("Done!")

    def get_edition_path(
        self, edition_str: str, recreate_json: bool = False, create_json: bool = True
    ) -> Path | None:
        edition, destination = self.get_edition_and_path(edition_str)
        if destination is None or edition is None:
            self.logger.error(f"DICOM edition {edition} not found.")
            return None

        docbook_path = self.docbook_path(edition)
        docbook_path.mkdir(parents=True, exist_ok=True)
        json_path = self.json_path(edition)
        json_path.mkdir(parents=True, exist_ok=True)

        # download the docbook files
        for chapter in [3, 4, 6]:
            if not self.get_chapter(
                edition=edition,
                chapter=chapter,
            ):
                return None

        if create_json and (
            not self.json_files_exist(edition)
            or not self.is_current_version(edition)
            or recreate_json
        ):
            self.create_json_files(edition)
        print(f"Using DICOM edition {edition}")
        return destination

    def is_current_version(self, edition: str) -> bool:
        version_path = self.version_path(edition)
        if not version_path.exists():
            return False
        with open(version_path, encoding="utf8") as f:
            return f.read() >= __version__

    def write_current_version(self, edition: str) -> None:
        self.json_path(edition).mkdir(parents=True, exist_ok=True)
        with open(self.version_path(edition), "w", encoding="utf8") as f:
            f.write(__version__)
