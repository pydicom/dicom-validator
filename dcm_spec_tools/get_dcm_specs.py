import argparse
import os

try:
    from urllib import urlretrieve
except ImportError:
    import urllib.request.urlretrieve as urlretrieve


def get_chapter(revision, chapter, destination):
    if not validate_chapter(chapter):
        print(u'Invalid chapter number: ' + chapter)
    else:
        chapter = int(chapter)
        base_url = 'http://dicom.nema.org/medical/dicom'
        url = base_url + '/{0}/source/docbook/part{1:02}/part{1:02}.xml'.format(revision, chapter)
        try:
            urlretrieve(url, os.path.join(destination, 'part{:02}.xml'.format(chapter)))
        except BaseException as exception:
            print(u'Failed to download {}: {}'.format(url, str(exception)))


def validate_chapter(chapter):
    try:
        chapter = int(chapter)
    except ValueError:
        return False
    if chapter < 0 or chapter > 20:
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Get DICOM standard docbook XML files')
    parser.add_argument('--destination', '-d',
                        help='Filepath to write to',
                        default='DICOM')
    parser.add_argument('--revision', '-r',
                        help='Standard revision (e.g. 2014a, 2016c',
                        default='current')
    parser.add_argument('--chapters', '-c',
                        help='Comma separated list of chapters (e.g. 4 stands for PS3.4)',
                        default='3,4,6')
    args = parser.parse_args()

    chapters = args.chapters.split(',')
    if not os.path.exists(args.destination):
        os.makedirs(args.destination)
    for chapter in chapters:
        get_chapter(revision=args.revision, chapter=chapter, destination=args.destination)
    return 0


if __name__ == '__main__':
    exit(main())
