# CHANGELOG

## 1.0.1 — 2026-11-05

- 去掉包内残留的本机绝对路径：体检报告落款、weekly_collect 文档示例、样例报告，改为可移植写法
- export_sessions.py 的 zstandard 改为惰性导入：没装依赖时 --help / --stats 仍可用，真读会话才提示 pip install
- 发布版（GitHub 用）

## 1.0.0 — 2026-11-05

- 首版：存（会话导出/原料收集）、用（三层注入）、学（六节蒸馏+冲突）、改（半衰期+体检）
- scripts：export_sessions.py / weekly_collect.py / knowledge_audit.py，全部路径可配（--vault / OBSIDIAN_VAULT）
- references：workflow.md 完整口径 + 三个可复制模板
