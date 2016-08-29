## Reader

#### Module definition tables from part 3
* handle functional groups :soon: 
* basic/enhanced, more? additional attributes
* handle other SOP classes not in the table (presentation states etc.)

#### Parse module conditions
 * handle required pixel type :soon:
 * handle functional group macros present :soon:

#### Parse attribute description
* add number of allowed sequences items (1 vs 1-n)
* add restriction for number of items where available
* allowed enum values

#### Parse attribute conditions
* collect all used styles for tests :on:
* extend module condition parser for all styles
    * compound conditions :soon:
    * compound conditions where not all parts can be checked
* check for condition who need special handling

## Validator

#### IOD Validator
* module checks
    * check condition for conditional modules :on:
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

#### Dump
* show sequence contents w/o help from pydicom
* add mapping of UIDs to output

## Miscellaneous
* make smaller test data for part 3
