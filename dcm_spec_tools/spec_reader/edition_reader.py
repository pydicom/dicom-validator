import datetime
import json
import logging
import os

import re

try:
    from urllib import urlretrieve
except ImportError:
    from urllib.request import urlretrieve

try:
    import HTMLParser as html_parser
except ImportError:
    import html.parser as html_parser


class EditionParser(html_parser.HTMLParser):
    edition_re = re.compile(r'\d\d\d\d[a-h]')

    def __init__(self):
        html_parser.HTMLParser.__init__(self)
        self._in_anchor = False
        self.editions = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self._in_anchor = True

    def handle_endtag(self, tag):
        if tag == 'a':
            self._in_anchor = False

    def handle_data(self, data):
        if self._in_anchor and self.edition_re.match(data):
            self.editions.append(data)


class EditionReader(object):
    html_filename = 'editions.html'
    json_filename = 'editions.json'

    def __init__(self, url, path):
        self.url = url
        self.path = path
        self.logger = logging.getLogger()

    def update_edition(self):
        try:
            self.logger.info('Getting DICOM editions...')
            self.retrieve(os.path.join(self.path, self.html_filename))
            self.write_to_json()
        except BaseException as exception:
            self.logger.warning(u'Failed to get DICOM read_from_html: {}'.format(str(exception)))

    def retrieve(self, html_path):
        urlretrieve(self.url, html_path)

    def get_editions(self):
        editions_path = os.path.join(self.path, self.json_filename)
        update = True
        if os.path.exists(editions_path):
            today = datetime.datetime.today()
            modified_date = datetime.datetime.fromtimestamp(os.path.getmtime(editions_path))
            # no need to update the edition dir more than once a month
            update = (today - modified_date).days > 30
        if update:
            self.update_edition()
        if os.path.exists(editions_path):
            with open(editions_path) as json_file:
                return json.load(json_file)

    def read_from_html(self):
        html_path = os.path.join(self.path, self.html_filename)
        with open(html_path) as html_file:
            contents = html_file.read()
        parser = EditionParser()
        parser.feed(contents)
        parser.close()
        return parser.editions

    def write_to_json(self):
        editions = self.read_from_html()
        if editions:
            json_path = os.path.join(self.path, self.json_filename)
            with open(json_path, 'w') as json_file:
                json_file.write(json.dumps(editions))

    def get_edition(self, revision):
        """Get the edition matching the revision or None.
        The revision can be the edition name, the year of the edition, or 'current'.
        """
        editions = sorted(self.get_editions())
        if revision in editions:
            return revision
        if len(revision) == 4:
            for edition in reversed(editions):
                if edition.startswith(revision):
                    return edition
        if revision == 'current':
            return editions[-1]
