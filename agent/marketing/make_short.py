"""Turn recorded gameplay frames into a YouTube Short that sends viewers to the website.
usage: python3 make_short.py <game.json> <frames dir> <out dir>
game.json: {"id","title","hook","captions":[[frame,"text"],...],"yt_title","yt_desc"}
Layout: hook text over the first seconds, a small "play free" URL tag all the way through,
captions on key moments, then a 4 s end card that advertises the website (the whole point of the Short)."""
import sys, os, json, subprocess, glob, math
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); W, H, FPS = 1080, 1920, 30
SITE = "dailylayer.funny3dprint.workers.dev"; INK = (27, 37, 71)
def font(size, weight="ExtraBold", fam="Baloo2"):
    f = ImageFont.truetype(os.path.join(HERE, "fonts", fam + ".ttf"), size)
    try: f.set_variation_by_name(weight)
    except Exception: pass
    return f
def pill(d, box, fill, r=40, outline=INK, w=8, shadow=10):
    x0, y0, x1, y1 = box
    if shadow: d.rounded_rectangle((x0, y0 + shadow, x1, y1 + shadow), r, fill=outline)
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=w)
def centred(d, y, text, f, fill=INK, stroke=0, sf=None):
    w = d.textlength(text, font=f); d.text(((W - w) / 2, y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=sf)
def star(d, cx, cy, r, fill=(255, 201, 60)):
    pts = [(cx + (r if k % 2 == 0 else r * 0.45) * math.cos(-math.pi / 2 + k * math.pi / 5), cy + (r if k % 2 == 0 else r * 0.45) * math.sin(-math.pi / 2 + k * math.pi / 5)) for k in range(10)]
    d.polygon(pts, fill=fill, outline=INK, width=6)
def layer(): im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); return im, ImageDraw.Draw(im)

def hook_png(text, path):
    im, d = layer(); f = font(96); lines = text.split("\n"); hgt = 120 * len(lines) + 80
    y0 = 1080; pill(d, (60, y0, W - 60, y0 + hgt), (255, 255, 255), r=56)
    for i, ln in enumerate(lines): centred(d, y0 + 30 + i * 120, ln, f)
    im.save(path)
def tag_png(path):
    im, d = layer(); f = font(36, "Bold"); text = "Play free: " + SITE; w = d.textlength(text, font=f)
    x0 = (W - w) / 2 - 30; pill(d, (x0, 1500, W - x0, 1560), (255, 107, 87), r=30, w=5, shadow=0)
    d.text((x0 + 30, 1503), text, font=f, fill=(255, 255, 255)); im.save(path)
def caption_png(text, path):
    im, d = layer(); f = font(104); w = d.textlength(text, font=f)
    x0 = (W - w) / 2 - 110; pill(d, (x0, 760, W - x0, 930), (255, 201, 60), r=60)
    star(d, x0 + 70, 845, 44, (255, 255, 255)); d.text((x0 + 130, 768), text, font=f, fill=INK); im.save(path)
def endcard_png(game_title, icons, path):
    im = Image.new("RGB", (W, H), (220, 240, 255)); d = ImageDraw.Draw(im)
    for k in range(9):                                            # soft stripes
        d.rectangle((0, k * 240 + 120, W, k * 240 + 200), fill=(201, 232, 255))
    centred(d, 110, "Daily Layer", font(150), fill=(255, 107, 87), stroke=10, sf=INK)
    centred(d, 300, "Free games for kids", font(84), fill=INK)
    centred(d, 400, "Play in your browser. No app, no ads.", font(50, "SemiBold", "Nunito"), fill=(85, 96, 138))
    # the toys, standing in a row on a shelf
    ims = [Image.open(p).convert("RGBA") for p in icons][:8]
    if ims:
        s = 230; row = [ims[:4], ims[4:8]]
        for r, group in enumerate(row):
            if not group: continue
            tot = len(group) * s - (len(group) - 1) * 20; x = (W - tot) // 2; y = 490 + r * 260
            d.rounded_rectangle((x - 30, y + s - 30, x + tot + 30, y + s + 4), 14, fill=(233, 185, 122), outline=INK, width=6)
            for im2 in group: im.paste(im2.resize((s, s), Image.LANCZOS), (x, y), im2.resize((s, s), Image.LANCZOS)); x += s - 20
    d = ImageDraw.Draw(im)
    centred(d, 1030, "Today's game: " + game_title, font(62, "Bold"), fill=INK)
    pill(d, (70, 1130, W - 70, 1310), (255, 107, 87), r=70, w=9)
    centred(d, 1155, "PLAY FREE NOW", font(108), fill=(255, 255, 255), stroke=6, sf=INK)
    f = font(56, "ExtraBold"); centred(d, 1350, SITE, f, fill=INK)
    centred(d, 1440, "Link in the description", font(46, "SemiBold", "Nunito"), fill=(85, 96, 138))
    centred(d, 1510, "A new game + a new 3D-printable toy every day", font(44, "Bold", "Nunito"), fill=INK)
    im.save(path)

