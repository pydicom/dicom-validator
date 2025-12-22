How the validator works
=======================
DICOM basics
~~~~~~~~~~~~
This explains some basics of the DICOM standard that are used by the validator.
The parts of the DICOM standard are referred to as *PS3.3* for part 3 of the current
standard, *PS3.4* for part 4 etc., as it is commonly used.

SOP classes and IODs
....................
All checks are performed based on the *SOP Class UID* found in the dataset.
Each DICOM dataset must contain exactly one *SOP Class UID* that defines the kind of the
contained data. Each UID is mapped to a *SOP Class* name in PS3.6.
Each SOP Class is related to an *Information Object Definition* (IOD), which are
described in the DICOM standard. Information about SOP Classes and IODs can be found in
`PS3.4, chapter 6 <https://dicom.nema.org/medical/dicom/current/output/chtml/part04/chapter_6.html>`__.
This part also contains
`a table <https://dicom.nema.org/medical/dicom/current/output/chtml/part04/sect_B.5.html>`__
which relates SOP Classes to IOD descriptions (which reside in PS3.3).

IOD Modules
...........
Each IOD matching a specific *SOP Class UID* defines a number of modules that can be part of that
IOD. A module in this context is a collection of attributes related to a specific property of the DICOM
instance. Each module defines the usage in the given IOD:

* *M* (mandatory) modules must be present for the IOD to conform to the standard
* *C* (conditional) modules must be present if a specific given condition is fulfilled,
  otherwise they may be present, or may only be present if an additional condition allows it
* *U* (user defined) modules are optional modules, that may or may not be present

Any module not listed for the IOD is not allowed to be present.

Each module is defined by a module table, also located in PS3.3. Modules specific to a UID are defined
with the IOD definition, modules used by more than one IOD are listed separately in PS3.3.
Most modules are used by more than one IOD. For example, the
`Patient <https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.html#sect_C.7.1.1>`__
module is used in all IODs, the
`Image Pixel <https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.3.html>`__
module is used by all IODs that contain pixel data, and the
`Multi-frame Functional Groups <https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.16.html>`__
module is used by all enhanced storage IODs.

Module Attributes
.................
Each attribute is related to a DICOM tag as defined in the DICOM dictionary in PS3.6.
An attribute definition in the module attribute table comprises:

* *Attribute Name*: The name of the related DICOM tag
* *Tag*: The tag ID of the related DICOM tag
* *Type*: Defines the usage of the tag in the module, simular to the usage of the module itself;
  the following types are defined:

  * *Type 1*: the attribute is mandatory and must contain a value
  * *Type 1C*: the attribute is mandatory and must contain a value, *if* the given condition is fulfilled
  * *Type 2*: the attribute is mandatory, but can be empty
  * *Type 2C*: the attribute is mandatory, *if* the given condition is fulfilled, but can be empty
  * *Type 3*: the attribute is optional
* *Attribute Description*: Contains a verbal description of the attribute, including allowed values
  and the condition for type 1C and 2C attributes

Usage in the tool
~~~~~~~~~~~~~~~~~
Parts of the standard used
..........................
For the validation, PS3.3, PS3.4 and PS3.6 are used. Specifically, the
`data dictionary <https://dicom.nema.org/medical/dicom/current/output/chtml/part06/chapter_6.html>`__
in PS3.6 is used to get information about DICOM tags (e.g. tag name, VR and VM), and
`SOP Class names <https://dicom.nema.org/medical/dicom/current/output/chtml/part06/chapter_A.html>`__
from SOP class UIDs. While this information is also contained in ``pydicom``, we want to use exactly
the information from a given revision of the standard (which may be newer or older as the one used
by ``pydicom``).
`PS3.4 <https://dicom.nema.org/medical/dicom/current/output/chtml/part04/chapter_6.html>`__
is used to map the SOP classes to IOD descriptions, and the IOD and module descriptions are
extracted from `PS3.3 <https://dicom.nema.org/medical/dicom/current/output/chtml/part03/chapter_A.html>`__.

