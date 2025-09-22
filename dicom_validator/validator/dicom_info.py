from dataclasses import dataclass


@dataclass
class DicomInfo:
    dictionary: dict[str, dict[str, str]]
    iods: dict[str, dict[str, dict]]
    modules: dict[str, dict[str, dict]]
