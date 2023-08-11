# Dicom Validator Release Notes
The released versions correspond to PyPi releases.

## [Version 0.4.0] (Unreleased)

### Features
* added initial support for validating functional group macros
* added option `--recreate-json` for testing purposes (per default, the json files are only
  recreated after a `dicom-validator` version change)

### Fixes
* fixed handling of unverifiable and condition, see [#32](../.. /issues/32)
* fixed too broad matching for "otherwise" condition, see [#29](../.. /issues/29)

### Infrastructure
* Added pre-commit configuration for use with pre-commit hook

## [Version 0.3.5](https://pypi.python.org/pypi/dicom-validator/0.3.5) (2023-07-24)
Fixes several issues with the condition parser.

### Fixes
* Condition parser: multiple or expressions handled correctly
* Condition parser: handle a few more complicated conditions
* Condition parser: handle conditions without values,
  see [#15](../.. /issues/15)
* Condition parser: fixed handling of "zero" and "non-zero" values
  see [#17](../.. /issues/17)
* Condition parser: handle a few more simple expressions
* Condition parser: ignore equality conditions with missing values
  (caused crash, see [#20](../.. /issues/20)

### Changes
* Removed support for Python 3.6, added support for Python 3.11

### Infrastructure
* Added release workflow

## [Version 0.3.4](https://pypi.python.org/pypi/dicom-validator/0.3.4) (2021-11-22)
Fixes a regression introduced with the last release.

### Fixes
- fixed regression that broke the validator command line tool,
  see [#9](../../issues/9))

## [Version 0.3.3](https://pypi.python.org/pypi/dicom-validator/0.3.3) (2021-11-20)
This is a bugfix release.

### Fixes
- all tags including PixelData are now loaded to account for dependencies on PixelData
  see [#6](../../issues/6))

## [Version 0.3.2](https://pypi.python.org/pypi/dicom-validator/0.3.2) (2021-07-30)
Renamed from dcm-spec-tools to dicom-validator and moved into pydicom organization.
No functional changes have been made in this release.

## [Version 0.3.1](https://pypi.org/project/dcm-spec-tools/0.3.1) (2021-01-24)

### Changes
* Removed support for Python 2.7, 3.4 and 3.5

### New Features
* dump_dcm_info: added --max-value-len (-ml) option to configure value display length
* dump_dcm_info: added possibility to dump several files or recurse directories
* dump_dcm_info: added option --show-image-data (-id) to also show the pixel data tag
* dump_dcm_info: added option --show-tags (-t) to show only specific tags
* all: added option --revision local to use latest locally installed revision

### Fixes
* handled empty rows in some editions (caused crash for 2019 edition)
* account for added columns in IOD and UID tables see [#3](../../issues/3))

### Infrastructure
* changed CI to GitHub actions

## [Version 0.3.0](https://pypi.org/project/dcm-spec-tools/0.3.0) (2018-06-26)
(omitted some minor releases)

### New Features
* validate_iods: consolidated / enhanced output

### Fixes
* fixed serialization of conditions

## [Version 0.2.0](https://pypi.org/project/dcm-spec-tools/0.2.0) (2018-04-23)
(omitted some minor releases)

### New Features
* validate_iods: added parsing of condition for optional presence of tags
* validate_iods: added handling of `or` compound conditions
* dump_dcm_info: added dumping of unknown tags
* all: download specs on demand instead of needing a separate command

### Fixes
* several fixes for condition handling

## [Version 0.1.0](https://pypi.org/project/dcm-spec-tools/0.1.0) (2016-12-18)
Initial release
