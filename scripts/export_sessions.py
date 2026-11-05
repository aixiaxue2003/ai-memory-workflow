# -*- coding: utf-8 -*-
"""把 DSH 会话文件（session*.jsonl.zstd）导出成 Obsidian 可读的 markdown。

用法:
  python export_sessions.py --stats
  python export_sessions.py --out "<你的库>/06-对话" [--include-subagents] [--no-tools]

判定：第一条用户消息 > 2000 字 → 视为子代理会话（prompt 长、没有真人对话），默认不导出。
"""
import argparse, json, os, re, sys, time

try:  # 可选依赖：只在真读会话文件时需要
    import zstandard as zstd
except ImportError:  # 让 --help / --stats 在没装的机器上也能跑
    zstd = None

HOME = os.path.expanduser("~")
ROOTS = [os.path.join(HOME, ".dsh", "sessions"),
         os.path.join(HOME, ".dsh", "dsh-session-archive")]
SUBAGENT_PROMPT_CHARS = 2000


def find_session_files():
    out = []
    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        for dp, dn, fn in os.walk(root):
            for f in fn:
                if f.startswith("session") and f.endswith(".jsonl.zstd"):
                    out.append(os.path.join(dp, f))
    return out


def load_events(path):
    if zstd is None:
        return None, "缺少 zstandard：pip install zstandard（只有本脚本需要）"
    try:
        with open(path, "rb") as f:
            raw = zstd.ZstdDecompressor().stream_reader(f).read()
    except Exception as e:
        return None, str(e)
    events = []
    for ln in raw.decode("utf-8", "replace").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            events.append(json.loads(ln))
        except Exception:
            continue
    return events, None


def text_of(content):
    if isinstance(content, str):
        return content
    parts = []
    for c in content or []:
        if isinstance(c, dict) and c.get("type") == "text":
            parts.append(c.get("text", ""))
    return "\n".join(p for p in parts if p)


def clean_user_text(s):
    """去掉注入到用户消息里的系统提醒 / 工作区规则 / 上下文快照。"""
    s = re.sub(r"<system-reminder>.*?</system-reminder>", "", s, flags=re.S)
    s = re.sub(r"<available_skills>.*?</available_skills>", "", s, flags=re.S)
    s = re.sub(r"Instructions from: [^\n]*\n(?:.*?)(?=\n\n[A-Z][^\n]{0,40}\n|\Z)", "", s, flags=re.S)
    s = re.sub(r"Time sampled while preparing turn[^\n]*\n?", "", s)
    s = re.sub(r"Elapsed since [^\n]*\n?", "", s)
    s = re.sub(r"Current runtime context[^\n]*\n?", "", s)
    drop = ("Current working directory:", "Current DSH file policy:", "Approval prompts are disabled",
            "Current DeepSeek Harness implementation checkout:", "Current DeepSeek Harness Web GUI URL:",
            "Browser time zone for this request:", "Time sampled", "Elapsed since",
            "The following workspace instructions", "Instructions from:")
    kept = [ln for ln in s.splitlines() if not ln.strip().startswith(drop)]
    s = "\n".join(kept).strip()
    s = re.sub(r"<[^>]{1,20}>", "", s) if s.strip().startswith("<") and len(s) < 60 else s
    return s.strip()


def parse(events):
    meta = {"id": "", "cwd": "", "created": None, "title": "", "first_user": "", "turns": 0}
    msgs = []
    for ev in events:
        t = ev.get("type")
        d = ev.get("data") or {}
        if t == "session":
            s = ev  # session 事件字段在顶层，没有 data 包裹
            meta["id"] = s.get("id", "")
            meta["cwd"] = s.get("cwd", "")
            meta["created"] = s.get("createdAt")
            meta["origin"] = s.get("origin") or "user"
            meta["depth"] = s.get("delegationDepth", 0) or 0
            meta["parent"] = s.get("parentSession") or ""
        elif t == "session/title":
            meta["title"] = d.get("title") or meta["title"]
        elif t == "user/message":
            txt = clean_user_text(text_of(d.get("content")))
            if not txt:
                continue
            if not meta["first_user"]:
                meta["first_user"] = txt
            meta["turns"] += 1
            msgs.append(("user", ev.get("time"), txt, None))
        elif t == "assistant/message":
            txt = text_of((d.get("message") or {}).get("content")).strip()
            if txt:
                msgs.append(("assistant", ev.get("time"), txt, None))
        elif t == "tool/call" and d.get("name"):
            brief = re.sub(r"\s+", " ", (d.get("arguments") or ""))[:160]
            msgs.append(("tool", ev.get("time"), d.get("name"), brief))
    return meta, msgs


def fmt_time(ms):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ms / 1000)) if ms else ""