.. _validation_logic:

Validation logic
................
For a given *SOP Class*, the presence of any module defined for the corresponding IOD is checked by
looking up the attributes defined for these modules. Any attribute not belonging to a module of the
IOD is seen as unexpected and generates a validation error.
For conditionally required (C) modules the condition is checked, and if it matches, it is handled
the same way as mandatory (M) modules (see also the chapter about condition handling below).
If the module has an additional condition that defines if it may be present if not required, this
condition is also checked, and if not fulfilled, the module is seen as not allowed, otherwise it is
handled like a user-defined (U) module.
For any present module and for all required modules (even if not present), all type 1 and 2 tags are
checked for presence. The logic for type 1C and 2C attributes follows the logic for modules of type C,
described above. Any missing type 1 or 2 attribute generates a validation error; the same holds for
required type 1C and 2C attributes. Likewise, any present type 1C and 2C attribute not allowed by a
condition generates a validation error.
Additionally, type 1/1C attributes are required to have a value, so an empty attribute also generates
a validation error.
Any allowed attribute that has a defined enum as the value is also checked for a correct enum value.

Validation errors
.................
According to the described logic, the following validation errors are defined:

* *Tag missing*: A mandatory attribute is missing from a module present in the dataset, or the
  attribute is mandatory in a missing mandatory module
* *Tag empty*: A type 1 or 1C attribute has no value
* *Tag unexpected*: A tag is found in the dataset that does not belong to any allowed module
* *Tag not allowed*: A tag is found that is not allowed by a condition
* *Enum value not allowed*: A tag has a value that is not one of the allowed enum values for this tag
* *Invalid value*: The tag value fails the VR validation as performed by ``pydicom``

Condition parsing
.................
Textual conditions appear both for modules of type C, and for type 1C and 2C attributes.
The conditions define when a module or attribute is required, and sometimes contain a second condition
defining if the module or attribute is allowed if the main condition is not fulfilled.
The conditions are formulated in plain language with no formalization, though most of them are written
in a consistent style. Parsing the condition is done using a PEG grammar parser
(`pyparsing <https://pypi.org/project/pyparsing/>`__). The grammar tries to accommodate for the different
conditions appearing in the standard and generates a formalized version of the condition. This works for
most of the conditions dealing with concrete tags in the same DICOM dataset. These conditions check for
the presence or absence of tags, for specific tag values, or limit the range of numeric tag values.
There can be composite conditions (comprised of sub-conditions combined via AND or OR), which may also
be nested.
However, there is a number of conditions that cannot be handled by the validator. These include:

* descriptions of the kind of patients, studies or equipment that is not directly contained in tags, e.g.:

  * the Patient is an animal
  * the image has been calibrated
  * this Instance was created by conversion from a DICOM source
  * application level confidentiality is needed
* descriptions that refer to the current dataset, but that cannot (yet) be handled, e.g.:

  * the code value is not a URN or URL
  * the aspect ratio values do not have a ratio of 1:1
  * the selected content is not a Sequence Item
* the information is related to other DICOM files (e.g. referenced images)
* the parsing failed because the condition is too complicated, unexpected, or due to a bug

Currently, 35-40% of all conditions in the standard are of this kind.
All such conditions are handled conservatively, e.g. a 1C/2C tag is handled as a type 3 tag.
If the unparseable condition is part of an AND condition, it is ignored, if it is part of an OR
condition, the whole condition is deemed unparseable.
All that means that some validations may not be found, and the number of found validations may be
too small.

Handling of functional group sequences
......................................
`Functional group sequences <https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.16.html>`__
need special handling due to the fact that tags may reside both in the shared and in the per-frame
functional group sequence. Each item in the per-frame functional groups is checked separately, and
if a mandatory tag is missing, it is looked up in the shared functional group sequence. The opposite
case, that a tag is missing in the shared functional group, but present in the per-frame functional
group is not strictly allowed according to the standard, but also handled and not seen as an error.
Functional group handling may still need some tweaking, so this behavior may still change in future versions.
