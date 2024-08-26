import re


def has_tag_error(messages, module_name, tag_id_string, error_kind, text=""):
    if module_name not in messages:
        return False
    for message in messages[module_name]:
        # we allow for both the presence or absence of the tag name,
        # as the tag may not be in the fixture dictionary
        if re.match(rf"Tag \({tag_id_string[1:-1]}\).* (is )?{error_kind}.*", message):
            return text in message if text else True
    return False


def has_error_message(messages, module_name, tag_id_string, error_kind, message):
    if module_name not in messages:
        return False
    for message in messages[module_name]:
        # we allow for both the presence or absence of the tag name,
        # as the tag may not be in the fixture dictionary
        if re.match(rf"Tag \{tag_id_string[:-1]}\).* (is )?{error_kind}.*", message):
            return
    return False
