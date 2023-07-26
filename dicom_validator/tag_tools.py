def tag_name_from_id_string(tag_id_string, dict_info):
    if dict_info and tag_id_string in dict_info:
        return f'{tag_id_string} ({dict_info[tag_id_string]["name"]})'
    return tag_id_string


def tag_name_from_id(tag_id, dict_info):
    tag_id_string = f"({tag_id // 0x10000:04X},{tag_id % 0x10000:04X})"
    return tag_name_from_id_string(tag_id_string, dict_info)
