"""$EVF gev 파일: 헤더 0x10=?,0x14=?, 0x18=오프셋표 위치, 0x1c=문자열풀 위치.
오프셋표: u16 * n (풀 기준 4바이트 단위). 풀: '$STR' + 문자열(널 포함, 4바이트 정렬)."""
import struct


def parse(d):
    assert d[:4] == b'$EVF'
    tbl, pool = struct.unpack('>II', d[0x14:0x1c])
    n = struct.unpack('>I', d[0x10:0x14])[0]
    offs = struct.unpack('>%dH' % n, d[tbl:tbl + n * 2])
    strs = []
    for o in offs:
        p = pool + o * 4
        e = d.index(b'\0', p)
        strs.append(d[p:e])
    return dict(head=d[:tbl], offs=offs, strs=strs, pool=pool, d=d)


def build(g):
    d = g['d']; n = len(g['offs'])
    tbl = struct.unpack('>I', d[0x14:0x18])[0]
    gap = d[tbl + n * 2:g['pool']]
    pool = bytearray(); newoff = {}; offs = []
    for o, s in zip(g['offs'], g['strs']):
        key = (o, s)
        if key not in newoff:
            newoff[key] = len(pool) // 4
            pool += s + bytes(1)
            while len(pool) % 4: pool += bytes(1)
        offs.append(newoff[key])
    assert len(pool) // 4 < 0x10000
    return d[:tbl] + struct.pack('>%dH' % n, *offs) + gap + bytes(pool)
