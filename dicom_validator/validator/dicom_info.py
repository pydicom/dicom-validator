from dataclasses import dataclass


@dataclass
class DicomInfo:
    """Holds DICOM standard information as read from the JSON cache files."""

    dictionary: dict[str, dict[str, str]]
    iods: dict[str, dict[str, dict]]
    modules: dict[str, dict[str, dict]]
