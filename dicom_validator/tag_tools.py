def tag_name_from_id_string(tag_id: str, dict_info: dict | None) -> str:
    if dict_info and tag_id in dict_info:
        return f'{tag_id} ({dict_info[tag_id]["name"]})'
    return tag_id


def tag_id_string(tag_id: int) -> str:
    return f"({tag_id // 0x10000:04X},{tag_id % 0x10000:04X})"


def tag_name_from_id(tag_id: int, dict_info: dict | None) -> str:
    return tag_name_from_id_string(tag_id_string(tag_id), dict_info)
