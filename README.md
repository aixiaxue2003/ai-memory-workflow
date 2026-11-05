# ai-memory-workflow

给 AI 装一套**可复用、会自我更新**的记忆：会话导出 → 分层入库 → 每周蒸馏 → 冲突裁决 → 半衰期淘汰。

不是"笔记模板"，是一套能跑的工作流：每个动作都有脚本、有产物，能挂在定时任务上。

## 国内下载（GitHub 直连很慢，走镜像）

本机实测：GitHub 首页 530KB 要 7.8 秒，Release 附件直连 25 秒都下不完。

- 仓库：https://github.com/aixiaxue2003/ai-memory-workflow
- 镜像下载 zip（实测 4.3 秒，20,731 字节）：

```bash
curl -L -o ai-memory-workflow-1.0.1.zip \
  "https://ghfast.top/https://github.com/aixiaxue2003/ai-memory-workflow/releases/download/v1.0.1/ai-memory-workflow-1.0.1.zip"
```

`ghfast.top`、`gh-proxy.com` 两个前缀都能用，把原地址整段接在后面即可。

## 目录

```
ai-memory-workflow/
  SKILL.md                    触发条件 / 步骤 / 验收 / 坑
  scripts/
    export_sessions.py        AI 会话（DSH 的 .jsonl.zstd）→ Obsidian markdown
    weekly_collect.py         最近 N 天原料 → feed.md（对话原话 + 新收藏）
    knowledge_audit.py        知识债 / 孤儿笔记 / 出片数据 → 体检报告
  references/
    workflow.md               存/用/学/改的完整口径与节奏表
    templates/                六节结论、冲突、周摘要的可复制模板
  examples/                   最小样例（可直接跑）
  VERSION / CHANGELOG.md / LICENSE
```

## 安装

解压到 `~/.dsh/skills/ai-memory-workflow/`（DSH），或任何 agent 的技能目录；目录名保持 `ai-memory-workflow`。

## 跑通（3 条命令）

```bash
export OBSIDIAN_VAULT="$HOME/ObsidianVault"     # 你的库

python scripts/export_sessions.py --out "$OBSIDIAN_VAULT/06-对话"
python scripts/weekly_collect.py --days 7
python scripts/knowledge_audit.py --vault "$OBSIDIAN_VAULT"
```

`export_sessions.py` 只认 DSH 的会话目录（`~/.dsh/sessions`）；不是 DSH 用户可以跳过这一步，只用手里的 md 当原料。

## 依赖

- Python 3.9+
- `zstandard`（仅 `export_sessions.py` 需要）：`pip install zstandard`
- 其余脚本零依赖、零联网、零 API 费用

## 设计取舍

- **结论必须带出处**：没有原话支撑，那条就空着，宁可少写
- **冲突不自动覆盖**：两边并排给你选，记忆不能被静默改写
- **带半衰期**：结构不过期 / 工具 6 个月 / 交付 30 天；30 天未引用标黄
- **脚本不做判断**：抓取、切分、计数、体检交脚本；判层与裁决交人

## 版本

见 `VERSION` 与 `CHANGELOG.md`。MIT License。
