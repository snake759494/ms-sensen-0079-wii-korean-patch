"""brres 텍스처 속 일본어 글자 한글화. build.py 에서 brres 데이터를 넘겨받아 해당 TEX0 데이터를 같은 크기/포맷으로 덮어쓴다."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import tex
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(W, 'fonts')
GOTHIC = os.path.join(ROOT, 'NanumSquareNeo-dEb.ttf')
GOTHIC_H = os.path.join(ROOT, 'NanumSquareNeo-eHv.ttf')
SERIF = os.path.join(ROOT, 'SeoulHangangEB.ttf')

TELOP = {}
for l in open(os.path.join(W, 'text/telop_ko.txt'), encoding='utf8'):
    if l.strip():
        c, k = l.rstrip('\n').split(' ', 1); TELOP[c] = k


def val(p):
    """픽셀의 '글자 세기' (알파 또는 밝기)"""
    r, g, b, a = p
    return min(a, max(r, g, b))


def tight(im, box, th=60):
    x0, y0, x1, y1 = box; px = im.load()
    xs = []; ys = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if val(px[x, y]) > th: xs.append(x); ys.append(y)
    if not xs: return None
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def draw_text(im, box, text, font=GOTHIC, align='c', clear=None, color=(255, 255, 255), vertical=False,
              outline=None, pad=0):
    """box(타이트 bbox)를 지우고 그 안에 text 를 그린다."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    px = im.load()
    if clear is None: clear = (0, 0, 0, 0)
    for y in range(y0 - pad, y1 + pad):
        for x in range(x0 - pad, x1 + pad):
            if 0 <= x < im.width and 0 <= y < im.height: px[x, y] = clear
    S = 4
    if vertical:
        n = len(text); cell = h / n
        for i, ch in enumerate(text):
            sub = (x0, int(y0 + i * cell), x1, int(y0 + (i + 1) * cell))
            draw_text(im, sub, ch, font, 'c', clear, color, outline=outline)
        return
    ft = ImageFont.truetype(font, h * S)
    tmp = Image.new('L', (1, 1)); dr = ImageDraw.Draw(tmp)
    l, t, r, b = dr.textbbox((0, 0), text, font=ft)
    # 높이 맞춤: 글자 실제 높이(가/한 기준)를 h 로
    l2, t2, r2, b2 = dr.textbbox((0, 0), '한', font=ft)
    scale = h * S / (b2 - t2)
    ft = ImageFont.truetype(font, max(4, int(h * S * scale)))
    l, t, r, b = dr.textbbox((0, 0), text, font=ft)
    l2, t2, r2, b2 = dr.textbbox((0, 0), '한', font=ft)
    tw, th = r - l, b2 - t2
    big = Image.new('L', (tw + 8 * S, h * S + 8 * S), 0)
    ImageDraw.Draw(big).text((4 * S - l, 4 * S - t2), text, font=ft, fill=255)
    big = big.crop((0, 0, big.width, h * S + 8 * S))
    nw = (tw + 8 * S) / S
    if nw - 8 > w: nw = w + 8 * (w / (nw - 8))  # 가로 압축
    sm = big.resize((max(1, round(nw)), h + 8), Image.LANCZOS)
    inner = sm.width - 8 * sm.width / ((tw + 8 * S) / S) if False else sm.width
    # 실제 글자 영역
    bb = sm.getbbox() or (0, 0, sm.width, sm.height)
    gw = bb[2] - bb[0]
    if align == 'l': ox = x0 - bb[0]
    elif align == 'r': ox = x1 - bb[2]
    else: ox = x0 + (w - gw) // 2 - bb[0]
    oy = y0 - 4
    if outline is not None:
        o = sm.filter(ImageFilter.MaxFilter(3))
        for yy in range(o.height):
            for xx in range(o.width):
                v = o.getpixel((xx, yy)); X, Y = ox + xx, oy + yy
                if v and 0 <= X < im.width and 0 <= Y < im.height:
                    base = px[X, Y]; a = v / 255
                    px[X, Y] = tuple(int(base[i] * (1 - a) + outline[i] * a) for i in range(3)) + (max(base[3], v),)
    for yy in range(sm.height):
        for xx in range(sm.width):
            v = sm.getpixel((xx, yy)); X, Y = ox + xx, oy + yy
            if v and 0 <= X < im.width and 0 <= Y < im.height:
                base = px[X, Y]; a = v / 255
                px[X, Y] = tuple(int(base[i] * (1 - a) + color[i] * a) for i in range(3)) + (max(base[3], v),)


def bgcolor(im, box):
    x0, y0, x1, y1 = box; px = im.load(); cs = {}
    for x in range(x0, x1):
        for y in (y0, y1 - 1):
            c = px[x, y]; cs[c] = cs.get(c, 0) + 1
    return max(cs, key=cs.get)


def rep(im, rough, text, **kw):
    b = tight(im, rough, kw.pop('th', 60))
    if b is None: return
    clear = kw.pop('clear', None)
    if clear == 'bg': clear = bgcolor(im, (rough[0], rough[1], rough[2], rough[3]))
    draw_text(im, b, text, clear=clear, **kw)


# ---- 텍스처별 처리 ----
def f_tutorial(im):
    rep(im, (0, 0, 243, 26), '튜토리얼 그만두기', align='l')
    rep(im, (0, 44, 100, 70), '다음으로', align='l')
    rep(im, (0, 70, 140, 95), '다시 듣기', align='l')
    rep(im, (200, 46, 238, 68), '뒤로', align='l')
    rep(im, (200, 68, 238, 92), '결정', align='l')


