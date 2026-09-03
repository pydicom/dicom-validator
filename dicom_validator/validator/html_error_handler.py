import html
from http.client import CannotSendHeader, HTTPSConnection
from typing import ClassVar
from urllib.parse import urlparse

from pydicom.tag import BaseTag

from dicom_validator.tag_tools import tag_name_from_id
from dicom_validator.validator.dicom_info import DicomInfo
from dicom_validator.validator.error_handler import (
    ValidationResultFormatter,
    ValidationResultHandlerBase,
)
from dicom_validator.validator.validation_result import (
    DicomTag,
    TagError,
    TagErrors,
    ValidationResult,
)


class HtmlErrorHandler(ValidationResultHandlerBase):
    """An example error handler that writes DICOM errors to a simple HTML page,
    adding links to each affected module."""

    valid_refs: ClassVar[dict[str, str]] = {}

    def __init__(self, dicom_info: DicomInfo) -> None:
        self.dicom_info = dicom_info
        self._formatter = ValidationResultFormatter(dicom_info.dictionary)
        self.html = ""
        self.sop_class = ""

    def handle_validation_result_start(self, result: ValidationResult) -> None:
        """Start a new HTML section for a validation result."""
        file_path = f"{result.file_path}<br>" if result.file_path else ""
        self.sop_class = result.sop_class_uid
        self.html += f"<h2>{file_path}SOP Class {self.sop_class}</h2>"

    def handle_validation_result_end(self, result: ValidationResult) -> None:
        """Finalize the HTML output for a validation result."""
        self.html = f"<html><body>{self.html}</body></html>"

    def handle_failed_validation_start(self, result: ValidationResult) -> None:
        """Add a paragraph explaining why the validation could not be started."""
        message = self._formatter.failed_validation_message(result)
        self.html += f"<p>{html.escape(message)}</p>"

    @staticmethod
    def url_for_ref(ref) -> str:
        """We always refer to the latest standard. This could be adapted to check for
        the documentation of a specific edition of the standard."""
        return f"https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_{ref}.html"

    @staticmethod
    def url_exists(url):
        """Check whether a URL is reachable via an HTTP HEAD request.

        Parameters
        ----------
        url : str
            Fully-qualified URL.

        Returns
        -------
        bool
            `True` if the server responds with a status code < 400.
        """
        p = urlparse(url)
        conn = HTTPSConnection(p.netloc)
        try:
            conn.request("HEAD", p.path)
        except (ValueError, TypeError, CannotSendHeader):
            return False
        return conn.getresponse().status < 400

    def valid_url_for_ref(self, ref: str) -> str | None:
        """Return a valid URL to the referenced PS3.3 section if it exists.

        Parameters
        ----------
        ref : str
            Section reference label (e.g., 'C.7.6.1').

        Returns
        -------
        str | None
            URL to the best-matching PS3.3 HTML section, or `None` if not found.
        """
        valid_ref = self.valid_refs.get(ref)
        if valid_ref:
            return self.url_for_ref(valid_ref)
        valid_ref = ref
        while True:
            url = self.url_for_ref(valid_ref)
            if self.url_exists(url):
                self.__class__.valid_refs[ref] = valid_ref
                return url
            if "." not in valid_ref:
                return None
            valid_ref = ".".join(valid_ref.split(".")[:-1])

    def handle_module_errors_start(
        self, module_name: str, tag_errors: TagErrors
    ) -> None:
        """Start a new HTML list for errors in a specific module."""
        sop_class_info = self.dicom_info.iods[self.sop_class]
        if module_name in sop_class_info["modules"]:
            ref = sop_class_info["modules"][module_name]["ref"]
        else:
            ref = sop_class_info["group_macros"][module_name]["ref"]
        url = self.valid_url_for_ref(ref)
        if url is None:
            module_ref = module_name
        else:
            module_ref = f'<a href="{url}">{module_name}</a>'
        self.html += f"<h3>{module_ref}</h3>\n<ul>"

    def handle_module_errors_end(self, module_name: str, tag_errors: TagErrors) -> None:
        """Close the HTML list for the current module's errors."""
        self.html += "</ul>\n"

    @staticmethod
    def error_message(error: TagError) -> str:
        """Return a human-readable message fragment for a tag error.

        Parameters
        ----------
        error : TagError
            The error to be rendered.

        Returns
        -------
        str
            A short message starting with a space to append after the tag name.
        """
        message = ValidationResultFormatter().error_message(error)
        return html.escape(message).replace("\n", "<br>")

    def tag_name(self, tag_id: BaseTag) -> str:
        """Return a human-readable name for a tag, including its ID.

        Parameters
        ----------
        tag_id : BaseTag
            DICOM tag identifier.

        Returns
        -------
        str
            A string like '(0010,0010) (Patient's Name)' when known, otherwise
            the tag ID string.
        """
        return tag_name_from_id(tag_id, self.dicom_info.dictionary)

    def handle_tag_error(self, tag_id: DicomTag, error: TagError) -> None:
        """Append a single tag error as an HTML list item."""
        self.html += (
            f"<li>{self.tag_name(tag_id.tag)}{self.error_message(error)}</li>\n"
        )

    def handle_tag_parents_start(self, parents: list[BaseTag]) -> None:
        """Start a new section header listing parent sequence tags."""
        msg = (
            " / ".join(
                tag_name_from_id(tag, self.dicom_info.dictionary) for tag in parents
            )
            + ":"
        )
        self.html += f"<h4>{msg}</h4>"
