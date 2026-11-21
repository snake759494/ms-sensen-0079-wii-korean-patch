import sys, re, json, collections, os
sys.path.insert(0, os.path.dirname(__file__))
import walk, xbf, u8, luastr
jp = re.compile('[぀-ヿ一-鿿＀-￯]')
order = collections.OrderedDict()


def add(t, src):
    if jp.search(t) and t not in order: order[t] = src


def cb(p, b):
    x = xbf.parse(b)
    for v in x['vals']: add(v, p.split('files', 1)[1])


def lw(b, p):
    if b[:4] != b'U\xaa8-': return
    for n, d in u8.parse(b):
        if not d: continue
        if n.endswith('.lua'):
            for s, e, v in luastr.strings(d):
                try: add(v.decode('utf8'), p.split('files', 1)[1] + '|' + n)
                except UnicodeDecodeError: pass
        lw(d, p + '|' + n)


fs = [f.replace(os.sep, '/') for f in walk.files()]
fs = [f for f in fs if '/test/' not in f]
for f in fs: walk.walk(open(f, 'rb').read(), f, cb)
for f in fs:
    if f.endswith('.arc'): lw(open(f, 'rb').read(), f)
print(len(order), sum(map(len, order)))
items = [{'id': i, 'src': s, 'jp': t, 'ko': ''} for i, (t, s) in enumerate(order.items())]
json.dump(items, open('text/all.json', 'w', encoding='utf8'), ensure_ascii=False, indent=0)
srcs = collections.Counter(re.sub(r'\d\d', '##', i['src'].split('|')[0]) for i in items)
for s, c in srcs.most_common(80): print(c, s)
