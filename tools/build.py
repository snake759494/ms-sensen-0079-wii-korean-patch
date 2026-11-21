"""번역·폰트를 주입해 patch/ 와 wfs/ 를 만든다.
python tools/build.py          -> patch/ 생성 + wfs/ 반영
"""
import sys, os, json, glob, shutil, hashlib, re
sys.path.insert(0, os.path.dirname(__file__))
import u8, xbf, luastr, mkfont, gev, kgev, texpatch

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(W)
EXT = 'ext/DATA/files'
PATCH = 'patch'
WFS = 'wfs'

items = json.load(open('text/all.json', encoding='utf8'))
tr = {}
for fn in sorted(glob.glob('text/tr/*.json')):
    for k, v in json.load(open(fn, encoding='utf8')).items():
        tr[int(k)] = v
TR = {}
for it in items:
    ko = tr.get(it['id'])
    if ko: TR[it['jp']] = ko
print('번역', len(TR), '/', len(items))
allko = ''.join(TR.values())

GI, GT = kgev.load()
GMAP = kgev.mapping(GI, GT)
TRG = kgev.table(GI, GT, GMAP)
print('gev 번역', len(TRG))

fontcache = {}


def font(d):
    h = hashlib.md5(d).hexdigest()
    if h not in fontcache:
        fontcache[h] = mkfont.patch(d, allko)
    return fontcache[h]


def lua_patch(d):
    out = bytearray(); last = 0; ch = False
    for s, e, v in luastr.strings(d):
        try: t = v.decode('utf8')
        except UnicodeDecodeError: continue
        if t in TR:
            out += d[last:s] + TR[t].encode('utf8'); last = e; ch = True
    if not ch: return d
    out += d[last:]
    return bytes(out)


def proc(name, d):
    """파일 하나 처리 -> 새 bytes"""
    if d[:4] == b'XBF\0':
        x = xbf.parse(d)
        if x['enc'] != 'utf8': return d
        nv = [TR.get(v, v) for v in x['vals']]
        if nv == x['vals']: return d
        x['vals'] = nv
        return xbf.build(x)
    if d[:4] == b'$EVF':
        g = gev.parse(d); ch = False
        for i, s in enumerate(g['strs']):
            try: t = s.decode('cp932')
            except UnicodeDecodeError: continue
            if t in TRG: g['strs'][i] = TRG[t]; ch = True
        return gev.build(g) if ch else d
    if d[:4] == b'U\xaa8-':
        ents = u8.parse(d); ch = False; ne = []
        for p, dd in ents:
            if dd is not None:
                n2 = proc(name + '/' + p, dd)
                if n2 is not dd and n2 != dd: ch = True
                dd = n2
            ne.append((p, dd))
        return u8.build(ne) if ch else d
    if d[:4] == b'bres':
        return texpatch.patch_brres(name, d)
    if name.endswith('.lua'):
        return lua_patch(d)
    if d[:4] == b'RFNT' and os.path.basename(name).upper() in ('NORMAL_FONT.BRFNT', 'IN_GAME_FONT.BRFNT'):
        return font(d)
    return d


def main():
    if os.path.isdir(PATCH): shutil.rmtree(PATCH)
    files = []
    for f in glob.glob(EXT + '/**/*', recursive=True):
        f = f.replace(os.sep, '/')
        if os.path.isdir(f) or '/test/' in f: continue
        if f.endswith(('.arc', '.xbf', '.brfnt', '.lua', '.gev')): files.append(f)
    n = 0
    for f in sorted(files):
        d = open(f, 'rb').read()
        nd = proc(f, d)
        if nd != d:
            rel = f[len(EXT) + 1:]
            os.makedirs(os.path.dirname(PATCH + '/' + rel), exist_ok=True)
            open(PATCH + '/' + rel, 'wb').write(nd); n += 1
    print('변경 파일', n)
    # wfs 반영
    if not os.path.isdir(WFS):
        os.system('cp -al ext/DATA wfs')
    lst = WFS + '/.patched'
    if os.path.exists(lst):
        for rel in open(lst, encoding='utf8').read().split('\n'):
            if rel and not os.path.exists(PATCH + '/' + rel):
                os.remove(WFS + '/files/' + rel); os.link(EXT + '/' + rel, WFS + '/files/' + rel)
    rels = []
    for f in glob.glob(PATCH + '/**/*', recursive=True):
        if os.path.isfile(f):
            rel = f.replace(os.sep, '/')[len(PATCH) + 1:]
            rels.append(rel)
            dst = WFS + '/files/' + rel
            if os.path.exists(dst): os.remove(dst)
            shutil.copyfile(f, dst)
    open(lst, 'w', encoding='utf8').write('\n'.join(rels))
    dol = kgev.patch_dol(open('ext/DATA/sys/main.dol', 'rb').read(), GMAP)
    os.makedirs('patch_sys', exist_ok=True)
    open('patch_sys/main.dol', 'wb').write(dol)
    if os.path.exists(WFS + '/sys/main.dol'): os.remove(WFS + '/sys/main.dol')
    open(WFS + '/sys/main.dol', 'wb').write(dol)


if __name__ == '__main__':
    main()
