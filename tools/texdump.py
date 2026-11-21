import sys, os, glob, hashlib, json
sys.path.insert(0, os.path.dirname(__file__)); import u8, tex
from PIL import Image
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.makedirs('tex/all', exist_ok=True)
seen = {}


def walk(p, d):
    if d[:4] == b'U\xaa8-':
        for n, dd in u8.parse(d):
            if dd is not None: walk(p + '/' + n, dd)
    elif d[:4] == b'bres' or d[:4] == b'\x00 \xaf0':
        for off, name, w, h, fmt, mips, doff in tex.find(d):
            raw = d[doff:doff + tex.size(w, h, fmt)]
            k = hashlib.md5(raw).hexdigest()[:10]
            if k in seen: seen[k]['refs'].append(p); continue
            seen[k] = dict(name=name, w=w, h=h, fmt=fmt, refs=[p])
            im = tex.decode(d, doff, w, h, fmt)
            bg = Image.new('RGBA', im.size, (0, 0, 80, 255)); bg.alpha_composite(im)
            bg.convert('RGB').save('tex/all/%s_%s.png' % (k, name))


for f in sorted(glob.glob('ext/DATA/files/_2d/**/*', recursive=True)):
    f = f.replace(os.sep, '/')
    if os.path.isfile(f): walk(f, open(f, 'rb').read())
json.dump(seen, open('tex/index.json', 'w'), indent=0)
print(len(seen))
