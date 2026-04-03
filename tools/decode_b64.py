import sys, re, json, base64, os

if len(sys.argv) < 3:
    print('Usage: decode_b64.py <html_file> <out_js>')
    sys.exit(2)
html = sys.argv[1]
out = sys.argv[2]
if not os.path.exists(html):
    print('HTML file not found:', html)
    sys.exit(3)
s = open(html, 'r', encoding='utf-8', errors='replace').read()
# find const b64 = <json-string>;
m = re.search(r"const\s+b64\s*=\s*(?P<val>\"(?:\\.|[^\\\"])*\"|'(?:\\.|[^\\'])*')", s, re.S)
if not m:
    print('base64 literal not found in', html)
    sys.exit(4)
val = m.group('val')
# val is a quoted JS string; convert to Python string via json loads if double-quoted
try:
    decoded_literal = json.loads(val)
except Exception:
    # try to unquote single-quoted
    if val[0] == "'" and val[-1] == "'":
        inner = val[1:-1]
        # replace common JS escapes
        inner = inner.encode('utf-8').decode('unicode_escape')
        decoded_literal = inner
    else:
        decoded_literal = val.strip('"')
# Now base64-decode
try:
    data = base64.b64decode(decoded_literal)
except Exception as e:
    print('Failed to base64-decode:', e)
    sys.exit(5)
open(out, 'wb').write(data)
print('Wrote decoded JS to', out)
# print first 200 bytes hex
head = data[:200]
print('First 200 bytes (hex):', ' '.join(f'{b:02x}' for b in head))
# compute sha256
import hashlib
h = hashlib.sha256(data).hexdigest()
print('Decoded SHA256:', h)
# also print local static/app.js sha256 if exists
local = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'app.js')
if os.path.exists(local):
    with open(local, 'rb') as f:
        lh = hashlib.sha256(f.read()).hexdigest()
    print('Local static/app.js SHA256:', lh)
else:
    print('Local static/app.js not found at', local)
