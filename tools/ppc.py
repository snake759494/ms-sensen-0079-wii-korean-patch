import struct, sys, capstone
D = open(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith('.dol') else 'ext/DATA/sys/main.dol', 'rb').read()
O = struct.unpack('>18I', D[0:72]); A = struct.unpack('>18I', D[72:144]); S = struct.unpack('>18I', D[144:216])
md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)


def v2o(v):
    for i in range(18):
        if S[i] and A[i] <= v < A[i] + S[i]: return O[i] + v - A[i]


def word(v): return struct.unpack('>I', D[v2o(v):v2o(v) + 4])[0]


def dis(v, n):
    o = v2o(v)
    for ins in md.disasm(D[o:o + n * 4], v):
        print('%08x: %s %s' % (ins.address, ins.mnemonic, ins.op_str))


def text_words():
    for i in range(7):
        if S[i]:
            for k in range(0, S[i], 4):
                yield A[i] + k, struct.unpack('>I', D[O[i] + k:O[i] + k + 4])[0]