def slug(s, n=40):
    s = re.sub(r"[\\/:*?\"<>|\r\n\t]+", " ", s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s[:n] or "未命名"


def render(meta, msgs, include_tools=True):
    title = slug(meta.get("title")) or "未命名会话"
    day = fmt_time(meta.get("created") or (msgs[0][1] if msgs else None))[:10] or "1970-01-01"
    lines = ["---", f"date: {day}", f"created: {fmt_time(meta.get('created'))}",
             f"workspace: \"{meta.get('cwd','')}\"", f"session: {meta.get('id','')}",
             f"turns: {meta['turns']}", "tags: [对话]", "---", f"# {title}", ""]
    if meta.get("cwd"):
        lines.append(f"> `{meta['cwd']}` ｜ {fmt_time(meta.get('created'))} ｜ {meta['turns']} 轮")
        lines.append("")
    buf = []

    def flush():
        if not buf:
            return
        lines.append(f"> [!example]- 工具调用（{len(buf)}）")
        for nm, br in buf:
            lines.append(f"> - `{nm}` {br}")
        lines.append("")
        buf.clear()

    for kind, t, txt, extra in msgs:
        if kind == "tool":
            if include_tools:
                buf.append((txt, extra or ""))
            continue
        flush()
        stamp = fmt_time(t)[11:] if t else ""
        lines.append(f"**{'我' if kind == 'user' else 'AI'}** {stamp}")
        lines.append("")
        lines.append(txt)
        lines.append("")
    flush()
    return "\n".join(lines).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--include-subagents", action="store_true")
    ap.add_argument("--no-tools", dest="include_tools", action="store_false", default=True)
    args = ap.parse_args()

    files = find_session_files()
    rows = []
    for p in files:
        ev, err = load_events(p)
        if ev is None:
            continue
        meta, msgs = parse(ev)
        if not msgs:
            continue
        meta["subagent"] = meta.get("origin") == "subagent" or (meta.get("depth") or 0) > 0
        meta["chars"] = sum(len(m[2]) for m in msgs if m[0] != "tool")
        rows.append((p, meta, msgs))

    human = [r for r in rows if not r[1]["subagent"]]
    subs = [r for r in rows if r[1]["subagent"]]
    print(f"会话文件 {len(files)}｜真人会话 {len(human)}｜子代理会话 {len(subs)}")
    print(f"真人会话正文 {sum(r[1]['chars'] for r in human)/1e6:.2f}M 字符")

    if args.stats:
        for p, meta, msgs in sorted(human, key=lambda r: -r[1]["chars"])[:12]:
            print(f"  {meta['chars']:>7} 字符 {fmt_time(meta.get('created'))} {slug(meta.get('title'),30)}")
        return

    if not args.out:
        print("需要 --out")
        return
    chosen = rows if args.include_subagents else human
    written = 0
    index = []
    for p, meta, msgs in chosen:
        day = fmt_time(meta.get("created") or msgs[0][1])[:10]
        month = day[:7]
        folder = os.path.join(args.out, month)
        os.makedirs(folder, exist_ok=True)
        short = meta.get("id", "").replace("session-", "")[:8]
        name = slug(f"{day} {meta.get('title')} {short}", 70) + ".md"
        path = os.path.join(folder, name)
        if os.path.exists(path) and day != time.strftime("%Y-%m-%d"):
            pass  # 历史会话已导出过，不重复写
        else:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(render(meta, msgs, args.include_tools))
            written += 1
        index.append((day, meta.get("title") or "未命名", meta.get("cwd", ""), meta["turns"], f"{month}/{name[:-3]}", meta["subagent"]))

    index.sort(key=lambda r: r[0], reverse=True)
    by_month = {}
    for row in index:
        by_month.setdefault(row[0][:7], []).append(row)
    il = ["---", "tags: [MOC, 对话]", "---", "# 对话总览", "",
          f"共 {len(index)} 个会话，最近的在前。搜索用 `Ctrl+Shift+F`，或直接在当前库搜索关键词。", ""]
    for month in sorted(by_month, reverse=True):
        il.append(f"## {month}")
        il.append("")
        il.append("| 日期 | 会话 | 工作区 | 轮数 |")
        il.append("|---|---|---|---|")
        for day, title, cwd, turns, link, sub in by_month[month]:
            label = slug(title, 34) + ("（子代理）" if sub else "")
            il.append(f"| {day} | [[{link}\\|{label}]] | {os.path.basename(cwd.rstrip(chr(92))) or cwd} | {turns} |")
        il.append("")
    with open(os.path.join(args.out, "对话总览.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(il) + "\n")

    print(f"写入 {written} 篇（索引 {len(index)} 条）-> {args.out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
