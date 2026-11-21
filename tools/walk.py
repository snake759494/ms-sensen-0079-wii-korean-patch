import sys,glob,os;sys.path.insert(0,os.path.dirname(__file__));import u8,xbf
def files(root='ext/DATA/files'):
    return sorted(glob.glob(root+'/**/*.arc',recursive=True)+glob.glob(root+'/**/*.xbf',recursive=True))
def walk(b,path,cb):
    if b[:4]==b'XBF\0': cb(path,b); return
    if b[:4]!=b'U\xaa8-': return
    for p,d in u8.parse(b):
        if d: walk(d,path+'|'+p,cb)
