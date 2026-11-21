"""이벤트(gev, SJIS ROM 폰트) 한글화.
- 한글 음절을 SJIS 1수준 한자 코드에 할당
- main.dol 에 새 섹션(코드+글리프)을 넣고 OSLoadFont 끝에서 ROM 폰트 시트의 해당 한자 칸을 한글로 덮어쓴다.
"""
import sys, os, json, struct, re
sys.path.insert(0, os.path.dirname(__file__))
import romfont
from PIL import Image, ImageDraw, ImageFont

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(W, 'fonts', 'NanumSquareNeo-dEb.ttf')
SECT = 0x80467920          # 기존 ArenaLo
ARENA_LIS = 0x8032e8d4      # lis r3,0x8046 ; addi r3,r3,0x7920
ARENA_LIS2 = 0x8032e924     # lis r3,0x8046 ; addi r3,r3,0x5910
HOOK = 0x80334750           # OSInitFont: li r3,1 (ExpandFontSheet 이후)
HOOK_RET = 0x80334754


def load():
    items = json.load(open(os.path.join(W, 'text/gev.json'), encoding='utf8'))
    tr = json.load(open(os.path.join(W, 'text/tr_gev.json'), encoding='utf8'))
    return items, {int(k): v for k, v in tr.items()}


def mapping(items, tr):
    used = set()
    for it in items:
        used |= set(c for c in it['jp'] if '一' <= c <= '鿿')
    hang = sorted(set(c for v in tr.values() for c in v if '가' <= c <= '힣'))
    m = {}
    codes = []
    for hi in range(0x88, 0x99):
        for lo in range(0x40, 0xfd):
            sj = hi << 8 | lo
            if not (0x889e < sj <= 0x9872) or lo == 0x7f: continue
            try: ch = bytes([hi, lo]).decode('cp932')
            except UnicodeDecodeError: continue
            if ch in used: continue
            codes.append(sj)
    assert len(codes) >= len(hang), (len(codes), len(hang))
    for c, sj in zip(hang, codes): m[c] = sj
    return m


def encode(s, m):
    out = b''
    for c in s:
        if c in m: out += struct.pack('>H', m[c])
        else: out += c.encode('cp932')
    return out


def table(items, tr, m):
    """jp(str) -> 새 bytes"""
    t = {}
    for it in items:
        if it['id'] in tr: t[it['jp']] = encode(tr[it['id']], m)
    return t


def render(ch, size=19):
    S = 4
    ft = ImageFont.truetype(FONT, size * S)
    big = Image.new('L', (24 * S, 24 * S), 0)
    dr = ImageDraw.Draw(big)
    l, t, r, b = dr.textbbox((0, 0), '한', font=ft, anchor='ls')
    y0 = (12 * S) - (t + b) / 2
    l, t, r, b = dr.textbbox((0, 0), ch, font=ft, anchor='ls')
    x = (20 * S - (r - l)) / 2 - l
    dr.text((x, y0), ch, fill=255, font=ft, anchor='ls')
    im = big.resize((24, 24), Image.LANCZOS)
    px = []
    for y in range(24):
        for xx in range(24):
            v = im.getpixel((xx, y))
            px.append(min(15, int(v * 15 / 255 + 0.3)))
    return px


def pack(px):
    out = bytearray(288)
    for p, v in enumerate(px):
        out[p >> 1] |= v << (0 if p & 1 else 4)
    return bytes(out)


# ---- 간이 PPC 어셈블러 ----
def D(op, rt, ra, d): return op << 26 | rt << 21 | ra << 16 | (d & 0xffff)
def X(rt, ra, rb, xo): return 31 << 26 | rt << 21 | ra << 16 | rb << 11 | xo << 1
def rlwinm(ra, rs, sh, mb, me): return 21 << 26 | rs << 21 | ra << 16 | sh << 11 | mb << 6 | me << 1
def srwi(ra, rs, n): return rlwinm(ra, rs, 32 - n, n, 31)
def slwi(ra, rs, n): return rlwinm(ra, rs, n, 0, 31 - n)
def cmpwi(ra, v): return 11 << 26 | ra << 16 | (v & 0xffff)
def li(rt, v): return D(14, rt, 0, v)


