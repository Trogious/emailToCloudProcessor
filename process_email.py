import datetime
import hashlib
import json
import os
import re
import requests
import sys
from email.parser import FeedParser

ENCODING = 'utf8'
DECODE = False
TEXT_CONTENT = 'text/plain'
RE_FROM = re.compile('<[^>]+>$')
DATE_FORMATS = ['%a, %d %b %Y %X %z', '%a, %d %b %Y %X %z (%Z)', '%d %b %Y %X %z', '%d %b %Y %X %z (%Z)']
API_KEY = os.getenv('API_KEY')
API_ENDPOINT = os.getenv('API_ENDPOINT')


class MsgParser:
    def __init__(self, input_file):
        self.msg = None
        self.input_file = input_file

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

    def get_from(self):
        return self.msg['from']

    def get_from_email(self):
        from_email = self.get_from()
        m = RE_FROM.search(from_email)
        if m is not None:
            from_email = m.group()[1:-1]
        return from_email

    def get_from_name(self):
        from_email = self.get_from()
        m = RE_FROM.search(from_email)
        if m is not None:
            from_email = from_email[:m.start()].replace('"', '').strip()
        return from_email

    def get_to(self):
        return self.msg['to']

    def get_to_email(self):
        to_email = self.get_to()
        m = RE_FROM.search(to_email)
        if m is not None:
            to_email = m.group()[1:-1]
        return to_email

    def get_subject(self):
        return self.msg['subject']

    def parse_date(self, date_in):
        for fmt in DATE_FORMATS:
            try:
                return datetime.datetime.strptime(date_in, fmt).isoformat(sep='T')
            except Exception:
                pass
        return None

    def get_date(self):
        return self.parse_date(self.msg['date'])

    def get_id(self):
        return self.msg['message-id'].strip()[1:-1]

    def get_id_hash(self):
        return hashlib.sha512(self.get_id().encode(ENCODING)).hexdigest()


def upload_email(mp):
    data = {
        'from_email': mp.get_from_email(),
        'from_name': mp.get_from_name(),
        'to_email': mp.get_to_email(),
        'subject': mp.get_subject(),
        'date': mp.get_date(),
        'id': mp.get_id_hash(),
        'body': mp.get_body()
    }
    resp = requests.post(API_ENDPOINT, data=json.dumps(data), headers={'x-api-key': API_KEY})
    if resp.status_code == 200:
        for p in mp.get_parts():
            print(p.get_content_type())
            print(p.get_filename())
    return resp.status_code == 200


def main():
    try:
        mp = MsgParser(sys.stdin)
        mp.parse()
        # upload_email(mp)
    except Exception:
        pass


if __name__ == '__main__':
    main()
