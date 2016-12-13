import argparse
import json
import os

from spec_reader.edition_reader import EditionReader

try:
    from urllib import urlretrieve
except ImportError:
    from urllib.request import urlretrieve

from dcm_spec_tools.spec_reader.part3_reader import Part3Reader
from dcm_spec_tools.spec_reader.part4_reader import Part4Reader
from dcm_spec_tools.spec_reader.part6_reader import Part6Reader


def get_chapter(revision, chapter, destination):
    file_path = os.path.join(destination, 'part{:02}.xml'.format(chapter))
    if os.path.exists(file_path):
        if revision:
            print('Chapter {} already present, skipping download'.format(chapter))
        return True
    elif not revision:
        print('Chapter {} not present at {}.'.format(chapter, file_path))
        return False
    url = '{0}{1}/source/docbook/part{2:02}/part{2:02}.xml'.format(EditionReader.base_url, revision, chapter)
    try:
        print('Downloading chapter {}...'.format(chapter))
        urlretrieve(url, file_path)
        return True
    except BaseException as exception:
        print(u'Failed to download {}: {}'.format(url, str(exception)))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                print('Failed to remove incomplete file {}.'.format(file_path))
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Get DICOM standard docbook XML files and converts parts to JSON')
    parser.add_argument('--destination', '-d',
                        help='Base file path to write_to_json to',
                        default=os.path.join(os.path.expanduser("~"), 'dcm-spec-tools'))
    parser.add_argument('--revision', '-r',
                        help='Standard revision (e.g. "2014c"), year of revision, or "current"',
                        default='current')
    args = parser.parse_args()

    if not os.path.exists(args.destination):
        os.makedirs(args.destination)

    revision, destination = EditionReader.get_revision(args.revision, args.destination)
    if destination is None:
        print('DICOM revision {} not found - exiting.'.format(args.revision))
        return 1

    docbook_path = os.path.join(destination, 'docbook')
    if not os.path.exists(docbook_path):
        os.makedirs(docbook_path)
    json_path = os.path.join(destination, 'json')
    if not os.path.exists(json_path):
        os.makedirs(json_path)

    # download the docbook files
    for chapter in [3, 4, 6]:
        if not get_chapter(revision=revision, chapter=chapter, destination=docbook_path):
            return 1

    # create the json files
    print('Creating JSON excerpts from docbook files...')
    part6reader = Part6Reader(docbook_path)
    dict_info = part6reader.data_elements()
    part3reader = Part3Reader(docbook_path, dict_info)
    part4reader = Part4Reader(docbook_path)

    iod_info = part3reader.iod_descriptions()
    chapter_info = part4reader.iod_chapters()
    definition = {}
    for chapter in iod_info:
        if chapter in chapter_info:
            for uid in chapter_info[chapter]:
                definition[uid] = iod_info[chapter]

    with open(os.path.join(json_path, 'iod_info.json'), 'w') as info_file:
        info_file.write(json.dumps(definition, sort_keys=True, indent=2))
    with open(os.path.join(json_path, 'module_info.json'), 'w') as info_file:
        info_file.write(json.dumps(part3reader.module_descriptions(), sort_keys=True, indent=2))
    with open(os.path.join(json_path, 'dict_info.json'), 'w') as info_file:
        info_file.write(json.dumps(dict_info, sort_keys=True, indent=2))
    print('Done!')

    return 0


if __name__ == '__main__':
    exit(main())