def f_2ppause(im):
    rep(im, (198, 46, 238, 67), '뒤로', align='l')
    rep(im, (198, 67, 238, 90), '결정', align='l')


def f_ind05(im):
    rep(im, (0, 0, 124, 30), '교환 가능')
    rep(im, (124, 0, 244, 30), '교환 불가')
    rep(im, (16, 30, 110, 58), '보급 중')


def f_ef00(im):
    px = im.load()
    b = (206, 28, 219, 127)
    hole = [(x, y) for y in range(b[1], b[3]) for x in range(b[0], b[2]) if px[x, y][3] < 128 or max(px[x, y][:3]) < 128]
    if hole:
        xs = [p[0] for p in hole]; ys = [p[1] for p in hole]
        tb = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
        # 게임은 이 세로 띠를 반시계 90° 돌려 가로로 표시 -> 가로로 그려 시계 90° 회전해 넣는다
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        sub = Image.new('RGBA', (th, tw), (255, 255, 255, 255))
        draw_text(sub, (2, 1, th - 2, tw - 1), '보급 가능', clear=(255, 255, 255, 255), color=(0, 0, 40))
        im.paste(sub.rotate(-90, expand=True), (tb[0], tb[1]))
    rep(im, (108, 161, 216, 174), '격투 가능', th=15)
    rep(im, (128, 202, 234, 215), '사정거리 밖', th=15)


def f_ze00(im):
    rep(im, (12, 171, 112, 185), '격투 가능', th=15)
    rep(im, (12, 192, 112, 206), '사정거리 밖', th=15)
    rep(im, (12, 213, 112, 227), '보급 가능', th=15)


def f_sal(im):
    rep(im, (0, 0, 128, 32), '선택 불가', align='l')


def f_chat1(im):
    rep(im, (40, 40, 245, 70), '앨런 아일워드', align='r')
    rep(im, (40, 78, 245, 106), '레오 브라우어', align='r')
    rep(im, (10, 114, 245, 142), '릴 소머즈', align='l')
    rep(im, (10, 150, 245, 180), '데니스 배로우', align='l')
    rep(im, (10, 186, 245, 216), '호아 블랑셰트', align='l')


def f_chat2(im):
    rep(im, (10, 4, 245, 32), '토르드 보브로프', align='l')
    rep(im, (10, 40, 245, 68), '클라우스 베르트랑', align='l')
    rep(im, (10, 78, 245, 106), '앤 프리베리', align='l')


def f_gsh(im):
    px = im.load()
    box = (14, 40, 116, 68)
    mask = set()
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            if max(px[x, y][:3]) > 110: mask.add((x, y))
    # 주변 dilate 1
    mask2 = set(mask)
    for (x, y) in mask:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1): mask2.add((x + dx, y + dy))
    todo = set(mask2)
    while todo:
        nxt = set()
        for (x, y) in todo:
            ns = [px[x + dx, y + dy] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if (x + dx, y + dy) not in todo and 0 <= x + dx < im.width and 0 <= y + dy < im.height]
            if ns: px[x, y] = tuple(sum(c[i] for c in ns) // len(ns) for i in range(4))
            else: nxt.add((x, y))
        if nxt == todo: break
        todo = nxt
    draw_text(im, (24, 45, 146, 64), '기니아스', clear=None, outline=(0, 0, 0), pad=-100) if False else None
    _draw_over(im, (18, 44, 112, 64), "기니아스")


def _draw_over(im, box, text):
    """배경 지우지 않고 글자만 그림"""
    x0, y0, x1, y1 = box
    sub = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0))
    draw_text(sub, (0, 0, sub.width, sub.height), text, font=GOTHIC_H, outline=(0, 0, 0))
    im.alpha_composite(sub, (x0, y0))


def f_telop(code):
    def f(im):
        k = TELOP[code]
        px = im.load()
        for y in range(im.height):
            for x in range(im.width): px[x, y] = (0, 0, 0, 255)
        draw_text(im, (12, 18, 1012, 58), k, font=SERIF, clear=(0, 0, 0, 255))
    return f


def handler(path, name):
    """path: 아카이브 경로 문자열, name: 텍스처 이름 -> 함수 또는 None"""
    if name == 'ME01_TELOP' and 'TELOP_' in path:
        code = path.split('TELOP_')[1][:4]
        if code in TELOP: return f_telop(code)
    return {'Tutorial_00': f_tutorial, '2P_PAUSE': f_2ppause, 'EF_Indicator05': f_ind05,
            'EF_Indicator00': f_ef00, 'ZE_Indicator00': f_ze00, 'SAL01': f_sal,
            'CHAT_name1': f_chat1, 'CHAT_name2': f_chat2, 'GSH_MSG_Window_01': f_gsh}.get(name)


def patch_brres(path, d):
    out = bytearray(d); ch = False
    for off, name, w, h, fmt, mips, doff in tex.find(d):
        fn = handler(path, name)
        if not fn: continue
        im = tex.decode(d, doff, w, h, fmt)
        fn(im)
        nb = tex.encode(im, fmt)
        n = tex.size(w, h, fmt)
        assert len(nb) == n, (name, len(nb), n)
        out[doff:doff + n] = nb; ch = True
        if mips > 1:
            # 밉맵도 축소본으로 갱신
            p = doff + n; mw, mh = w, h
            for _ in range(mips - 1):
                mw, mh = max(1, mw // 2), max(1, mh // 2)
                m = im.resize((mw, mh), Image.LANCZOS)
                mb = tex.encode(m, fmt); out[p:p + len(mb)] = mb; p += len(mb)
    return bytes(out) if ch else d
