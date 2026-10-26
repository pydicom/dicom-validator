import pytest

from dicom_validator.validator.validation_result import (
    DicomTag,
    ErrorCode,
    TagError,
    ValidationResult,
)


@pytest.mark.parametrize("initial_errors", [0, 1])
@pytest.mark.parametrize(
    "batches, expected_counts",
    [
        ([(0x00100010,), (0x00100020,)], [1, 2]),
        ([(0x00100010, 0x00100020), (0x00100020, 0x00100030)], [2, 3]),
        ([(0x00100010, 0x00100020), (0x00100010,)], [2, 2]),
        ([(0x00100010, 0x00100020), (0x00100010, 0x00100020)], [2, 2]),
        ([(0x00100010, 0x00100020), ()], [2, 2]),
        ([(0x00100010,), (0x00100020,), (0x00100010,), (0x00100020,)], [1, 2, 2, 2]),
    ],
)
def test_add_tag_errors_accumulates_distinct_tags(
    initial_errors, batches, expected_counts
):
    result = ValidationResult(errors=initial_errors)
    retained_tags = set()

    for batch, expected_count in zip(batches, expected_counts):
        errors = {DicomTag(tag): TagError(code=ErrorCode.TagMissing) for tag in batch}
        result.add_tag_errors("Patient", errors)
        retained_tags.update(errors)

        assert result.errors == initial_errors + expected_count
        assert set(result.module_errors["Patient"]) == retained_tags


def test_add_tag_errors_counts_each_module():
    result = ValidationResult()
    tag = DicomTag(0x00100010)
    errors = {tag: TagError(code=ErrorCode.TagMissing)}

    result.add_tag_errors("Patient", errors)
    result.add_tag_errors("Other", errors)

    assert result.errors == 2
    assert result.module_errors == {"Patient": errors, "Other": errors}


def test_add_tag_errors_updates_existing_error():
    result = ValidationResult()
    tag = DicomTag(0x00100010)
    result.add_tag_errors("Patient", {tag: TagError(code=ErrorCode.TagMissing)})
    replacement = TagError(code=ErrorCode.TagEmpty)

    result.add_tag_errors("Patient", {tag: replacement})

    assert result.errors == 1
    assert result.module_errors["Patient"][tag] is replacement
