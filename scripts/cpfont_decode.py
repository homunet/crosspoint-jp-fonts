#!/usr/bin/env python3
"""Decoder / validator / previewer for CrossPoint .cpfont (v4) files.

Mirrors the firmware loader (lib/EpdFont/SdCardFont.cpp) validation, and renders
text to a PNG using the 4 gray levels (0 = white ... 3 = black).

  cpfont_decode.py info  FILE
  cpfont_decode.py render FILE OUT.png [--text STR] [--scale N]
  cpfont_decode.py compare A B          # structural diff (everything but bitmap bytes)
  cpfont_decode.py preview OUT.png A B [--text STR] [--scale N]   # stacked A over B
"""
import struct, sys, argparse
from PIL import Image, ImageDraw

MAX_INTERVALS, MAX_GLYPHS, MAX_KERN = 4096, 65536, 4096
GLYPH_FMT = "<BBHhhH2xI"  # w, h, advance(12.4), left, top, data_len, data_off
SAMPLE = "吾輩は猫である。名前はまだ無い。どこで生れたかとんと見当がつかぬ。\n何でも薄暗いじめじめした所でニャーニャー泣いていた事だけは記憶している。"


class Style:
    pass


class CpFont:
    def __init__(self, path):
        self.path = path
        d = self.data = open(path, "rb").read()
        self.problems = []
        magic, ver, flags, nstyles = struct.unpack_from("<8sHHB", d, 0)
        self.magic, self.version, self.flags, self.style_count = magic, ver, flags, nstyles
        self.header_raw = d[:32]
        if magic != b"CPFONT\0\0":
            raise ValueError("bad magic")
        self.styles = {}
        for i in range(nstyles):
            toc = d[32 + 32 * i: 64 + 32 * i]
            s = Style()
            s.toc_raw = toc
            (s.id, s.n_iv, s.n_gl, s.advY, s.asc, s.desc, s.kl, s.kr,
             s.klc, s.krc, s.nlig, s.off) = struct.unpack("<B3xIIBhhHHBBBI4x", toc)
            s.iv_off = s.off
            s.gl_off = s.iv_off + 12 * s.n_iv
            s.kl_off = s.gl_off + 16 * s.n_gl
            s.kr_off = s.kl_off + 3 * s.kl
            s.km_off = s.kr_off + 3 * s.kr
            s.lig_off = s.km_off + s.klc * s.krc
            s.bm_off = s.lig_off + 8 * s.nlig
            s.intervals = [struct.unpack_from("<III", d, s.iv_off + 12 * j) for j in range(s.n_iv)]
            s.glyphs = [struct.unpack_from(GLYPH_FMT, d, s.gl_off + 16 * j) for j in range(s.n_gl)]
            self.styles[s.id] = s
            self._validate(s)
        order = sorted(self.styles.values(), key=lambda x: x.off)
        for a, b in zip(order, order[1:]):
            if a.end != b.off:
                self.problems.append(f"style {a.id} ends at {a.end} but style {b.id} starts at {b.off}")
        if order[-1].end != len(self.data):
            self.problems.append(f"file size {len(self.data)} != expected {order[-1].end}")

    def _validate(self, s):
        p = self.problems.append
        if self.version != 4:
            p(f"version {self.version} != 4")
        if s.n_iv > MAX_INTERVALS:
            p(f"style {s.id}: intervalCount {s.n_iv} > firmware MAX_INTERVALS {MAX_INTERVALS} (loader rejects file)")
        if s.n_gl > MAX_GLYPHS:
            p(f"style {s.id}: glyphCount {s.n_gl} > MAX_GLYPHS {MAX_GLYPHS}")
        if s.kl > MAX_KERN or s.kr > MAX_KERN:
            p(f"style {s.id}: kern entries too many")
        exp, prev = 0, -1
        for j, (a, b, o) in enumerate(s.intervals):
            span = b - a + 1
            if a > b or a <= prev or span > s.n_gl or o != exp or o > s.n_gl - span:
                p(f"style {s.id}: bad interval {j} ({a:#x}-{b:#x} off={o} expected {exp})")
                break
            exp += span
            prev = b
        if exp != s.n_gl:
            p(f"style {s.id}: intervals cover {exp} glyphs but glyphCount={s.n_gl}")
        # bitmap bounds / data_length consistency
        total = 0
        for k, g in enumerate(s.glyphs):
            w, h, adv, l, t, dl, do = g
            need = (w * h + 3) // 4
            if dl != need:
                p(f"style {s.id}: glyph #{k} data_length {dl} != ceil(w*h/4)={need}")
                break
            if do != total:
                p(f"style {s.id}: glyph #{k} data_offset {do} != running {total}")
                break
            total += dl
        s.bitmap_total = total
        s.end = s.bm_off + total
        if self.style_count == 1 and s.end != len(self.data):
            p(f"style {s.id}: file size {len(self.data)} != expected {s.end}")

    def glyph_index(self, s, cp):
        for a, b, o in s.intervals:
            if a <= cp <= b:
                return o + cp - a
        return None

    def glyph_pixels(self, s, idx):
        w, h, adv, l, t, dl, do = s.glyphs[idx]
        raw = self.data[s.bm_off + do: s.bm_off + do + dl]
        px = []
        for i in range(w * h):
            px.append((raw[i >> 2] >> (6 - 2 * (i & 3))) & 3)
        return w, h, px


