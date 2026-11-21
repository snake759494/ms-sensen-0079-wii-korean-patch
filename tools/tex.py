"""brres 안 TEX0 텍스처 목록/디코드/인코드 (I4, I8, IA4, IA8, RGB565, RGB5A3, RGBA8, CMPR)."""
import struct
from PIL import Image

BLK = {0: (8, 8, 4), 1: (8, 4, 8), 2: (8, 4, 8), 3: (4, 4, 16), 4: (4, 4, 16), 5: (4, 4, 16), 6: (4, 4, 32), 14: (8, 8, 4)}


def find(d):
    """[(off, name, w, h, fmt, mips, dataoff)]"""
    out = []; p = 0
    while True:
        p = d.find(b'TEX0', p)
        if p < 0: break
        try:
            ln, ver, outer, doff, noff = struct.unpack('>IIiII', d[p + 4:p + 24])
            w, h = struct.unpack('>HH', d[p + 0x1c:p + 0x20])
            fmt, mips = struct.unpack('>II', d[p + 0x20:p + 0x28])
            if ver in (1, 3) and fmt in BLK and 0 < w <= 1024 and 0 < h <= 1024 and noff < 0x1000000:
                nl = struct.unpack('>I', d[p + noff - 4:p + noff])[0]
                name = d[p + noff:p + noff + nl].decode('ascii', 'replace')
                out.append((p, name, w, h, fmt, mips, p + doff))
        except Exception:
            pass
        p += 4
    return out


