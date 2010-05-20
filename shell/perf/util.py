from datetime import datetime
import hashlib
import hmac
import re
import smtplib

from django.conf import settings
from django.template.loader import render_to_string

# Encoding detection for JSON rfc4627, section 3. The RFC doesn't mention
# the possibility of starting with a BOM, but in pratice that's likely
# if the input data is UTF-16.
def application_json_to_unicode(raw):
    bom = True
    if raw[0:2] == '\xfe\xff':
        encoding = 'UTF-16BE'
    elif raw[0:2] == '\xff\xfe':
        encoding = 'UTF-16LE'
    elif raw[0:3] == '\xef\xbb\xbf':
        encoding = 'UTF-8'
    elif raw[0:4] == '\x00\x00\xfe\xff':
        encoding = 'UTF-32BE'
    elif raw[0:4] == '\xff\xfe\x00\x00':
        encoding = 'UTF-32LE'
    else:
        bom = False
        null_patterns = {
            'NNNX': 'UTF-32BE',
            'NXNX': 'UTF-16BE',
            'XNNN': 'UTF-32LE',
            'XNXN': 'UTF-16LE'
        };

        nullPattern = re.sub(r'[^\x00]', 'X', raw[0:4])
        nullPattern = re.sub(r'\x00', 'N', nullPattern)

        if nullPattern in null_patterns:
            encoding = encodings[nullPattern]
        else:
            encoding = 'UTF-8'

    # json module can't handle initial bom, so strip if we found it
    decoded = raw.decode(encoding)
    if bom:
        return decoded[1:]
    else:
        return decoded

# This is a workaround to make the Python 2.4 hmac module work with the
# external hashlib module in python-2.4
class _sha1_adapter:
    new = hashlib.sha1
    digest_size = 20

def hmac_sha1(key, msg=None):
    return hmac.new(key, msg, digestmod=_sha1_adapter)

def parse_isodate(s):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f")

def _hex(byte):
    digits = '0123456789abcdef'
    return digits[byte >> 4] + digits[byte & 0xf]

def random_key():
    f = open('/dev/random')
    bytes = f.read(16)
    return "".join((_hex(ord(byte)) for byte in bytes))

def send_email(template_name, args, toaddr):
    fullargs = dict(args)
    fullargs['fromaddr'] = settings.MAIL_FROM
    fullargs['toaddr'] = toaddr
    msg = render_to_string(template_name, fullargs)
    
    m = re.match(r'([^:]+)(?::(\d+))?', settings.SMTP_SERVER)
    if m is None:
        raise ValueError("Bad setting for SMTP_SERVER, should be <host>[:<port>]")
    host = m.group(1)
    if m.group(2) is not None:
        port = int(m.group(2))
    else:
        port = 25

    server = smtplib.SMTP(host, port)
    server.sendmail(settings.MAIL_FROM, [toaddr], msg)
    server.quit()
