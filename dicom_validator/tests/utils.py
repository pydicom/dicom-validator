from dicom_validator.validator.validation_result import ValidationResult, ErrorCode


def has_tag_error(
    result: ValidationResult,
    module_name: str,
    tag_id: int,
    error_code: ErrorCode,
    context: dict | None = None,
):
    if not result.module_errors or module_name not in result.module_errors:
        return False
    tag_errors = result.module_errors[module_name]
    found_ids = [tag for tag in tag_errors if tag.tag == tag_id]
    if not found_ids:
        return False
    tag_error = tag_errors[found_ids[0]]
    if tag_error.code != error_code:
        return False
    if context is not None:
        for key, value in context.items():
            if not tag_error.context or key not in tag_error.context:
                return False
            if tag_error.context[key] != value:
                return False
    return True
