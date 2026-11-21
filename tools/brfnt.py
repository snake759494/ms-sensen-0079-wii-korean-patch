"""NW4R RFNT(brfnt) 파서/빌더 (I4 시트 전용)"""
import struct
from PIL import Image


def _blocks(d):
    nb = struct.unpack_from('>H', d, 0xE)[0]
    o = 0x10; out = []
    for _ in range(nb):
        mg = d[o:o + 4]; sz = struct.unpack_from('>I', d, o + 4)[0]
        out.append((mg, o, sz)); o += sz
    return out


def load(d):
    f = {}
    bl = _blocks(d)
    fi = [b for b in bl if b[0] == b'FINF'][0][1]
    (f['type'], f['lf'], f['alt'], dl, dg, dc, f['enc'], pg, pw, pm,
     f['h'], f['w'], f['asc'], _) = struct.unpack_from('>BbHbBbBIIIBBBB', d, fi + 8)
    f['defw'] = (dl, dg, dc)
    t = pg - 8
    (cw, ch, base, mw, ssz, ns, fmt, cols, rows, sw, sh, so) = struct.unpack_from('>BBBBIHHHHHHI', d, t + 8)
    f.update(cw=cw, ch=ch, base=base, mw=mw, fmt=fmt, cols=cols, rows=rows, sw=sw, sh=sh)
    assert fmt == 0
    f['sheets'] = [d[so + i * ssz: so + (i + 1) * ssz] for i in range(ns)]
    # widths
    widths = {}
    p = pw
    while p:
        b0, b1, nxt = struct.unpack_from('>HHI', d, p)
        for i in range(b0, b1 + 1):
            widths[i] = struct.unpack_from('>bBb', d, p + 8 + (i - b0) * 3)
        p = nxt
    f['widths'] = widths
    cmap = {}
    p = pm
    while p:
        c0, c1, meth, _, nxt = struct.unpack_from('>HHHHI', d, p)
        q = p + 12
        if meth == 0:
            off = struct.unpack_from('>H', d, q)[0]
            for c in range(c0, c1 + 1): cmap[c] = off + c - c0
        elif meth == 1:
            for c in range(c0, c1 + 1):
                g = struct.unpack_from('>H', d, q + (c - c0) * 2)[0]
                if g != 0xFFFF: cmap[c] = g
        else:
            n = struct.unpack_from('>H', d, q)[0]
            for k in range(n):
                c, g = struct.unpack_from('>HH', d, q + 2 + k * 4)
                cmap[c] = g
        p = nxt
    f['cmap'] = cmap
    f['ver'] = d[6:8]
    return f


def sheet_img(f, k):
    sw, sh = f['sw'], f['sh']; raw = f['sheets'][k]
    im = Image.new('L', (sw, sh)); px = im.load(); i = 0
    for by in range(0, sh, 8):
        for bx in range(0, sw, 8):
            for y in range(8):
                for x in range(0, 8, 2):
                    b = raw[i]; i += 1
                    px[bx + x, by + y] = (b >> 4) * 17; px[bx + x + 1, by + y] = (b & 15) * 17
    return im


def sheet_bytes(im):
    sw, sh = im.size; px = im.load(); out = bytearray()
    for by in range(0, sh, 8):
        for bx in range(0, sw, 8):
            for y in range(8):
                for x in range(0, 8, 2):
                    out.append((min(15, (px[bx + x, by + y] + 8) // 17)) << 4 | min(15, (px[bx + x + 1, by + y] + 8) // 17))
    return bytes(out)


def glyph_img(f, g):
    per = f['cols'] * f['rows']
    s, r = divmod(g, per); row, col = divmod(r, f['cols'])
    im = sheet_img(f, s)
    x = col * (f['cw'] + 1); y = row * (f['ch'] + 1)
    return im.crop((x, y, x + f['cw'], y + f['ch']))


def add_glyphs(f, glyphs):
    """glyphs: list of (code, L-image cw x ch, (left,glyphw,charw)). 기존 코드면 덮어씀."""
    per = f['cols'] * f['rows']
    nglyph = len(f['sheets']) * per
    used = max(f['widths']) + 1
    new = []
    for code, im, w in glyphs:
        if code in f['cmap']:
            g = f['cmap'][code]
        else:
            g = used; used += 1; f['cmap'][code] = g
        f['widths'][g] = w
        new.append((g, im))
    # 시트 확장
    while len(f['sheets']) * per < used:
        f['sheets'].append(bytes(len(f['sheets'][0])))
    cache = {}
    for g, im in new:
        s, r = divmod(g, per); row, col = divmod(r, f['cols'])
        if s not in cache: cache[s] = sheet_img(f, s)
        cache[s].paste(Image.new('L', (f['cw'], f['ch']), 0), (col * (f['cw'] + 1), row * (f['ch'] + 1)))
        cache[s].paste(im, (col * (f['cw'] + 1), row * (f['ch'] + 1)))
    for s, im in cache.items():
        f['sheets'][s] = sheet_bytes(im)


def build(f):
    def al(b, a=4):
        return b + b'\0' * ((-len(b)) % a)
    ns = len(f['sheets']); ssz = len(f['sheets'][0])
    # 오프셋 계산
    finf_off = 0x10
    tglp_off = finf_off + 0x20
    sheet_off = (tglp_off + 0x30 + 31) & ~31
    tglp_end = sheet_off + ns * ssz
    tglp_size = tglp_end - tglp_off
    cwdh_off = tglp_end
    n = max(f['widths']) + 1
    wd = b''.join(struct.pack('>bBb', *f['widths'].get(i, f['defw'])) for i in range(n))
    cwdh = al(b'CWDH' + struct.pack('>IHHI', 0, 0, n - 1, 0) + wd)
    cwdh = cwdh[:4] + struct.pack('>I', len(cwdh)) + cwdh[8:]
    cmap_off = cwdh_off + len(cwdh)
    codes = sorted(f['cmap'])
    body = struct.pack('>H', len(codes)) + b''.join(struct.pack('>HH', c, f['cmap'][c]) for c in codes)
    cmap = al(b'CMAP' + struct.pack('>IHHHHI', 0, codes[0], codes[-1], 2, 0, 0) + body)
    cmap = cmap[:4] + struct.pack('>I', len(cmap)) + cmap[8:]
    total = cmap_off + len(cmap)
    hdr = b'RFNT' + b'\xfe\xff' + f['ver'] + struct.pack('>IHH', total, 0x10, 4)
    dl, dg, dc = f['defw']
    finf = b'FINF' + struct.pack('>I', 0x20) + struct.pack('>BbHbBbBIIIBBBB', f['type'], f['lf'], f['alt'], dl, dg, dc, f['enc'],
                                                         tglp_off + 8, cwdh_off + 8, cmap_off + 8, f['h'], f['w'], f['asc'], 0)
    tglp = b'TGLP' + struct.pack('>I', tglp_size) + struct.pack('>BBBBIHHHHHHI', f['cw'], f['ch'], f['base'], f['mw'], ssz, ns, 0,
                                                                f['cols'], f['rows'], f['sw'], f['sh'], sheet_off)
    out = hdr + finf + tglp
    out += b'\0' * (sheet_off - len(out))
    out += b''.join(f['sheets']) + cwdh + cmap
    assert len(out) == total
    return out
