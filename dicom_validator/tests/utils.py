def has_tag_error(messages, module_name, tag_id_string, error_kind):
    if module_name not in messages:
        return False
    for message in messages[module_name]:
        if message.startswith(f"Tag {tag_id_string} is {error_kind}"):
            return True
    return False
