import re


def has_tag_error(messages, module_name, tag_id_string, error_kind):
    if module_name not in messages:
        return False
    for message in messages[module_name]:
        # we allow for both the presence or absence of the tag name,
        # as the tag may not be in the fixture dictionary
        if re.match(rf"Tag \{tag_id_string[:-1]}\).* is {error_kind}.*", message):
            return True
    return False
