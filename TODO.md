## Reader

#### Module definition tables from part 3
* code sequence includes
* basic/enhanced, more? additional attributes
* handle functional groups
* handle other SOP classes not in the table (presentation states etc.)

#### Parse module conditions
 * handle required pixel type
 * handle functional group macros present

#### Parse attribute description
* add number of allowed sequences items (1 vs 1-n)
* allowed enum values

#### Parse attribute conditions
* collect all used styles for tests :o:
* extend module condition parser for all styles
    * compound conditions
    * compound conditions where not all parts can be checked
* add special handling for code value related tags

## Validator

#### IOD Validator
* module checks
    * check condition for conditional modules :o:
    * check optional modules for consistence
* check tags
    * check condition for 1C/2C attributes - test missing
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
