import enum
from dataclasses import dataclass

from pydicom.tag import BaseTag


class ErrorCode(enum.Enum):
    """Defines the kind of error found for a DICOM tag in a module."""

    NoError = 0
    TagMissing = 1
    """Mandatory tag is missing from a module"""
    TagEmpty = 2
    """Type 1 or 1C tag is empty"""
    TagUnexpected = 3
    """Tag is not in any allowed module"""
    TagNotAllowed = 4
    """Tag not allowed by a condition"""
    EnumValueNotAllowed = 5
    """Value not in the list of allowed enum values"""
    InvalidValue = 6
    """The value failed the VR validation"""


class ErrorScope(enum.Enum):
    """Defines the scope of an error found for a DICOM tag in a module.
    Some errors are specific to functional groups while having the
    same error code as errors unrelated to functional groups."""

    General = 0
    """Tag not inside a functional group sequence"""
    SharedFuncGroup = 1
    """Tag inside the shared the functional group sequence"""
    PerFrameFuncGroup = 2
    """Tag inside the per-frame the functional group sequence"""
    BothFuncGroups = 3
    """Tag in both shared and per-frame functional group sequences"""


class TagType(str, enum.Enum):
    """The DICOM tag type used in a specific module."""

    Undefined = "Undefined"
    Type1 = "1"
    """Tag must exist and not be empty"""
    Type1C = "1C"
    """Tag must exist and not be empty if the condition is fulfilled"""
    Type2 = "2"
    """Tag must exist"""
    Type2C = "2C"
    """Tag must exist if the condition is fulfilled"""
    Type3 = "3"
    """Tag is optional"""


class Status(enum.Enum):
    """The result state after validation."""

    Passed = 0
    """No errors found in validation"""
    Failed = 1
    """Some violations found in validation"""
    MissingFile = 2
    """File to be validated is missing"""
    InvalidFile = 3
    """File to be validated is invalid DICOM"""
    MissingSOPClassUID = 4
    """File to be validated has no SOP Class UID"""
    UnknownSOPClassUID = 5
    """The SOP Class UID in the file to be validated is unknown"""


@dataclass
class DicomTag:
    """Represents a DICOM tag together with parent sequences, if any.

    Attributes
    ----------
    tag:
        The DICOM tag ID
    parents:
        List of parent DICOM tag IDs if the tag is inside a sequence, or `None`
    """

    tag: BaseTag
    parents: list[BaseTag] | None = None

    def __init__(self, tag: int, parents: list[int] | None = None):
        self.tag = BaseTag(tag)
        self.parents = [BaseTag(p) for p in parents] if parents else None

    def __hash__(self):
        return hash(self.tag + (sum(self.parents) if self.parents else 0))

    def __str__(self):
        """String representation for easier debugging."""
        if self.parents:
            s = " / ".join(str(tag) for tag in self.parents) + " / "
        else:
            s = ""
        return s + str(self.tag)

    def __lt__(self, other):
        """Comparison operator. Makes sure that tags with the
        same parent sequences are ordered adjacently."""
        if self.parents:
            if other.parents:
                if self.parents == other.parents:
                    return self.tag < other.tag
                return self.parents < other.parents
            return self.parents[0] < other.tag
        if other.parents:
            return self.tag < other.parents[0]
        return self.tag < other.tag


@dataclass
class TagError:
    """Represents the error found for a specific DICOM tag.

    Attributes
    ----------
    type:
        Type of tag (1, 1C, 2, 2C, 3)
    code:
        Error code of the tag error
    scope:
        Scope (root or functional groups) where the tag error occurred
    context:
        Contains additional information for some errors
    """

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
    """The validation result for a specific DICOM dataset.

    Attributes
    ----------
    sop_class_uid:
        The SOP Class UID of the dataset
    file_path:
        The path of the DICOM file if known
    status:
        Status of the validation
    errors:
        Number of validation errors found
    module_errors:
        Tag errors per module, where module name is the key, and a dictionary with errors
        per DICOM tag ID is the value
    """

    sop_class_uid: str = ""
    file_path: str = ""
    status: Status = Status.Passed
    errors: int = 0
    module_errors: ModuleErrors | None = None

    def reset(self):
        self.status = Status.Passed
        self.errors = 0
        self.module_errors = ModuleErrors()

    def add_tag_errors(self, module_name: str, tag_errors: TagErrors) -> None:
        self.module_errors = self.module_errors or ModuleErrors()
        nr_module_errors = len(self.module_errors.get(module_name, []))
        self.module_errors.setdefault(module_name, {}).update(tag_errors)
        self.errors += len(tag_errors) - nr_module_errors
