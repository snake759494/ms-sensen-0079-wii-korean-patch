"""NORMAL_FONT 계열 brfnt 에 한글 글리프를 넣는다. 쓰지 않게 된 한자 슬롯을 재사용한다."""
import sys, os, hashlib
sys.path.insert(0, os.path.dirname(__file__))
import brfnt
from PIL import Image, ImageDraw, ImageFont

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(W, 'fonts', 'NanumSquareNeo-dEb.ttf')


def ks2350():
    out = []
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            try: out.append(bytes([hi, lo]).decode('euc-kr'))
            except UnicodeDecodeError: pass
    return out


_cache = {}


def render(ch, cw, ch_h, size, ybase):
    key = (ch, cw, ch_h, size, ybase)
    if key in _cache: return _cache[key]
    ft = ImageFont.truetype(FONT, size)
    big = Image.new('L', (cw * 4, ch_h * 4), 0)
    dr = ImageDraw.Draw(big)
    # 4배 크기로 그린 뒤 축소(안티앨리어싱)
    ft4 = ImageFont.truetype(FONT, size * 4)
    l, t, r, b = dr.textbbox((0, 0), ch, font=ft4, anchor='ls')
    w = (r - l) / 4
    x = (cw * 4 - (r - l)) / 2 - l
    dr.text((x, ybase * 4), ch, fill=255, font=ft4, anchor='ls')
    im = big.resize((cw, ch_h), Image.LANCZOS)
    im = im.point(lambda v: min(255, int(v * 1.15)))
    _cache[key] = im
    return im


def patch(data, chars, size=19, ybase=18):
    f = brfnt.load(data)
    cw, chh = f['cw'], f['ch']
    hang = sorted(set(c for c in chars if 0xAC00 <= ord(c) <= 0xD7A3) | set(ks2350()))
    # 한자 슬롯 회수
    kanji = sorted(c for c in f['cmap'] if 0x4E00 <= c <= 0x9FFF)
    free = [f['cmap'].pop(c) for c in kanji]
    free.sort()
    glyphs = []
    for i, c in enumerate(hang):
        im = render(c, cw, chh, size, ybase)
        bb = im.getbbox() or (0, 0, cw, chh)
        w = (1, 17, 18) if cw == 20 else (0, cw, cw)
        if i < len(free):
            g = free[i]
            f['cmap'][ord(c)] = g
        glyphs.append((ord(c), im, w))
    brfnt.add_glyphs(f, glyphs)
    return brfnt.build(f)


if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    out = patch(d, '')
    open(sys.argv[2], 'wb').write(out)
    print(len(d), len(out))
