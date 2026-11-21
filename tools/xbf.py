import struct
def parse(d):
    assert d[:4]==b'XBF\0'
    h=struct.unpack('>9I',d[4:40])
    enc='utf8'
    try: d[h[5]:].decode('utf8')
    except UnicodeDecodeError: enc='cp932'
    _,noff,ncnt,t1,c1,t2,c2,t3,c3=h
    def lst(o,c):
        out=[]
        for _ in range(c):
            e=d.index(b'\0',o); out.append(d[o:e].decode(enc)); o=e+1
        return out,o
    tags,_=lst(t1,c1); attrs,_=lst(t2,c2); vals,end=lst(t3,c3)
    return dict(enc=enc,h=h,head=d[:t3],tags=tags,attrs=attrs,vals=vals,tail=d[end:])
def build(x):
    vb=b''.join(v.encode(x['enc'])+b'\0' for v in x['vals'])
    return x['head']+vb+x['tail']