def render(font, text, scale=2, style_id=0, margin=8, cols=None):
    s = font.styles[style_id]
    lines = text.split("\n")
    lh = s.advY
    # 12.4 fixed advance
    widths = []
    for ln in lines:
        x = 0
        for ch in ln:
            gi = font.glyph_index(s, ord(ch))
            x += (s.glyphs[gi][2] / 16.0) if gi is not None else 0
        widths.append(x)
    W = int(max(widths) + 2 * margin) + 1
    H = lh * len(lines) + 2 * margin
    img = Image.new("L", (W, H), 255)
    pix = img.load()
    lut = {0: 255, 1: 170, 2: 85, 3: 0}
    for li, ln in enumerate(lines):
        x = float(margin)
        base = margin + li * lh + s.asc
        for ch in ln:
            gi = font.glyph_index(s, ord(ch))
            if gi is None:
                continue
            w, h, px = font.glyph_pixels(s, gi)
            g = s.glyphs[gi]
            ox, oy = int(round(x)) + g[3], base - g[4]
            for yy in range(h):
                for xx in range(w):
                    v = px[yy * w + xx]
                    X, Y = ox + xx, oy + yy
                    if v and 0 <= X < W and 0 <= Y < H:
                        pix[X, Y] = min(pix[X, Y], lut[v])
            x += g[2] / 16.0
    if scale != 1:
        img = img.resize((W * scale, H * scale), Image.NEAREST)
    return img


def hist(font, style_id=0):
    s = font.styles[style_id]
    c = [0, 0, 0, 0]
    for b in font.data[s.bm_off:s.bm_off + s.bitmap_total]:
        for k in range(4):
            c[(b >> (2 * k)) & 3] += 1
    n = sum(c) or 1
    return [f"{x / n * 100:.1f}%" for x in c]


def cmd_info(a):
    f = CpFont(a.file)
    print(f"{a.file}: {len(f.data)} bytes, version {f.version}, flags {f.flags}, styles {f.style_count}")
    for s in f.styles.values():
        print(f"  style {s.id}: intervals={s.n_iv} glyphs={s.n_gl} advY={s.advY} asc={s.asc} desc={s.desc} "
              f"kernL/R={s.kl}/{s.kr} cls={s.klc}x{s.krc} lig={s.nlig} bitmap={s.bitmap_total}B")
        print(f"    pixel level histogram (0..3, 2-bit pixels incl. padding): {hist(f, s.id)}")
        mw = max(g[0] for g in s.glyphs); mh = max(g[1] for g in s.glyphs)
        print(f"    max glyph box {mw}x{mh}")
    if f.problems:
        print("  PROBLEMS:")
        for p in f.problems:
            print("   -", p)
    else:
        print("  validation: OK (matches firmware loader checks)")
    return 1 if f.problems else 0


