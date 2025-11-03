from collections.abc import Generator
from xml.etree import ElementTree

import pytest
from pydicom.valuerep import VR

from dicom_validator.spec_reader.condition import (
    Condition,
    ConditionType,
    ConditionOperator,
)
from dicom_validator.spec_reader.condition_parser import ConditionParser
from dicom_validator.spec_reader.enum_parser import EnumParser
from dicom_validator.spec_reader.part3_reader import Part3Reader


@pytest.fixture
def chapter_c(dict_reader, spec_path):
    yield Part3Reader(spec_path, dict_reader.data_elements()).get_doc_root().find(
        ['chapter[@label="C"]']
    )


def find_chapter(name: str):
    return None


@pytest.fixture
def parser(dict_info) -> Generator[EnumParser, None, None]:
    yield EnumParser(find_chapter, ConditionParser(dict_info))


def section(contents, label="C.42.3.5") -> ElementTree.Element | None:
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
    <book xmlns="http://docbook.org/ns/docbook" xmlns:xl="http://www.w3.org/1999/xlink">
    <chapter label="C"><section label="{label}" xml:id="sect_{label}">
    {contents}
    </section></chapter>
    </book>"""
    doc = ElementTree.fromstring(xml)
    return doc.find(f".//{{http://docbook.org/ns/docbook}}section[@label='{label}']")


class TestEmptyEnumParser:
    def test_empty_description(self, parser):
        assert parser.parse(section(""), VR.SH) == []

    def test_incorrect_tag(self, parser):
        content = """<variablelist>
        <div>Enumerated Values:</div>
        <varlistentry>
        <term>NO</term>
        </varlistentry>
        </variablelist>"""
        assert parser.parse(section(content), VR.SS) == []

    def test_empty_list(self, parser):
        content = """<variablelist>
        <title>Enumerated Values:</title>
        </variablelist>"""
        assert parser.parse(section(content), VR.LO) == []


class TestEnumParser:
    def test_single_enum(self, parser):
        content = """<variablelist>
        <title>Enumerated Values:</title>
        <varlistentry>
        <term>NO</term>
        </varlistentry>
        </variablelist>"""
        assert parser.parse(section(content), VR.SH) == [{"val": ["NO"]}]

    def test_single_enum_with_extra_tag(self, parser):
        content = """<variablelist>
        <title>Enumerated Values:</title>
        <varlistentry>
        <listitem>
        <para xml:id="para_f6578fe2-d628-412e-8314-af2c8961b633"/>
        </listitem>
        <term>NO</term>
        </varlistentry>
        </variablelist>"""
        assert parser.parse(section(content), VR.SH) == [{"val": ["NO"]}]

    def test_two_enums(self, parser):
        content = """<variablelist>
        <title>Enumerated Values:</title>
        <varlistentry>
        <term>YES</term>
        </varlistentry>
        <varlistentry>
        <term>NO</term>
        </varlistentry>
        </variablelist>"""
        assert parser.parse(section(content), VR.SH) == [{"val": ["YES", "NO"]}]

    def test_enums_for_tag(self, parser):
        content = """<variablelist spacing="compact">
            <title>Enumerated Values for Shading Style (0070,1701):</title>
            <varlistentry>
                <term>SINGLESIDED</term>
                <listitem>
                    <para xml:id="para_473d9354-6a53-44e8-ad28-f22416acfb56">Only "front-facing" voxels are shaded.</para>
                </listitem>
            </varlistentry>
            <varlistentry>
                <term>DOUBLESIDED</term>
                <listitem>
                    <para xml:id="para_b1cd12b0-4f01-4370-bb13-ab04d3f1b048">"Front-facing" and "back-facing" voxels are shaded.</para>
                </listitem>
            </varlistentry>
        </variablelist>"""
        assert parser.parse(section(content), VR.CS) == [
            {"tag": "(0070,1701)", "val": ["SINGLESIDED", "DOUBLESIDED"]}
        ]

    def test_int_enums(self, parser):
        content = """<variablelist>
        <title>Enumerated Values:</title>
        <varlistentry>
        <term>0000</term>
        </varlistentry>
        <varlistentry>
        <term>0001</term>
        </varlistentry>
        </variablelist>"""
        assert parser.parse(section(content), VR.US) == [{"val": [0, 1]}]

    def test_hex_enums(self, parser):
        content = """<variablelist>
        <title>Enumerated Values:</title>
        <varlistentry>
        <term>0010H</term>
        </varlistentry>
        <varlistentry>
        <term>0011H</term>
        </varlistentry>
        </variablelist>"""
        assert parser.parse(section(content), VR.US) == [{"val": [16, 17]}]

    def test_linked_enum(self, dict_info):
        content = """<para>Bla blah, see
        <xref linkend="sect_10.7.1.2" xrefstyle="select: label"/>.</para>"
        """
        linked = """
        <title>Pixel Spacing Calibration Type</title>
        <para xml:id="para_f24c1">Pixel Spacing Calibration Type.</para>
        <variablelist spacing="compact">
            <title>Enumerated Values:</title>
            <varlistentry>
                <term>GEOMETRY</term>
                <listitem>
                    <para xml:id="para_a79e2faf">Description...</para>
                </listitem>
            </varlistentry>
            <varlistentry>
                <term>FIDUCIAL</term>
                <listitem>
                    <para xml:id="para_10de0799">Another...</para>
                </listitem>
            </varlistentry>
        </variablelist>
        """
        parser = EnumParser(lambda s: section(linked, s), ConditionParser(dict_info))
        assert parser.parse(section(content), VR.SH) == [
            {"val": ["GEOMETRY", "FIDUCIAL"]}
        ]

    def test_linked_enum_with_tag(self, dict_info):
        content = (
            '<para xml:id="para_97e843f4-e558-44fd-8858-5b899ad5eeb7">'
            'See <xref linkend="sect_C.8.12.4.1.5" xrefstyle="select: label"/> '
            "for further explanation.</para>"
        )
        linked = """
        <title>Photometric Interpretation and Samples per Pixel</title>
        <variablelist spacing="compact">
            <title>Enumerated Values for Photometric Interpretation (0028,0004):</title>
            <varlistentry>
                <term>MONOCHROME2</term>
                <listitem>
                    <para xml:id="para_7a7f7d7f-3c23-4ec2-990e-a3fad60a5863"/>
                </listitem>
            </varlistentry>
            <varlistentry>
                <term>RGB</term>
                <listitem>
                    <para xml:id="para_2ba62380-d35e-429a-9f39-f2af10ca8dfb"/>
                </listitem>
            </varlistentry>
        </variablelist>
        <variablelist spacing="compact">
            <title>Enumerated Values for Samples per Pixel (0028,0002) when Photometric Interpretation (0028,0004) is MONOCHROME2:</title>
            <varlistentry>
                <term>1</term>
                <listitem>
                    <para xml:id="para_4eef8f1d-9f61-4bb9-8d57-b5e987cdd413"/>
                </listitem>
            </varlistentry>
        </variablelist>
        <variablelist spacing="compact">
            <title>Enumerated Values for Samples per Pixel (0028,0002) when Photometric Interpretation (0028,0004) is not MONOCHROME2:</title>
            <varlistentry>
                <term>3</term>
                <listitem>
                    <para xml:id="para_502ba4c0-30a4-4341-833f-f73c2cde930d"/>
                </listitem>
            </varlistentry>
        </variablelist>
        """
        parser = EnumParser(lambda s: section(linked, s), ConditionParser(dict_info))
        assert parser.parse(section(content), VR.SH) == [
            {"tag": "(0028,0004)", "val": ["MONOCHROME2", "RGB"]},
            {
                "tag": "(0028,0002)",
                "val": ["1"],
                "cond": Condition(
                    ConditionType.MandatoryOrUserDefined,
                    ConditionOperator.EqualsValue,
                    "(0028,0004)",
                    0,
                    ["MONOCHROME2"],
                ),
            },
            {
                "tag": "(0028,0002)",
                "val": ["3"],
                "cond": Condition(
                    ConditionType.MandatoryOrUserDefined,
                    ConditionOperator.NotEqualsValue,
                    "(0028,0004)",
                    0,
                    ["MONOCHROME2"],
                ),
            },
        ]

    def test_enum_value_for_value(self, parser):
        content = """
        <variablelist spacing="compact">
            <title>Enumerated Values for Value 1:</title>
            <varlistentry>
                <term>DERIVED</term>
                <listitem>
                    <para xml:id="para_34ae991b-705a-4ffc-992e-6f97e657d0d0"/>
                </listitem>
            </varlistentry>
        </variablelist>
        <variablelist spacing="compact">
            <title>Enumerated Values for Value 2:</title>
            <varlistentry>
                <term>PRIMARY</term>
                <listitem>
                    <para xml:id="para_c6dbc4cc-fdd6-499f-ab90-9dc7f4ee13a9"/>
                </listitem>
            </varlistentry>
        </variablelist>
        """
        assert parser.parse(section(content), VR.CS) == [
            {"index": 1, "val": ["DERIVED"]},
            {"index": 2, "val": ["PRIMARY"]},
        ]

    def test_value_for_enum_value(self, parser):
        content = """
        <variablelist spacing="compact">
            <title>Value 2 Enumerated Values:</title>
            <varlistentry>
                <term>IMAGE</term>
                <listitem>
                    <para xml:id="para_bb573f6c-2620-4591-9fc9-81303702994f"/>
                </listitem>
            </varlistentry>
            <varlistentry>
                <term>REPROJECTION</term>
                <listitem>
                    <para xml:id="para_39df48ba-44f2-4c5a-8110-228b8cfc9abb"/>
                </listitem>
            </varlistentry>
        </variablelist>
        """
        assert parser.parse(section(content), VR.CS) == [
            {"index": 2, "val": ["IMAGE", "REPROJECTION"]},
        ]

    def test_values_with_condition(self, parser):
        content = """
        <variablelist spacing="compact">
            <title>Enumerated Values if Segmentation Type (0062,0001) is BINARY or FRACTIONAL:</title>
            <varlistentry>
                <term>MONOCHROME2</term>
                <listitem>
                    <para xml:id="para_8e13fa16-ef94-4273-9bf1-4476d60c86f2"/>
                </listitem>
            </varlistentry>
        </variablelist>
        <variablelist spacing="compact" termlength="3in">
            <title>Enumerated Values if Segmentation Type (0062,0001) is LABELMAP:</title>
            <varlistentry>
                <term>MONOCHROME2</term>
                <listitem>
                    <para xml:id="para_c0295049-6342-4816-b56f-c0de51206c23"/>
                </listitem>
            </varlistentry>
            <varlistentry>
                <term>PALETTE COLOR</term>
                <listitem>
                    <para xml:id="para_7cc0cd10-131d-43cd-815c-f585fb0c09c8"/>
                </listitem>
            </varlistentry>
        </variablelist>
        """
        assert parser.parse(section(content), VR.CS) == [
            {
                "val": ["MONOCHROME2"],
                "cond": Condition(
                    ConditionType.MandatoryOrUserDefined,
                    ConditionOperator.EqualsValue,
                    "(0062,0001)",
                    0,
                    ["BINARY", "FRACTIONAL"],
                ),
            },
            {
                "val": ["MONOCHROME2", "PALETTE COLOR"],
                "cond": Condition(
                    ConditionType.MandatoryOrUserDefined,
                    ConditionOperator.EqualsValue,
                    "(0062,0001)",
                    0,
                    ["LABELMAP"],
                ),
            },
        ]