def main():
    meta = json.load(open(sys.argv[1])); frames, out = sys.argv[2], sys.argv[3]; os.makedirs(out, exist_ok=True)
    tmp = os.path.join(out, "tmp"); os.makedirs(tmp, exist_ok=True)
    n = len(glob.glob(os.path.join(frames, "*.jpg"))); play = n / FPS; END = 4.0; total = play + END
    hook_png(meta["hook"], f"{tmp}/hook.png"); tag_png(f"{tmp}/tag.png")
    icons = sorted(glob.glob(os.path.join(meta.get("icons", "/home/claude/site/products"), "*", "icon.png")))
    lib = json.load(open(meta.get("toys", "/home/claude/site/toys.json")))["toys"]           # featured / newest toys first
    order = [os.path.join(os.path.dirname(icons[0]), "..", t["slug"], "icon.png") for t in lib] if icons else []
    endcard_png(meta["title"], [p for p in order if os.path.exists(p)], f"{tmp}/end.png")
    # captions land on the recorder's marks ("found", ...): the n-th mark gets the n-th line of that kind
    marks = json.load(open(os.path.join(frames, "marks.json"))) if os.path.exists(os.path.join(frames, "marks.json")) else []
    lines = meta.get("captions", {}); caps = []; used = {}
    for fr, kind in marks:
        seq = lines.get(kind, []); k = used.get(kind, 0); used[kind] = k + 1
        if seq: caps.append([fr, seq[k % len(seq)]])
    for i, (_, text) in enumerate(caps): caption_png(text, f"{tmp}/cap{i}.png")
    music = f"{tmp}/music.wav"; subprocess.run(["python3", os.path.join(HERE, "music.py"), str(total), music, str(meta.get("seed", 1))], check=True)
    inputs = ["-framerate", str(FPS), "-i", os.path.join(frames, "%05d.jpg"), "-loop", "1", "-t", str(END), "-i", f"{tmp}/end.png",
              "-i", f"{tmp}/hook.png", "-i", f"{tmp}/tag.png"]
    for i in range(len(caps)): inputs += ["-i", f"{tmp}/cap{i}.png"]
    inputs += ["-i", music]
    fc = [f"[0:v]scale={W}:{H}:flags=lanczos,setsar=1,fps={FPS}[g0]",
          f"[g0][2:v]overlay=0:0:enable='lte(t,2.6)'[g1]", "[g1][3:v]overlay=0:0[g2]"]
    last = "g2"
    for i, (fr, _) in enumerate(caps):
        t0 = fr / FPS; fc.append(f"[{last}][{4 + i}:v]overlay=0:0:enable='between(t,{t0:.2f},{t0 + 1.1:.2f})'[c{i}]"); last = f"c{i}"
    fc.append(f"[1:v]scale={W}:{H},setsar=1,fps={FPS},zoompan=z='min(1.025,1+0.0002*on)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}[end]")
    fc.append(f"[{last}][end]concat=n=2:v=1:a=0,format=yuv420p[v]")
    a_idx = 4 + len(caps)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", f"{a_idx}:a",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
           os.path.join(out, f"{meta['id']}_short.mp4")]
    subprocess.run(cmd, check=True)
    url = f"https://{SITE}/games/{meta['id']}/"
    desc = meta["yt_desc"].replace("{url}", url).replace("{site}", "https://" + SITE)
    open(os.path.join(out, f"{meta['id']}_youtube.txt"), "w").write(f"TITLE:\n{meta['yt_title']}\n\nDESCRIPTION:\n{desc}\n")
    print("short", os.path.join(out, f"{meta['id']}_short.mp4"), round(total, 1), "s")
if __name__ == "__main__": main()
