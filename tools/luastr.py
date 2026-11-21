import re
LB = re.compile(rb'\[(=*)\[')
def strings(d):
    """lua 소스에서 주석을 건너뛰고 문자열 리터럴 (start,end,bytes) 목록"""
    out = []; i = 0; n = len(d)
    while i < n:
        c = d[i]
        if d.startswith(b'--', i):
            m = LB.match(d, i + 2)
            if m:
                close = b']' + m.group(1) + b']'
                j = d.find(close, i); i = (j + len(close)) if j >= 0 else n
            else:
                j = d.find(b'\n', i); i = j if j >= 0 else n
            continue
        if c in (0x22, 0x27):
            j = i + 1
            while j < n and d[j] != c and d[j] != 0x0a:
                if d[j] == 0x5c: j += 1
                j += 1
            out.append((i + 1, j, d[i + 1:j])); i = j + 1; continue
        if c == 0x5b:
            m = LB.match(d, i)
            if m:
                close = b']' + m.group(1) + b']'
                j = d.find(close, i)
                out.append((m.end(), j, d[m.end():j])); i = j + len(close); continue
        i += 1
    return out
