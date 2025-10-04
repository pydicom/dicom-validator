from pydicom.tag import BaseTag


def tag_name_from_id_string(tag_id: str, dict_info: dict | None) -> str:
    if dict_info and tag_id in dict_info:
        return f'{tag_id} ({dict_info[tag_id]["name"]})'
    return tag_id


def tag_name_from_id(tag_id: BaseTag, dict_info: dict | None) -> str:
    return tag_name_from_id_string(str(tag_id), dict_info)
