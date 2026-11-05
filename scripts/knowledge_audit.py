# -*- coding: utf-8 -*-
"""知识库体检：算知识债、孤儿笔记、出片数据、转化率，写成 02-领域/知识体检.md。

零 API 费，全靠读文件。每周五 21:00 自动跑一次。
用法: python knowledge_audit.py
"""
import argparse
import datetime as dt
import os
import re
import sys

VAULT = os.environ.get("OBSIDIAN_VAULT", os.path.join(os.path.expanduser("~"), "ObsidianVault"))
REPORT = None  # 运行时按 VAULT 计算


def md_files():
    for dp, dn, fn in os.walk(VAULT):
        if ".obsidian" in dp:
            continue
        for f in fn:
            if f.endswith(".md"):
                yield os.path.join(dp, f)


def main():
    global VAULT, REPORT
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=None)
    ap.add_argument("--report", default=None)
    a = ap.parse_args()
    if a.vault:
        VAULT = a.vault
    REPORT = a.report or os.path.join(VAULT, "02-领域", "知识体检.md")
    files = list(md_files())
    text = {}
    for p in files:
        try:
            text[p] = open(p, encoding="utf-8").read()
        except Exception:
            text[p] = ""

    # 1) 知识债：收件箱里待处理（除说明外）
    inbox = [p for p in files if os.path.basename(os.path.dirname(p)) == "00-收件箱"
             and "说明" not in os.path.basename(p)]

    # 2) 孤儿笔记：没有任何 [[入链]]
    names = {os.path.basename(p)[:-3].lower(): p for p in files}
    inbound = {k: 0 for k in names}
    for p, t in text.items():
        for m in re.findall(r"\[\[([^\]|#\\]+)", t):
            k = m.strip().split("/")[-1].lower()
            if k in inbound and names[k] != p:
                inbound[k] += 1
    orphans = [k for k, v in inbound.items() if v == 0 and not k.startswith("首页")]

    # 3) 出片记录
    out = os.path.join(VAULT, "01-项目", "出片记录.md")
    rows = []
    layout = []
    if os.path.exists(out):
        for ln in open(out, encoding="utf-8").read().splitlines():
            if ln.strip().startswith("|") and "---" not in ln and "日期" not in ln:
                cols = [c.strip() for c in ln.strip().strip("|").split("|")]
                if len(cols) >= 8 and cols[0] not in ("示例", ""):
                    rows.append(cols)
                    layout.append(len(cols))
    total = len(rows)
    last14 = [r for r in rows if r[0] >= (dt.date.today() - dt.timedelta(days=14)).isoformat()]
    judged = [r for r in rows if r[-1] in ("留", "改", "砍")]

    # 4) 转化率 & 候选数
    pool = os.path.join(VAULT, "03-资源", "蒸馏-选题.md")
    cand = len(re.findall(r"^- ", open(pool, encoding="utf-8").read(), re.M)) if os.path.exists(pool) else 0
    conv = (total / cand) if cand else 0

    # 5) 有无数据的片
    def col(r, new_i, old_i):
        return r[new_i] if len(r) >= 9 else r[old_i]
    nodata = [r for r in rows if not col(r, 4, 3) or not col(r, 5, 4)]

    today = dt.date.today().isoformat()
    L = ["---", f"date: {today}", "tags: [体检]", "---", f"# 知识体检 {today}", ""]
    L += ["## 5 个数", "", "| 指标 | 值 | 阈值 | 判定 |", "|---|---|---|---|"]
    def judge(ok, bad_msg=""):
        return "达标" if ok else f"✗ {bad_msg}"
    L.append(f"| 近 14 天出片 | {len(last14)} | ≥6（两周 3 条/周） | {judge(len(last14)>=6, '出片不够')} |")
    if total == 0:
        L.append("| 有结论的片 | 0/0 | 全部 | 待开始（还没有出片记录） |")
    else:
        L.append(f"| 有结论的片 | {len(judged)}/{total} | 全部 | {judge(len(judged)==total, '有片没结论')} |")
    L.append(f"| 缺数据的片 | {len(nodata)} | 0 | {judge(len(nodata)==0, '数据没回填')} |")
    L.append(f"| 知识债（收件箱待处理） | {len(inbox)} | ≤20 | {judge(len(inbox)<=20, '债太多，只许处理')} |")
    L.append(f"| 候选 → 出片 转化率 | {conv:.0%} | ≥60% | {judge(conv>=0.6, '采了没拍')} |")
    L += ["", "## 库存", "",
          f"- 笔记总数：**{len(files)}**",
          f"- 候选选题：**{cand}**",
          f"- 孤儿笔记（没被任何笔记链接、也没链接别人）：**{len(orphans)}**",
          "", "## 建议动作（机械规则，自己拍板）", ""]
    if inbox:
        L.append(f"- 收件箱 {len(inbox)} 条待判：每天 3 分钟判层，判不出的进候选")
    if nodata:
        L.append(f"- {len(nodata)} 条片没填数据：数据不回填，机制等于没跑")
    if conv and conv < 0.6:
        L.append(f"- 转化率 {conv:.0%}：本周少采纳，多拍")
    if orphans[:8]:
        L.append("- 孤儿笔记示例：" + "、".join(orphans[:8]))
    L += ["", "---", "由 `knowledge_audit.py`（ai-memory-workflow）生成，可按需重跑覆盖。"]

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    open(REPORT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(f"体检 -> {REPORT}")
    print(f"笔记 {len(files)}｜收件箱 {len(inbox)}｜出片 {total}｜有结论 {len(judged)}｜候选 {cand}｜孤儿 {len(orphans)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
