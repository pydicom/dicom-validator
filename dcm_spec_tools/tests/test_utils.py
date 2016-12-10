import os


def fixture_path():
    return os.path.join(os.path.dirname(__file__), 'fixtures')


def spec_fixture_path():
    return os.path.join(fixture_path(), 'docbook')


def json_fixture_path():
    return os.path.join(fixture_path(), 'json')
