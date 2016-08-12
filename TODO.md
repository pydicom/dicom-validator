## Reader

#### Module definition tables from part 3
* code sequence includes
* basic/enhanced, more? additional attributes
* handle functional groups
* handle other SOP classes not in the table (presentation states etc.)

#### Parse attribute description
* add number of allowed sequences items (1 vs 1-n)
* allowed enum values
* condition for type C attributes

## Validator

#### IOD Validator
* check for mandatory tags
* check for unsupported tags
* check for conditional tags
* check functional groups

#### Other 
* type validation :question:
* value validation (content, size)

## Tools

#### Common stuff
* get input from json files (instead of DICOM spec)
* verbosity :question:
* optional additional config files :question:

#### Validator
* allow several files / directories
* output options (xml:question:)

## Miscellaneous
* make smaller test data for part 3
* check travis - add pylint, check nicer test output
