from pydicom.tag import BaseTag


def tag_name_from_id_string(tag_id: str, dict_info: dict | None) -> str:
    """Return a human-readable tag identifier with name when available.

    Parameters
    ----------
    tag_id : str
        Tag identifier string in the form '(gggg,eeee)'.
    dict_info : dict | None
        Dictionary mapping tag IDs to metadata including the 'name' field.

    Returns
    -------
    str
        The tag ID with its human-readable name in parentheses when known.
    """
    if dict_info and tag_id in dict_info:
        return f'{tag_id} ({dict_info[tag_id]["name"]})'
    return tag_id


def tag_name_from_id(tag_id: BaseTag, dict_info: dict | None) -> str:
    """Return a human-readable tag string for a `pydicom` tag.

    Parameters
    ----------
    tag_id : BaseTag
        `pydicom.tag.BaseTag` instance.
    dict_info : dict | None
        Dictionary mapping tag IDs to metadata including the 'name' field.

    Returns
    -------
    str
        The tag ID with its human-readable name in parentheses when known.
    """
    return tag_name_from_id_string(str(tag_id), dict_info)
