from http.client import HTTPSConnection
from urllib.parse import urlparse

from pydicom.tag import BaseTag

from dicom_validator.tag_tools import tag_name_from_id
from dicom_validator.validator.dicom_info import DicomInfo
from dicom_validator.validator.error_handler import ValidationResultHandlerBase
from dicom_validator.validator.validation_result import (
    ValidationResult,
    TagErrors,
    TagError,
    ErrorScope,
    ErrorCode,
    DicomTag,
)


class HtmlErrorHandler(ValidationResultHandlerBase):
    """An example error handler that writes DICOM errors to a simple HTML page,
    adding links to each affected module."""

    valid_refs: dict[str, str] = {}

    def __init__(self, dicom_info: DicomInfo) -> None:
        self.dicom_info = dicom_info
        self.html = ""
        self.sop_class = ""

    def handle_validation_result_start(self, result: ValidationResult) -> None:
        file_path = f"{result.file_path}<br>" if result.file_path else ""
        self.sop_class = result.sop_class_uid
        self.html += f"<h2>{file_path}SOP Class {self.sop_class}</h2>"

    def handle_validation_result_end(self, result: ValidationResult) -> None:
        self.html = f"<html><body>{self.html}</body></html>"

    @staticmethod
    def url_for_ref(ref) -> str:
        """We always refer to the latest standard. This could be adapted to check for
        the documentation of a specific edition of the standard."""
        return f"https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_{ref}.html"

    @staticmethod
    def url_exists(url):
        p = urlparse(url)
        conn = HTTPSConnection(p.netloc)
        conn.request("HEAD", p.path)
        return conn.getresponse().status < 400

    def valid_url_for_ref(self, ref: str) -> str | None:
        """Returns the URL for the module reference in the DICOM standard.
        All URLs are for PS3.3 of the standard.

        Some of the modules are described on a separate HTML page, some are
        part of a higher level chapter. We are checking for an existing reference
        by sending a HEAD request until we find a valid page."""
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
        self.html += "</ul>\n"

    @staticmethod
    def error_message(error: TagError) -> str:
        match error.scope:
            case ErrorScope.SharedFuncGroup:
                postfix = " in Shared Group"
            case ErrorScope.PerFrameFuncGroup:
                postfix = " in Per-Frame Group"
            case ErrorScope.BothFuncGroups:
                postfix = " in both Shared and Per-Frame Groups"
            case _:
                postfix = ""

        match error.code:
            case ErrorCode.TagMissing:
                return f" is missing{postfix}"
            case ErrorCode.TagEmpty:
                return " is empty"
            case ErrorCode.TagUnexpected:
                return f" is unexpected{postfix}"
            case ErrorCode.TagNotAllowed:
                return f" is not allowed{postfix}"
            case ErrorCode.EnumValueNotAllowed:
                error.context = error.context or {}
                return f" - enum value '{error.context.get('value', '')}' not allowed"
            case ErrorCode.InvalidValue:
                info = ""
                if error.context is not None:
                    value = error.context.get("value", "")
                    vr = error.context.get("VR", "")
                    info = f" '{value}' for VR {vr}"
                return f" has invalid value{info}"
            case _:
                return ""

    def tag_name(self, tag_id: BaseTag) -> str:
        dict_info = self.dicom_info.dictionary
        if str(tag_id) in dict_info:
            return f'{dict_info[str(tag_id)]["name"]} {tag_id}'
        return str(tag_id)

    def handle_tag_error(self, tag_id: DicomTag, error: TagError) -> None:
        self.html += (
            f"<li>{self.tag_name(tag_id.tag)}{self.error_message(error)}</li>\n"
        )

    def handle_tag_parents_start(self, parents: list[BaseTag]) -> None:
        msg = (
            " / ".join(
                tag_name_from_id(tag, self.dicom_info.dictionary) for tag in parents
            )
            + ":"
        )
        self.html += f"<h4>{msg}</h4>"
