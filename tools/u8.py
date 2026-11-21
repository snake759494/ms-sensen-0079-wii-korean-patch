import struct
def parse(b):
    assert b[:4]==b'\x55\xaa\x38\x2d'
    root,hsz,doff=struct.unpack('>III',b[4:16])
    n=struct.unpack('>I',b[root+8:root+12])[0]
    st=root+n*12
    nodes=[]
    for i in range(n):
        t,no,do,sz=struct.unpack('>BxHII',b[root+i*12:root+i*12+12]) if False else (b[root+i*12],)+struct.unpack('>H',b[root+i*12+2:root+i*12+4])+struct.unpack('>II',b[root+i*12+4:root+i*12+12])
        name=b[st+no:b.index(b'\0',st+no)].decode('cp932')
        nodes.append([t,name,do,sz])
    # build paths
    out=[];stack=[(n,'')]
    path=''
    ends=[]
    for i in range(1,n):
        while ends and ends[-1][0]<=i: ends.pop()
        t,name,do,sz=nodes[i]
        pre='/'.join(e[1] for e in ends)
        full=(pre+'/' if pre else '')+name
        if t==1: ends.append((sz,name)); out.append((full,None))
        else: out.append((full,b[do:do+sz]))
    return out
def build(entries):
    # entries: list of (path,data|None) in original order (dirs before contents)
    # rebuild tree preserving order
    names=[''];types=[1];parents=[0];datas=[None]
    idx={'':0}
    for p,d in entries:
        par=p.rsplit('/',1)[0] if '/' in p else ''
        idx[p]=len(names); names.append(p.rsplit('/',1)[-1]); types.append(1 if d is None else 0); parents.append(idx[par]); datas.append(d)
    n=len(names)
    # dir next index: last descendant+1
    nxt=[0]*n
    for i in range(n):
        if types[i]==1:
            j=i+1
            while j<n and isanc(i,j,parents): j+=1
            nxt[i]=j
    stab=b'';noff=[]
    for nm in names: noff.append(len(stab)); stab+=nm.encode('cp932')+b'\0'
    hsz=n*12+len(stab)
    doff=(0x20+hsz+0x1f)&~0x1f
    data=b'';fo=[0]*n
    for i in range(n):
        if types[i]==0:
            data+=b'\0'*((-len(data))%32); fo[i]=doff+len(data); data+=datas[i]
    nb=b''
    for i in range(n):
        if types[i]==1: nb+=struct.pack('>BBHII',1,0,noff[i] if i else 0,0 if i==0 else depth_parent(i,parents),nxt[i])
        else: nb+=struct.pack('>BBHII',0,0,noff[i],fo[i],len(datas[i]))
    hdr=b'\x55\xaa\x38\x2d'+struct.pack('>III',0x20,hsz,doff)+b'\0'*16
    body=hdr+nb+stab
    body+=b'\0'*(doff-len(body))
    return body+data
def isanc(a,j,parents):
    while j!=0:
        j=parents[j]
        if j==a: return True
    return a==0
def depth_parent(i,parents): return parents[i]