def cmd_render(a):
    f = CpFont(a.file)
    render(f, a.text.replace("\\n", "\n"), a.scale).save(a.out)
    print("wrote", a.out)


def cmd_compare(a):
    A, B = CpFont(a.a), CpFont(a.b)
    ok = True
    def chk(name, x, y):
        nonlocal ok
        if x != y:
            ok = False
            print(f"DIFF {name}: {x!r} != {y!r}")
    chk("header", A.header_raw, B.header_raw)
    chk("style ids", sorted(A.styles), sorted(B.styles))
    for i in A.styles:
        sa, sb = A.styles[i], B.styles[i]
        chk("toc", sa.toc_raw, sb.toc_raw)
        chk("intervals", sa.intervals, sb.intervals)
        if a.bbox_ok:
            chk("glyph advances", [g[2] for g in sa.glyphs], [g[2] for g in sb.glyphs])
            nb = sum(1 for g1, g2 in zip(sa.glyphs, sb.glyphs) if g1[:2] + g1[3:5] != g2[:2] + g2[3:5])
            print(f"style {i}: {nb}/{sa.n_gl} glyphs have a different bbox (w,h,left,top) -- expected without hinting")
            dw = [g2[0] - g1[0] for g1, g2 in zip(sa.glyphs, sb.glyphs)]
            dh = [g2[1] - g1[1] for g1, g2 in zip(sa.glyphs, sb.glyphs)]
            print(f"   width delta range {min(dw)}..{max(dw)}, height delta range {min(dh)}..{max(dh)}")
            chk("kern/lig sections", A.data[sa.kl_off:sa.bm_off], B.data[sb.kl_off:sb.bm_off])
            print(f"style {i}: bitmap bytes {sa.bitmap_total} -> {sb.bitmap_total}")
            continue
        chk("glyph metadata", sa.glyphs, sb.glyphs)  # includes data_length/data_offset
        chk("kern/lig sections", A.data[sa.kl_off:sa.bm_off], B.data[sb.kl_off:sb.bm_off])
        chk("bitmap length", sa.bitmap_total, sb.bitmap_total)
        n = sum(1 for k, (g1, g2) in enumerate(zip(sa.glyphs, sb.glyphs))
                if A.data[sa.bm_off + g1[6]: sa.bm_off + g1[6] + g1[5]] != B.data[sb.bm_off + g2[6]: sb.bm_off + g2[6] + g2[5]])
        print(f"style {i}: {n}/{sa.n_gl} glyph bitmaps differ")
    print("STRUCTURALLY IDENTICAL (only bitmap bytes differ)" if ok else "STRUCTURE DIFFERS")
    return 0 if ok else 1


def cmd_preview(a):
    imgs = [render(CpFont(p), a.text.replace("\\n", "\n"), a.scale) for p in (a.a, a.b)]
    W = max(i.width for i in imgs); H = sum(i.height for i in imgs) + 60
    out = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(out)
    y = 0
    for label, im in zip(a.labels, imgs):
        d.text((4, y + 2), label, fill=0)
        out.paste(im, (0, y + 16))
        y += im.height + 30
    out.crop((0, 0, W, y)).save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("info"); p.add_argument("file"); p.set_defaults(fn=cmd_info)
    p = sp.add_parser("render"); p.add_argument("file"); p.add_argument("out")
    p.add_argument("--text", default=SAMPLE); p.add_argument("--scale", type=int, default=3); p.set_defaults(fn=cmd_render)
    p = sp.add_parser("compare"); p.add_argument("a"); p.add_argument("b"); p.add_argument("--bbox-ok", action="store_true"); p.set_defaults(fn=cmd_compare)
    p = sp.add_parser("preview"); p.add_argument("out"); p.add_argument("a"); p.add_argument("b")
    p.add_argument("--labels", nargs=2, default=["baseline (stock)", "smooth"])
    p.add_argument("--text", default=SAMPLE); p.add_argument("--scale", type=int, default=3); p.set_defaults(fn=cmd_preview)
    a = ap.parse_args()
    sys.exit(a.fn(a) or 0)
