import struct, sys, json, os, collections

# (block_size, type_size_bytes) per GGML type id, from ggml.h
T = {
 0:("F32",1,4), 1:("F16",1,2), 2:("Q4_0",32,18), 3:("Q4_1",32,20),
 6:("Q5_0",32,22), 7:("Q5_1",32,24), 8:("Q8_0",32,34), 9:("Q8_1",32,36),
 10:("Q2_K",256,84), 11:("Q3_K",256,110), 12:("Q4_K",256,144),
 13:("Q5_K",256,176), 14:("Q6_K",256,210), 15:("Q8_K",256,292),
 16:("IQ2_XXS",256,66), 17:("IQ2_XS",256,74), 18:("IQ3_XXS",256,98),
 19:("IQ1_S",256,50), 20:("IQ4_NL",32,18), 21:("IQ3_S",256,110),
 22:("IQ2_S",256,82), 23:("IQ4_XS",256,136), 24:("I8",1,1), 25:("I16",1,2),
 26:("I32",1,4), 27:("I64",1,8), 28:("F64",1,8), 29:("IQ1_M",256,56),
 30:("BF16",1,2), 34:("TQ1_0",256,54), 35:("TQ2_0",256,66), 39:("MXFP4",32,17),
}

class R:
    def __init__(s, f): s.f = f
    def raw(s, n):
        b = s.f.read(n)
        if len(b) != n: raise EOFError("short read")
        return b
    def u32(s): return struct.unpack("<I", s.raw(4))[0]
    def u64(s): return struct.unpack("<Q", s.raw(8))[0]
    def st(s):
        n = s.u64()
        return s.raw(n).decode("utf-8", "replace")

# GGUF metadata value type ids -> (struct fmt, size) for scalars
SC = {0:("<B",1),1:("<b",1),2:("<H",2),3:("<h",2),4:("<I",4),5:("<i",4),
      6:("<f",4),7:("<?",1),10:("<Q",8),11:("<q",8),12:("<d",8)}

def rdval(r, vt):
    if vt in SC:
        fmt, n = SC[vt]
        return struct.unpack(fmt, r.raw(n))[0]
    if vt == 8:  # string
        return r.st()
    if vt == 9:  # array
        et = r.u32(); n = r.u64()
        if et == 8:
            # strings: read them but only keep a few (vocab can be 150k)
            out = []
            for i in range(n):
                v = r.st()
                if i < 3: out.append(v)
            return {"_array_str": n, "_head": out}
        if et == 9:
            return {"_nested_array": n}
        fmt, sz = SC[et]
        buf = r.raw(sz * n)
        vals = list(struct.unpack("<" + fmt[1] * n, buf)) if n else []
        return vals if n <= 16 else {"_array": n, "_head": vals[:8]}
    raise ValueError("unknown value type %d" % vt)

def scan(path):
    with open(path, "rb", buffering=1024 * 1024) as f:
        r = R(f)
        if r.raw(4) != b"GGUF": raise ValueError("not a GGUF file")
        ver = r.u32(); ntensor = r.u64(); nkv = r.u64()
        meta = {}
        for _ in range(nkv):
            k = r.st(); vt = r.u32()
            meta[k] = rdval(r, vt)
        tensors = []
        for _ in range(ntensor):
            name = r.st(); nd = r.u32()
            dims = [r.u64() for _ in range(nd)]
            tid = r.u32(); off = r.u64()
            tensors.append((name, dims, tid, off))
    return ver, meta, tensors

def report(path, label):
    ver, meta, tensors = scan(path)
    by = collections.defaultdict(lambda: [0, 0, 0])  # type -> [ntensors, params, bytes]
    tot_p = tot_b = 0
    for name, dims, tid, off in tensors:
        if tid not in T:
            print("  !! unknown ggml type id %d on %s" % (tid, name)); continue
        tname, blk, tsz = T[tid]
        n = 1
        for d in dims: n *= d
        nbytes = (n // blk) * tsz
        by[tname][0] += 1; by[tname][1] += n; by[tname][2] += nbytes
        tot_p += n; tot_b += nbytes
    bpw = tot_b * 8.0 / tot_p if tot_p else 0.0

    # FFN-only view (the axis the roster compares on)
    ffn_p = collections.defaultdict(int); ffn_tot = 0
    for name, dims, tid, off in tensors:
        if "ffn" not in name or tid not in T: continue
        n = 1
        for d in dims: n *= d
        ffn_p[T[tid][0]] += n; ffn_tot += n

    arch = meta.get("general.architecture", "?")
    blocks = meta.get("%s.block_count" % arch, "?")
    print("=" * 78)
    print("%s" % label)
    print("  file            %s" % os.path.basename(path))
    print("  size on disk    %s bytes (%.2f GiB)" % (os.path.getsize(path), os.path.getsize(path) / 2**30))
    print("  gguf version    %s   tensors %d   kv %d" % (ver, len(tensors), len(meta)))
    print("  arch            %s   block_count %s" % (arch, blocks))
    for k in ("general.name", "general.size_label", "general.file_type",
              "%s.context_length" % arch, "%s.embedding_length" % arch,
              "%s.attention.head_count" % arch, "%s.attention.head_count_kv" % arch,
              "%s.attention.key_length" % arch, "%s.expert_count" % arch,
              "%s.expert_used_count" % arch, "%s.rope.freq_base" % arch,
              "%s.full_attention_interval" % arch, "%s.linear_attention_interval" % arch):
        if k in meta: print("  %-28s %s" % (k.split(".", 1)[-1], meta[k]))
    mtp = [n for n, d, t, o in tensors if "nextn" in n or "mtp" in n.lower()]
    lastblk = sorted({int(n.split(".")[1]) for n, d, t, o in tensors
                      if n.startswith("blk.") and n.split(".")[1].isdigit()})
    print("  blk.N present    %d..%d  (%d distinct)" % (lastblk[0], lastblk[-1], len(lastblk)) if lastblk else "  no blk.*")
    print("  MTP-ish tensors  %d %s" % (len(mtp), mtp[:3]))
    print("  TOTAL params    %s" % f"{tot_p:,}")
    print("  TOTAL weights   %s bytes (%.0f MiB)" % (f"{tot_b:,}", tot_b / 2**20))
    print("  >> EFFECTIVE BPW  %.3f" % bpw)
    print("  per-type breakdown (share of params):")
    for tname, (nt, p, b) in sorted(by.items(), key=lambda kv: -kv[1][1]):
        print("     %-9s %4d tensors  %14s params  %6.2f%%  %.3f bpw"
              % (tname, nt, f"{p:,}", 100.0 * p / tot_p, b * 8.0 / p))
    if ffn_tot:
        print("  FFN-only breakdown:")
        for tname, p in sorted(ffn_p.items(), key=lambda kv: -kv[1]):
            print("     %-9s %6.2f%%" % (tname, 100.0 * p / ffn_tot))
    return bpw

if __name__ == "__main__":
    args = sys.argv[1:]
    for i in range(0, len(args), 2):
        try:
            report(args[i], args[i + 1])
        except Exception as e:
            print("=" * 78); print("%s\n  FAILED: %r" % (args[i + 1], e))
