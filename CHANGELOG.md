# 变更记录

## v1.0.0（2026-09-02）

首个正式发布版：

- 文章下载：人民时评 / 今日谈 / 求是社论评论 / 半月谈评论 / NYT Opinion，PDF + Word 导出到桌面并按三大类归档；
- 事件中心：人民网时政/国际、纽约时报 World 自动同步 + 手动添加事件；
- 评论与讨论：事件详情写评论、标记“想和 Codex 讨论”、讨论记录回写并展示；
- 独立桌面窗口：pywebview 原生 macOS 窗口 + 一键下载；
- 打包安装：`.app` 安装到 /Applications，提供 DMG 安装镜像；
- 用户数据：迁移到 `~/Library/Application Support/ShishipinglunCenter/`，与程序本体分离。

### 开发里程碑

1. CLI 文章下载工具（人民网/求是/半月谈，PDF/Word）；
2. NYT Opinion 接入（RSS 摘要回退）；
3. 定时任务：每日 08:30 自动下载 + 事件同步；
4. 事件中心（本地网页、事件库、评论、讨论回写）；
5. 整理为代码库项目（main.py 统一入口）；
6. pywebview 桌面窗口 + 窗口内一键下载；
7. PyInstaller 打包为 .app，用户数据外置；
8. 文档、测试与发布流程（v1.0.0）。
