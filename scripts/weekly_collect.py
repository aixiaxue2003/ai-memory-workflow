# -*- coding: utf-8 -*-
"""每周蒸馏：把「最近 7 天」的对话与收藏原料收集成一份 feed.md，供 Codex / agent 读取。

用法:
  python weekly_collect.py            # 最近 7 天（含今天）
  python weekly_collect.py --days 14  # 自定义天数

产出（默认写到 $AMW_WORK，可用环境变量改）:
  $AMW_WORK/weekly/<YYYY-Www>/feed.md
  $AMW_WORK/weekly/<YYYY-Www>/meta.json
"""
import argparse, datetime as dt, glob, json, os, re, sys

VAULT = os.environ.get("OBSIDIAN_VAULT", os.path.join(os.path.expanduser("~"), "ObsidianVault"))
OUT_ROOT = os.environ.get("AMW_WORK", os.path.join(os.path.expanduser("~"), ".ai-memory-workflow", "weekly"))
CONV = os.path.join(VAULT, "06-对话")
FAV = os.path.join(VAULT, "03-资源", "抖音收藏")
CAP_MSG = 500
CAP_SESSION = 2500


def parse_note(path):
    txt = open(path, encoding="utf-8").read()
    meta = {}
    m = re.match(r"---\n(.*?)\n---\n", txt, re.S)
    if m:
        for ln in m.group(1).splitlines():
            if ":" in ln:
                k, v = ln.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
        txt = txt[m.end():]
    title = ""
    for ln in txt.splitlines():
        if ln.startswith("# "):
            title = ln[2:].strip(); break
    return meta, title, txt


def user_quotes(txt):
    out = []
    for b in re.split(r"\n\*\*", txt):
        if b.startswith("我**"):
            body = b.split("\n", 1)[1] if "\n" in b else ""
            body = re.split(r"\n\*\*(?:AI|我)\*\*", body)[0]
            body = body.split("\n> [!example]-")[0].strip()
            body = re.sub(r"\n{2,}", "\n", body)
            if body:
                out.append(body[:CAP_MSG])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--vault", default=None, help="Obsidian 库根目录，默认取 env OBSIDIAN_VAULT")
    a = ap.parse_args()
    global VAULT, CONV, FAV
    if a.vault:
        VAULT = a.vault
    CONV = os.path.join(VAULT, "06-对话")
    FAV = os.path.join(VAULT, "03-资源", "抖音收藏")
    today = dt.date.today()
    start = today - dt.timedelta(days=a.days - 1)
    iso = today.isocalendar()
    week = f"{iso[0]}-W{iso[1]:02d}"
    outdir = os.path.join(OUT_ROOT, week)
    os.makedirs(outdir, exist_ok=True)

    conv_rows = []
    for p in sorted(glob.glob(os.path.join(CONV, "*", "*.md"))):
        meta, title, txt = parse_note(p)
        day = meta.get("date", "")
        if not day or day < start.isoformat():
            continue
        quotes = user_quotes(txt)
        if not quotes:
            continue
        used, body = 0, []
        for q in quotes:
            if used > CAP_SESSION:
                body.append("（后续略）"); break
            body.append("- " + q.replace("\n", " "))
            used += len(q)
        ws = os.path.basename(meta.get("workspace", "").rstrip("\\")) or "—"
        conv_rows.append((day, title, ws, body))

    fav_rows = []
    for p in sorted(glob.glob(os.path.join(FAV, "*收藏明细.md"))):
        d = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(p))
        if not d or d.group(1) < start.isoformat():
            continue
        txt = open(p, encoding="utf-8").read()
        blocks = re.split(r"\n## ", txt)[1:]
        for b in blocks:
            head = b.split("\n", 1)[0].strip()
            body = re.sub(r"\s+", " ", b)[:400]
            fav_rows.append((d.group(1), head, body))

    L = [f"# 每周原料 · {week}（{start} ~ {today}）", "",
         f"- 对话：{len(conv_rows)} 个会话",
         f"- 收藏：{len(fav_rows)} 条新增",
         "", "---", "", "## 一、本周对话（只含我说的原话）", ""]
    for day, title, ws, body in conv_rows:
        L.append(f"### {day} {title} ｜{ws}")
        L += body
        L.append("")
    L += ["---", "", "## 二、本周新增收藏（标题 + 转写开头）", ""]
    if not fav_rows:
        L.append("（本周没有新增收藏）")
    for day, head, body in fav_rows:
        L.append(f"### {day} {head}")
        L.append(body)
        L.append("")

    feed = os.path.join(outdir, "feed.md")
    open(feed, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    json.dump({"week": week, "start": start.isoformat(), "end": today.isoformat(),
               "sessions": len(conv_rows), "favorites": len(fav_rows)},
              open(os.path.join(outdir, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{week}: 对话 {len(conv_rows)} 个会话 / 收藏 {len(fav_rows)} 条 -> {feed}")
    print(f"feed 大小 {os.path.getsize(feed)/1024:.1f} KB")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
