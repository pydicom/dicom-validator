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

#### Parse module conditions
 * fix parsing of conditions with links
 * handle required pixel type
 * handle functional group macros present
 * add parse result to part3 reader results

#### Parse tag conditions
* extend module condition parser
* collect all used styles for tests

## Validator

#### IOD Validator
* module checks
    * mandatory modules (mostly done)
    * check condition for conditional modules
    * check optional modules for consistence
* check tags
    * mandatory tags (mostly done)
    * check condition for 1C/2C attributes
    * unsupported tags
    * functional groups
    * repeating groups (60xx)
* allow additional user input specs (fixed name)

#### Other 
* type validation :question:
* value validation (content, size)

## Tools

#### Validator
* allow several files / directories
* output options (xml:question:)
* get input from json files (instead of DICOM spec)
* verbosity :question:
* optional additional config files that replace part of the spec

## Miscellaneous
* make smaller test data for part 3
* check travis - add pylint, check nicer test output
