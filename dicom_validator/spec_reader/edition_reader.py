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
            self.logger.setLevel(logging.INFO)

    def editions_path(self) -> Path:
        """Return the path to the JSON file containing the identifiers of
        all found DICOM editions as a comma separated list."""
        return self.path / "editions.json"

    def docbook_path(self, edition: str) -> Path:
        """Return the local path where docbook XML files for an edition reside.

        Parameters
        ----------
        edition : str
            Edition identifier (e.g. '2025c').

        Returns
        -------
        Path
            Directory path to the docbook sources for the given edition.
        """
        return self.path / edition / "docbook"

    def json_path(self, edition: str) -> Path:
        """Return the local path where JSON cache files are stored
        that contain the processed information for a DICOM edition.

        Parameters
        ----------
        edition : str
            Edition identifier (e.g. '2025c').

        Returns
        -------
        Path
            Directory path to the JSON cache for the given edition.
        """
        return self.path / edition / "json"

    def version_path(self, edition: str) -> Path:
        """Return the path of the file that stores the version string
        of the dicom-validator version used to create the JSON cache files.

        Parameters
        ----------
        edition : str
            Edition identifier (e.g. '2025c').

        Returns
        -------
        Path
            Path to the version file within the JSON cache directory.
        """
        return self.json_path(edition) / "version"

    def update_edition(self) -> None:
        """Fetch the list of available DICOM editions and cache it locally.

        Notes
        -----
        Writes `editions.html` as downloaded, and `editions.json` as created
        from the HTML file under the base path.
        Logs a warning if the retrieval of the editions file failed.
        """
        try:
            self.logger.info("Getting DICOM editions...")
            self.retrieve(self.path / self.html_filename)
            self.write_to_json()
        except BaseException as exception:
            self.logger.warning("Failed to get DICOM editions: %s", str(exception))

    def retrieve(self, html_path: Path) -> None:
        """Download the editions HTML page to the given path.

        Parameters
        ----------
        html_path : pathlib.Path
            Destination path for the downloaded `editions.html`.
        """
        html_path.parent.mkdir(exist_ok=True)
        urlretrieve(self.base_url, html_path)

    def get_editions(self, update: bool = True) -> list[str] | None:
        """Return available DICOM edition identifiers, updating the cache if needed.

        Parameters
        ----------
        update : bool, optional
            If `True`, refresh the local cache when it is older than ~30 days
            or missing. If `False`, only read from the cache, creating it only if empty.

        Returns
        -------
        list[str] | None
            Sorted list of edition identifiers (e.g., '2025c'), or `None` if
            unavailable.
        """
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
        """Parse the downloaded editions HTML and extract edition identifiers.

        Returns
        -------
        list[str]
            List of edition identifiers found in the HTML.
        """
        html_path = self.path / self.html_filename
        with open(html_path, encoding="utf8") as html_file:
            contents = html_file.read()
        parser = EditionParser()
        parser.feed(contents)
        parser.close()
        return parser.editions

    def write_to_json(self) -> None:
        """Write the parsed editions list to the JSON cache file."""
        editions = self.read_from_html()
        if editions:
            editions_path = self.editions_path()
            with open(editions_path, "w", encoding="utf8") as json_file:
                json_file.write(json.dumps(editions))

    def get_edition(self, edition_str: str) -> str | None:
        """Resolve an edition selector to a concrete edition identifier, updating the
        available editions if needed.

        Parameters
        ----------
        edition_str : str
            One of:
            - Exact edition name (e.g., '2025c')
            - Year (e.g., '2025') to select the latest available revision of that year
            - 'current' for the latest published edition
            - 'local' for the latest locally available edition

        Returns
        -------
        str | None
            The resolved edition identifier or `None` if it cannot be determined.
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
        """Check whether the given selector refers to the current edition.

        Parameters
        ----------
        edition_str : str
            Edition selector as accepted by `get_edition`.

        Returns
        -------
        bool
            `True` if it resolves to the latest edition, otherwise `False`.
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
        """Resolve an edition selector and return its local base path.

        Parameters
        ----------
        edition_str : str
            Edition selector as accepted by `get_edition`.

        Returns
        -------
        tuple[str | None, Path | None]
            The resolved edition and its local base directory, or `(None, None)`
            if it cannot be resolved.
        """
        edition = self.get_edition(edition_str)
        if edition is not None:
            return edition, self.path / edition
        return None, None

    def get_chapter(self, edition: str, chapter: int) -> bool:
        """Ensure the DocBook file for a given part is present locally,
        downloading it if needed.

        Parameters
        ----------
        edition : str
            Edition identifier (e.g., '2025c').
        chapter : int
            DICOM standard part number (e.g., 3, 4, or 6).

        Returns
        -------
        bool
            `True` if the file exists locally or is downloaded successfully,
            otherwise `False`.
        """
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
        """Load a JSON info file for the given edition.

        Parameters
        ----------
        edition : str
            Edition identifier (e.g., '2025c').
        info_json : str
            File name within the edition's JSON directory.

        Returns
        -------
        dict
            Parsed JSON content.
        """
        json_path = self.json_path(edition)
        with open(json_path / info_json, encoding="utf8") as info_file:
            return json.load(info_file)

    def load_dicom_info(self, edition: str) -> DicomInfo:
        """Load all DICOM info JSON files and build a `DicomInfo` instance.

        Parameters
        ----------
        edition : str
            Edition identifier (e.g., '2025c').

        Returns
        -------
        DicomInfo
            Aggregated information from dictionary, IOD, and module JSON.
        """
        return DicomInfo(
            self.load_info(edition, self.dict_info_json),
            self.load_info(edition, self.iod_info_json),
            self.load_info(edition, self.module_info_json),
        )

    def json_files_exist(self, edition: str) -> bool:
        """Check if all expected JSON files exist for the given edition.

        Parameters
        ----------
        edition : str
            Edition identifier (e.g., '2025c').

        Returns
        -------
        bool
            `True` if all JSON files are present; otherwise `False`.
        """
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
        """Serialize a description dictionary to a pretty-printed JSON string.

        Parameters
        ----------
        description : dict
            Dictionary structure to serialize.

        Returns
        -------
        str
            Pretty-printed JSON string.
        """
        return json.dumps(description, sort_keys=True, indent=2, cls=DefinitionEncoder)

    def create_json_files(self, edition: str) -> None:
        """Parse DocBook sources and (re)create all JSON cache files.

        Parameters
        ----------
        edition : str
            Edition identifier (e.g., '2025c').
        """
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
        """Prepare local files for an edition and return its base path.

        Parameters
        ----------
        edition_str : str
            Edition selector as accepted by `get_edition`.
        recreate_json : bool, optional
            If `True`, force re-creating the JSON cache files regardless of
            their age. Defaults to `False`.
        create_json : bool, optional
            If `True`, create JSON cache files if missing or outdated.
            Defaults to `True`.

        Returns
        -------
        Path | None
            Local base directory of the edition, or `None` on failure.
        """
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
        self.logger.info(f"Using DICOM edition {edition}")
        return destination

    def is_current_version(self, edition: str) -> bool:
        """Check whether the local JSON cache matches this package version exactly.
        We want an exact match as the format is not guaranteed to be downwards compatible.

        Parameters
        ----------
        edition : str
            Edition identifier (e.g., '2025c').

        Returns
        -------
        bool
            `True` if the stored version is equal to this package's `__version__`.
        """
        version_path = self.version_path(edition)
        if not version_path.exists():
            return False
        with open(version_path, encoding="utf8") as f:
            return f.read() == __version__

    def write_current_version(self, edition: str) -> None:
        """Write this package's version string into the edition's cache.

        Parameters
        ----------
        edition : str
            Edition identifier (e.g., '2025c').
        """
        self.json_path(edition).mkdir(parents=True, exist_ok=True)
        with open(self.version_path(edition), "w", encoding="utf8") as f:
            f.write(__version__)
