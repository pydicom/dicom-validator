import os

CURRENT_REVISION = '2021d'


def fixture_path():
    return os.path.join(os.path.dirname(__file__), 'fixtures')


def spec_fixture_path():
    return os.path.join(fixture_path(), CURRENT_REVISION, 'docbook')


def json_fixture_path():
    return os.path.join(fixture_path(), CURRENT_REVISION, 'json')


def dicom_fixture_path():
    return os.path.join(fixture_path(), 'dicom')