def code(blob_addr):
    ins = []; labels = {}; fix = []
    def L(n): labels[n] = len(ins)
    def br(kind, n): fix.append((len(ins), kind, n)); ins.append(0)
    e = ins.append
    e(D(37, 1, 1, -0x40))                 # stwu r1,-0x40(r1)
    e(D(47, 20, 1, 8))                    # stmw r20,8(r1)
    e(D(32, 3, 13, -0x5500))              # lwz r3,-0x5500(r13)
    e(cmpwi(3, 0)); br('beq', 'done')
    ha = (blob_addr + 0x8000) >> 16 & 0xffff
    e(D(15, 4, 0, ha)); e(D(14, 4, 4, blob_addr & 0xffff))
    e(D(32, 5, 4, 0)); e(D(14, 4, 4, 4))
    e(D(40, 20, 3, 0x1a)); e(D(40, 21, 3, 0x1c)); e(X(22, 20, 21, 235))
    e(D(40, 23, 3, 0x1e)); e(srwi(23, 23, 3))
    e(D(32, 24, 3, 0x14)); e(D(32, 25, 3, 0x24)); e(X(25, 25, 3, 266))
    L('g')
    e(cmpwi(5, 0)); br('beq', 'done')
    e(D(32, 6, 4, 0)); e(D(14, 4, 4, 4))
    e(X(7, 6, 22, 459))                   # divwu r7,r6,r22
    e(X(8, 7, 22, 235)); e(X(8, 8, 6, 40))  # r8 = r6 - r7*r22
    e(X(9, 8, 20, 459))
    e(X(10, 9, 20, 235)); e(X(10, 10, 8, 40))
    e(D(7, 9, 9, 24)); e(D(7, 10, 10, 24))
    e(X(7, 7, 24, 235)); e(X(26, 25, 7, 266))
    e(li(11, 0))
    L('y')
    e(li(12, 0))
    L('x')
    e(D(7, 27, 11, 24)); e(X(27, 27, 12, 266))
    e(srwi(28, 27, 1)); e(X(28, 4, 28, 87))          # lbzx r28,r4,r28
    e(rlwinm(29, 27, 2, 29, 29)); e(D(8, 29, 29, 4))  # subfic r29,r29,4
    e(X(28, 28, 29, 536))                            # srw r28,r28,r29
    e(D(28, 28, 28, 15))                             # andi. r28,r28,15
    e(X(27, 10, 12, 266)); e(X(29, 9, 11, 266))
    e(srwi(30, 29, 3)); e(X(30, 30, 23, 235)); e(srwi(31, 27, 3)); e(X(30, 30, 31, 266)); e(slwi(30, 30, 5))
    e(rlwinm(31, 29, 2, 27, 29)); e(X(30, 30, 31, 266))
    e(rlwinm(31, 27, 31, 30, 31)); e(X(30, 30, 31, 266))
    e(rlwinm(31, 27, 2, 29, 29)); e(D(8, 31, 31, 4))
    e(X(0, 26, 30, 87))                              # lbzx r0,r26,r30
    e(li(7, 15)); e(X(7, 7, 31, 24)); e(X(0, 0, 7, 60))   # slw r7,r7,r31 ; andc r0,r0,r7
    e(X(28, 28, 31, 24)); e(X(0, 0, 28, 444))       # slw r28,r28,r31 ; or r0,r0,r28
    e(X(0, 26, 30, 215))                             # stbx r0,r26,r30
    e(D(14, 12, 12, 1)); e(cmpwi(12, 24)); br('blt', 'x')
    e(D(14, 11, 11, 1)); e(cmpwi(11, 24)); br('blt', 'y')
    e(D(14, 4, 4, 288)); e(D(14, 5, 5, -1)); br('b', 'g')
    L('done')
    e(D(46, 20, 1, 8))                    # lmw r20,8(r1)
    e(D(14, 1, 1, 0x40))
    e(li(3, 1))                           # li r3,1
    br('ret', None)
    for i, kind, n in fix:
        if kind == 'ret':
            off = HOOK_RET - (SECT + i * 4); ins[i] = 18 << 26 | (off & 0x3fffffc)
        else:
            off = (labels[n] - i) * 4
            if kind == 'b': ins[i] = 18 << 26 | (off & 0x3fffffc)
            else:
                bi = {'beq': 2, 'blt': 0}[kind]
                bo = 12
                ins[i] = 16 << 26 | bo << 21 | bi << 16 | (off & 0xfffc)
    return b''.join(struct.pack('>I', x) for x in ins)


def patch_dol(dol, m):
    glyphs = sorted(m.items(), key=lambda kv: kv[1])
    c0 = code(0)
    blob_addr = SECT + ((len(c0) + 31) & ~31)
    c = code(blob_addr)
    blob = struct.pack('>I', len(glyphs))
    for ch, sj in glyphs:
        blob += struct.pack('>I', romfont.kanji_code(sj)) + pack(render(ch))
    sect = c + bytes(blob_addr - SECT - len(c)) + blob
    while len(sect) % 32: sect += bytes(1)
    d = bytearray(dol)
    O = list(struct.unpack('>18I', d[0:72])); A = list(struct.unpack('>18I', d[72:144])); S = list(struct.unpack('>18I', d[144:216]))
    slot = 2
    assert S[slot] == 0
    while len(d) % 32: d += bytes(1)
    O[slot] = len(d); A[slot] = SECT; S[slot] = len(sect)
    d += sect
    d[0:72] = struct.pack('>18I', *O); d[72:144] = struct.pack('>18I', *A); d[144:216] = struct.pack('>18I', *S)
    def v2o(v):
        for i in range(18):
            if S[i] and A[i] <= v < A[i] + S[i] and i != slot: return O[i] + v - A[i]
    newlo = (SECT + len(sect) + 31) & ~31
    o = v2o(ARENA_LIS)
    assert struct.unpack('>II', d[o:o + 8]) == (0x3c608046, 0x38637920)
    ha = (newlo + 0x8000) >> 16
    d[o:o + 8] = struct.pack('>II', D(15, 3, 0, ha), D(14, 3, 3, newlo & 0xffff))
    # 실제로 쓰이는 경로: lis r3,0x8046 ; addi r3,r3,0x5910 (+0x1f 정렬)
    o = v2o(ARENA_LIS2)
    assert struct.unpack('>II', d[o:o + 8]) == (0x3c608046, 0x38635910)
    d[o:o + 8] = struct.pack('>II', D(15, 3, 0, ha), D(14, 3, 3, newlo & 0xffff))
    o = v2o(HOOK)
    assert struct.unpack('>I', d[o:o + 4])[0] == 0x38600001
    d[o:o + 4] = struct.pack('>I', 18 << 26 | ((SECT - HOOK) & 0x3fffffc))
    print('gev 한글 %d자, 섹션 %#x 바이트, ArenaLo -> %#x' % (len(glyphs), len(sect), newlo))
    return bytes(d)


if __name__ == '__main__':
    items, tr = load()
    m = mapping(items, tr)
    print(len(m))
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
    c = code(SECT + 0x200)
    for i in md.disasm(c, SECT): print('%08x: %s %s' % (i.address, i.mnemonic, i.op_str))
    px = render('한')
    for y in range(24): print(''.join(' .:#'[px[y * 24 + x]] for x in range(24)))
