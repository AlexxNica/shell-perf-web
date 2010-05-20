import base64
import re
import sys
import urllib
import util

class BadSignature(Exception):
    pass

def _dequote(str):
    m = re.match(r'^\"((?:\\.|[^\"\\])+)\"$', str)
    if m is not None:
        return re.sub(r'\\(.)', r'\1', m.group(1))
    else:
        return str

# This defines a method of signing an HTTP request similar to an OAuth
# signed request, except that instead of treating the body of a POST
# as a form with additional parameters, we just treat it as an opaque
# blob.
def check_signature(request, secret_key):
    if isinstance(secret_key, unicode):
        secret_key = secret_key.encode("UTF-8")

    if not 'HTTP_X_SHELL_SIGNATURE' in request.META:
        raise BadSignature("X-Shell-Signature header missing")

    sent_signature_header = request.META['HTTP_X_SHELL_SIGNATURE']
    m = re.match(r'^\s*([^\s,]+)\s*,\s*(\S+)\s*$', sent_signature_header)
    if not m:
        raise BadSignature("Can't parse X-Shell-Signature header")

    signature_method = _dequote(m.group(1))
    sent_signature = _dequote(m.group(2))

    if signature_method != "HMAC-SHA1":
        raise BadSignature("Bad signature method '%s'" % signature_method)

    signature_data = request.method + "&"
    if request.is_secure():
        signature_data += "https://"
    else:
        signature_data += "http://"

    signature_data += request.get_host()
    signature_data += request.path

    params = []
    for key, values in request.GET.iterlists():
        for value in values:
            params.append(urllib.quote(key, "~") + "=" + urllib.quote(value, "~"))

    if len(params) > 0:
        signature_data += "&" + "&".join(sorted(params))

    signature_data += "&&"

    h = util.hmac_sha1(secret_key.encode("UTF-8"))
    h.update(signature_data)
    h.update(request.raw_post_data)
    expected_signature = urllib.quote(base64.b64encode(h.digest()), "~")

    if sent_signature != expected_signature:
        raise BadSignature("Bad signature")
