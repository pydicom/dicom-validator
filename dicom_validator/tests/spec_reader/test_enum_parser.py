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
            {"val": ["SINGLESIDED", "DOUBLESIDED"]}
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

    def test_value_for_value(self, parser):
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
