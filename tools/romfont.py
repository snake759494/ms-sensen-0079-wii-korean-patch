"""Wii/GC ROM 폰트(SJIS) 분석/글리프 인덱스 계산."""
import struct


def yay0(src):
    assert src[:4] == b'Yay0'
    size, lo, co = struct.unpack('>III', src[4:16])
    out = bytearray(); mp = 16
    mask = 0; bits = 0
    while len(out) < size:
        if bits == 0:
            mask = struct.unpack('>I', src[mp:mp + 4])[0]; mp += 4; bits = 32
        if mask & 0x80000000:
            out.append(src[co]); co += 1
        else:
            v = struct.unpack('>H', src[lo:lo + 2])[0]; lo += 2
            dist = (v & 0xfff) + 1; n = v >> 12
            if n == 0: n = src[co] + 18; co += 1
            else: n += 2
            for _ in range(n): out.append(out[-dist])
        mask = (mask << 1) & 0xffffffff; bits -= 1
    return bytes(out)


HDR = ['fontType', 'firstChar', 'lastChar', 'invalChar', 'ascent', 'descent', 'width', 'leading',
       'cellWidth', 'cellHeight']


def header(f):
    h = dict(zip(HDR, struct.unpack('>10H', f[:20])))
    h['sheetSize'], = struct.unpack('>I', f[0x14:0x18])
    (h['sheetFormat'], h['sheetColumn'], h['sheetRow'], h['sheetWidth'], h['sheetHeight'],
     h['widthTable']) = struct.unpack('>6H', f[0x18:0x24])
    h['sheetImage'], h['sheetFullSize'] = struct.unpack('>II', f[0x24:0x2c])
    h['c'] = f[0x2c:0x30]
    return h


def trail_ok(t): return 0x40 <= t <= 0xfc and t != 0x7f


def kanji_code(sj):
    """SJIS 1수준 한자 -> 폰트 코드 (0x889F..0x9872)."""
    assert 0x889e < sj <= 0x9872
    i = ((sj >> 8) - 0x88) * 188
    j = sj & 0xff
    assert trail_ok(j)
    j -= 0x40
    if j >= 0x40: j -= 1
    return i + j + 0x2be


def texel_off(h, code, x, y):
    per = h['sheetColumn'] * h['sheetRow']
    sheet = code // per; n = code - sheet * per
    row = n // h['sheetColumn']; col = n - row * h['sheetColumn']
    X = col * h['cellWidth'] + x; Y = row * h['cellHeight'] + y
    base = h['sheetImage'] + (h['sheetSize'] * sheet) // 2
    off = base + ((h['sheetWidth'] // 8) * (Y // 8) + X // 8) * 16 + (Y % 8) * 2 + (X % 8) // 4
    return off, 6 - 2 * (X % 4)


def glyph(f, h, code):
    rows = []
    for y in range(h['cellHeight']):
        r = ''
        for x in range(h['cellWidth']):
            o, s = texel_off(h, code, x, y)
            r += ' .:#'[(f[o] >> s) & 3]
        rows.append(r)
    return rows