def size(w, h, fmt):
    bw, bh, bpp = BLK[fmt]
    return ((w + bw - 1) // bw) * ((h + bh - 1) // bh) * bw * bh * bpp // 8


def c565(v): return ((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31


def c5a3(v):
    if v & 0x8000: return ((v >> 10) & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, (v & 31) * 255 // 31, 255
    return ((v >> 8) & 15) * 17, ((v >> 4) & 15) * 17, (v & 15) * 17, ((v >> 12) & 7) * 255 // 7


def decode(d, off, w, h, fmt):
    bw, bh, bpp = BLK[fmt]
    im = Image.new('RGBA', (w, h)); px = im.load()
    p = off
    for by in range(0, h, bh):
        for bx in range(0, w, bw):
            if fmt == 6:
                blk = d[p:p + 64]; p += 64
                for i in range(16):
                    x, y = bx + i % 4, by + i // 4
                    if x < w and y < h:
                        a, r = blk[i * 2], blk[i * 2 + 1]; g, b = blk[32 + i * 2], blk[32 + i * 2 + 1]
                        px[x, y] = (r, g, b, a)
                continue
            if fmt == 14:
                for sb in range(4):
                    sx, sy = bx + (sb & 1) * 4, by + (sb >> 1) * 4
                    c0, c1, bits = struct.unpack('>HHI', d[p:p + 8]); p += 8
                    a = c565(c0) + (255,); b = c565(c1) + (255,)
                    if c0 > c1:
                        c2 = tuple((2 * a[i] + b[i]) // 3 for i in range(3)) + (255,)
                        c3 = tuple((a[i] + 2 * b[i]) // 3 for i in range(3)) + (255,)
                    else:
                        c2 = tuple((a[i] + b[i]) // 2 for i in range(3)) + (255,); c3 = (0, 0, 0, 0)
                    pal = (a, b, c2, c3)
                    for i in range(16):
                        x, y = sx + i % 4, sy + i // 4
                        if x < w and y < h: px[x, y] = pal[(bits >> (30 - 2 * i)) & 3]
                continue
            n = bw * bh * bpp // 8
            blk = d[p:p + n]; p += n
            for i in range(bw * bh):
                x, y = bx + i % bw, by + i // bw
                if fmt == 0: v = (blk[i // 2] >> (4 if i % 2 == 0 else 0)) & 15; c = (v * 17,) * 3 + (255,)
                elif fmt == 1: c = (blk[i],) * 3 + (255,)
                elif fmt == 2: v = blk[i]; c = ((v & 15) * 17,) * 3 + ((v >> 4) * 17,)
                elif fmt == 3: c = (blk[i * 2 + 1],) * 3 + (blk[i * 2],)
                elif fmt == 4: c = c565(struct.unpack('>H', blk[i * 2:i * 2 + 2])[0]) + (255,)
                elif fmt == 5: c = c5a3(struct.unpack('>H', blk[i * 2:i * 2 + 2])[0])
                if x < w and y < h: px[x, y] = c
    return im


def e5a3(r, g, b, a):
    if a >= 0xe0: return 0x8000 | (r >> 3) << 10 | (g >> 3) << 5 | (b >> 3)
    return (a >> 5) << 12 | (r >> 4) << 8 | (g >> 4) << 4 | (b >> 4)


def encode(im, fmt):
    w, h = im.size; im = im.convert('RGBA'); px = im.load()
    bw, bh, bpp = BLK[fmt]
    out = bytearray()
    def P(x, y): return px[x, y] if x < w and y < h else (0, 0, 0, 0)
    for by in range(0, h, bh):
        for bx in range(0, w, bw):
            if fmt == 6:
                ar = bytearray(); gb = bytearray()
                for i in range(16):
                    r, g, b, a = P(bx + i % 4, by + i // 4); ar += bytes([a, r]); gb += bytes([g, b])
                out += ar + gb; continue
            if fmt == 14:
                for sb in range(4):
                    sx, sy = bx + (sb & 1) * 4, by + (sb >> 1) * 4
                    out += cmpr_block([P(sx + i % 4, sy + i // 4) for i in range(16)])
                continue
            if fmt == 0:
                for i in range(0, 64, 2):
                    a = P(bx + i % 8, by + i // 8); b = P(bx + (i + 1) % 8, by + (i + 1) // 8)
                    out.append((lum(a) >> 4) << 4 | lum(b) >> 4)
                continue
            for i in range(bw * bh):
                c = P(bx + i % bw, by + i // bw); r, g, b, a = c
                if fmt == 1: out.append(lum(c))
                elif fmt == 2: out.append((a >> 4) << 4 | lum(c) >> 4)
                elif fmt == 3: out += bytes([a, lum(c)])
                elif fmt == 4: out += struct.pack('>H', (r >> 3) << 11 | (g >> 2) << 5 | (b >> 3))
                elif fmt == 5: out += struct.pack('>H', e5a3(r, g, b, a))
    return bytes(out)


def lum(c): return max(c[0], c[1], c[2]) if c[0] == c[1] == c[2] else (c[0] * 299 + c[1] * 587 + c[2] * 114) // 1000


def cmpr_block(cs):
    op = [c for c in cs if c[3] >= 128]
    trans = len(op) < 16
    def to565(c): return (c[0] >> 3) << 11 | (c[1] >> 2) << 5 | (c[2] >> 3)
    if not op:
        return struct.pack('>HHI', 0, 0xffff, 0xffffffff)
    # 가장 먼 두 색
    best = (-1, op[0], op[0])
    for i in range(len(op)):
        for j in range(i, len(op)):
            dd = sum((op[i][k] - op[j][k]) ** 2 for k in range(3))
            if dd > best[0]: best = (dd, op[i], op[j])
    a, b = to565(best[1]), to565(best[2])
    if trans:
        if a > b: a, b = b, a
        if a == b and a < 0xffff: b = a + 1 if a != 0xffff else a
    else:
        if a < b: a, b = b, a
        if a == b:
            if a > 0: b = a - 1
            else: a = 1
    ca, cb = c565(a), c565(b)
    if a > b: pal = [ca, cb, tuple((2 * ca[i] + cb[i]) // 3 for i in range(3)), tuple((ca[i] + 2 * cb[i]) // 3 for i in range(3))]
    else: pal = [ca, cb, tuple((ca[i] + cb[i]) // 2 for i in range(3)), None]
    bits = 0
    for i, c in enumerate(cs):
        if c[3] < 128 and a <= b: k = 3
        else:
            k = min(range(4 if a > b else 3), key=lambda k: sum((pal[k][j] - c[j]) ** 2 for j in range(3)))
        bits |= k << (30 - 2 * i)
    return struct.pack('>HHI', a, b, bits)
