## Reader

#### Module definition tables from part 3
* handle functional groups
* basic/enhanced, more? additional attributes
* handle other SOP classes not in the table (presentation states etc.)

#### Parse attribute description
* add number of allowed sequences items (1 vs 1-n)
* add restriction for number of items where available
* allowed enum values

#### Parse attribute and module conditions
* collect all used styles for tests :on:
* extend module condition parser for all styles
    * compound conditions :on:
* check for condition who need special handling
    * pixel type
    * functional group macros present

## Validator

#### IOD Validator
* module checks
    * check condition for conditional modules :on:
    * check optional modules for consistence
* check tags
    * check condition for 1C/2C attributes
        * several "Required" statements
        * tests for different types
    * unsupported tags
    * functional groups
    * repeating groups (60xx)
* add modules requiring missing attributes to result
* allow additional user input specs (fixed name)

#### Other 
* type validation :question:
* value validation (content, size)

## Tools

#### Validator
* verbosity levels :on:
    * warning level: show only missing / unexpected attributes
    * info level: show checked modules where errors occur
    * info level: show failed condition (create from json)
    * debug level: show each checked module
* optional additional config files that replace part of the spec

#### Dump
* add tag length
* add image tag
