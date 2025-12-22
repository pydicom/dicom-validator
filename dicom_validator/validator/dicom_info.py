from dataclasses import dataclass


@dataclass
class DicomInfo:
    """Holds DICOM standard information as read from the JSON cache files.

    Attributes
    ----------
        dictionary:
            The DICOM dictionary from PS3.6
        iods:
            The IOD descriptions for each SOP Class from PS3.3 and PS3.4
        modules:
            The attribute descriptions for each module extracted from PS3.3
    """

    dictionary: dict[str, dict[str, str]]
    iods: dict[str, dict[str, dict]]
    modules: dict[str, dict[str, dict]]
