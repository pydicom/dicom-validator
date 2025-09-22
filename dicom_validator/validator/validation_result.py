import enum
from dataclasses import dataclass

from dicom_validator.tag_tools import tag_id_string


class ErrorCode(enum.Enum):
    """Defines the kind of error found for a DICOM tag in a module."""

    NoError = 0
    TagMissing = 1  # tag is missing from a module
    TagEmpty = 2  # type 1 tag is empty
    TagUnexpected = 3  # tag is not in any allowed module
    TagNotAllowed = 4  # tag not allowed by a condition
    EnumValueNotAllowed = 5  # value not in the list of allowed enum values
    InvalidValue = 6  # the value failed the VR validation


class ErrorScope(enum.Enum):
    """Defines the scope of an error found for a DICOM tag in a module.
    Some errors are specific to functional groups while having the
    same error code as errors unrelated to functional groups."""

    General = 0
    SharedFuncGroup = 1
    PerFrameFuncGroup = 2
    BothFuncGroups = 3


class TagType(str, enum.Enum):
    """The DICOM tag type used in a specific module."""

    Undefined = "Undefined"  # tag not in an expected module
    Type1 = "1"
    Type1C = "1C"
    Type2 = "2"
    Type2C = "2C"
    Type3 = "3"


class Status(enum.Enum):
    """The result state after validation."""

    Passed = 0  # no errors found in validation
    Failed = 1  # some violations found in validation
    MissingFile = 2  # file to be validated is missing
    InvalidFile = 3  # file to be validated is invalid DICOM
    MissingSOPClassUID = 4  # file to be validated has no SOP Class UID
    UnknownSOPClassUID = 5  # the SOP Class UID in the file to be validated is unknown


@dataclass
class DicomTag:
    """Represents a DICOM tag together with parent sequences, if any."""

    tag: int
    parents: list[int] | None = None

    def __hash__(self):
        return hash(self.tag)

    def __str__(self):
        """String representation for easier debugging."""
        if self.parents:
            s = " / ".join(tag_id_string(tag) for tag in self.parents) + " / "
        else:
            s = ""
        return s + tag_id_string(self.tag)


@dataclass
class TagError:
    """Represents error found for a specific DICOM tag."""

    type: TagType = TagType.Undefined
    code: ErrorCode = ErrorCode.NoError
    scope: ErrorScope = ErrorScope.General
    context: dict | None = None

    def is_error(self):
        return self.code != ErrorCode.NoError


TagErrors = dict[DicomTag, TagError]
ModuleErrors = dict[str, TagErrors]


@dataclass
class ValidationResult:
    """The validation result for a specific DICOM dataset."""

    sop_class_uid: str = ""
    filename = ""
    status: Status = Status.Passed
    errors: int = 0
    module_errors: ModuleErrors | None = None

    def reset(self):
        self.status = Status.Passed
        self.errors = 0
        self.module_errors = ModuleErrors()

    def add_tag_errors(self, module_name: str, tag_errors: TagErrors) -> None:
        self.module_errors = self.module_errors or ModuleErrors()
        self.module_errors.setdefault(module_name, {}).update(tag_errors)
        self.errors += len(tag_errors)
