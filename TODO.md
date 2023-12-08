## Reader

#### Module definition tables from part 3
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

## Validator

#### IOD Validator
* check tags
    * check condition for 1C/2C attributes
        * several "Required" statements
        * tests for different types
    * unsupported tags
    * repeating groups (60xx)
* add modules requiring missing attributes to result
* allow additional user input specs (fixed name)

#### Other
* type validation :question:
* value validation (content, size)

## Tools

#### Validator
* optional additional config files that replace part of the spec

#### Dump
* add tag length
