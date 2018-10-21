import datetime
import hashlib
import json
import os
import re
import requests
import sys
from email.parser import FeedParser
from threading import Thread

ENCODING = 'utf8'
DECODE = False
TEXT_CONTENT = 'text/plain'
HTML_CONTENT = 'text/html'
RE_FROM = re.compile('<[^>]+>$')
DATE_FORMATS = ['%a, %d %b %Y %X %z', '%a, %d %b %Y %X %z (%Z)', '%d %b %Y %X %z', '%d %b %Y %X %z (%Z)']
DEFAULT_FOLDER = 'Inbox'
API_KEY = os.getenv('API_KEY')
API_ENDPOINT = os.getenv('API_ENDPOINT')


class MsgParser:
    def __init__(self, input_file, folder=DEFAULT_FOLDER):
        self.msg = None
        self.input_file = input_file
        self.folder = folder
        self.from_email = None
        self.from_name = None
        self.to_email = None
        self.subject = None
        self.date = None
        self.id = None
        self.id_hash = None

    def valid_header_line(self, line):
        return not line.startswith('From ') and not line.startswith('^From ')

    def parse(self):
        parser = FeedParser()
        line = self.input_file.readline()
        while line is not None and len(line) > 0:
            if self.valid_header_line(line):
                parser.feed(line)
            line = self.input_file.readline()
        self.msg = parser.close()
        self.from_email = self._get_from_email()
        self.from_name = self._get_from_name()
        self.to_email = self._get_to_email()
        self.subject = self._get_subject()
        self.date = self._get_date()
        self.id = self._get_id()
        self.id_hash = self._get_id_hash()

    def get_body(self):
        body = None
        if self.msg.is_multipart():
            for part in self.msg.walk():
                if part.is_multipart():
                    for subpart in part.walk():
                        if subpart.get_TEXT_CONTENT() == TEXT_CONTENT:
                            body = subpart.get_payload(decode=DECODE)
                elif part.get_TEXT_CONTENT() == TEXT_CONTENT:
                    body = part.get_payload(decode=DECODE)
        elif self.msg.get_TEXT_CONTENT() == TEXT_CONTENT:
            body = self.msg.get_payload(decode=DECODE)
        return body

    def get_parts(self):
        parts = []
        if self.msg.is_multipart():
            for part in self.msg.walk():
                parts.append(part)
        else:
            parts.append(self.msg)
        return parts

    def _get_from(self):
        return self.msg['from']

    def _get_from_email(self):
        from_email = self._get_from()
        m = RE_FROM.search(from_email)
        if m is not None:
            from_email = m.group()[1:-1]
        return from_email

    def _get_from_name(self):
        from_email = self._get_from()
        m = RE_FROM.search(from_email)
        if m is not None:
            from_email = from_email[:m.start()].replace('"', '').strip()
        return from_email

    def _get_to(self):
        return self.msg['to']

    def _get_to_email(self):
        to_email = self._get_to()
        m = RE_FROM.search(to_email)
        if m is not None:
            to_email = m.group()[1:-1]
        return to_email

    def _get_subject(self):
        return self.msg['subject']

    def _parse_date(self, date_in):
        for fmt in DATE_FORMATS:
            try:
                return datetime.datetime.strptime(date_in, fmt).isoformat(sep='T')
            except Exception:
                pass
        return None

    def _get_date(self):
        return self._parse_date(self.msg['date'])

    def _get_id(self):
        return self.msg['message-id'].strip()[1:-1]

    def _get_id_hash(self):
        return hashlib.sha512(self._get_id().encode(ENCODING)).hexdigest()


class PartUploader(Thread):
    def __init__(self, part, part_no, prefix):
        super().__init__()
        self.part = part
        self.no = part_no
        self.prefix = prefix

    def get_object_name(self):
        if self.part.get_content_type() == TEXT_CONTENT:
            return 'part _' + str(self.no) + '.txt'
        elif self.part.get_content_type() == HTML_CONTENT:
            return 'part_' + str(self.no) + '.html'
        else:
            file_name = self.part.get_filename()
            if file_name is not None:
                return file_name
            else:
                return 'part_' + str(self.no) + '.unknown'

    def run(self):
        endpoint = API_ENDPOINT + '/' + self.prefix + '/' + self.get_object_name()
        print(endpoint)
        data = {
            'object_name': self.get_object_name(),
            'payload': self.part.get_payload(decode=DECODE)
        }
        resp = requests.post(endpoint, data=json.dumps(data), headers={'x-api-key': API_KEY})
        if resp.status_code == 200:
            pass
        print(resp.status_code)
        print(resp.text)


def upload_email(mp):
    data = {
        'from_email': mp.from_email,
        'from_name': mp.from_name,
        'to_email': mp.to_email,
        'subject': mp.subject,
        'date': mp.date,
        'folder': mp.folder,
        'id': mp.id_hash
    }
    resp = requests.post(API_ENDPOINT, data=json.dumps(data), headers={'x-api-key': API_KEY})
    if resp.status_code == 200:
        part_no = 0
        uploaders = []
        for part in mp.get_parts():
            uploader = PartUploader(part, part_no, mp.folder + '/' + mp.id_hash)
            uploaders.append(uploader)
            uploader.start()
            part_no += 1
        for u in uploaders:
            u.join()
        return True
    return False


def main():
    try:
        mp = MsgParser(sys.stdin)
        mp.parse()
        upload_email(mp)
    except Exception:
        raise


if __name__ == '__main__':
    main()
