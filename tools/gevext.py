import sys, glob, json, os, re
sys.path.insert(0, os.path.dirname(__file__)); import gev, u8
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JP = re.compile('[　-鿿＀-￯]')
uniq = {}


def visit(p, d):
    if d[:4] == b'$EVF':
        for s in gev.parse(d)['strs']:
            try: t = s.decode('cp932')
            except UnicodeDecodeError: continue
            if JP.search(t): uniq.setdefault(t, p)
    elif d[:4] == b'U\xaa8-':
        for n, dd in u8.parse(d):
            if dd is not None: visit(p + '/' + n, dd)


for f in sorted(glob.glob('ext/DATA/files/**/*', recursive=True)):
    f = f.replace(os.sep, '/')
    if os.path.isfile(f) and '/_test/' not in f and '/test/' not in f:
        visit(f, open(f, 'rb').read())
items = [{'id': i, 'src': p, 'jp': t} for i, (t, p) in enumerate(uniq.items())]
json.dump(items, open('text/gev.json', 'w', encoding='utf8'), ensure_ascii=False, indent=0)
with open('text/gevdump.txt', 'w', encoding='utf8') as w:
    for it in items:
        w.write('%d|%s|%s\n' % (it['id'], it['src'].split('/')[-1], it['jp'].replace('\n', '\\n')))
print(len(items), sum(len(x['jp']) for x in items))
