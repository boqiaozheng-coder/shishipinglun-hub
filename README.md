# 时评与事件中心（shishipinglun-hub）

一个本地运行的“软件”，把三件事合在一起：

1. **文章下载**：抓取人民日报（人民时评 / 今日谈）、求是网社论评论、半月谈网评论、纽约时报 Opinion，导出 PDF / Word，按三大类别归档到桌面；
2. **事件中心**：收录国内外要闻（人民网时政/国际、纽约时报 World），可手动补充事件；
3. **评论与讨论**：给事件写评论，标记“想和 Codex 讨论”，在 Codex 中讨论后把回复写回事件中心，前端可查看完整记录。

网页前端负责“找工具、看事件、写评论”，命令行负责“下载文章”。

## 目录结构

```text
shishipinglun-hub/
├── main.py                     # 软件统一入口
├── requirements.txt
├── README.md
├── LICENSE                     # MIT 许可证
├── CHANGELOG.md                # 版本变更记录
├── shishipinglun/
│   ├── downloader.py           # 文章下载（原 download_articles.py）
│   ├── desktop.py              # 独立桌面窗口（pywebview）
│   └── events/
│       ├── db.py               # 本地 JSON 数据库
│       ├── server.py           # 事件中心网页服务
│       ├── sync_events.py      # 国内外事件同步
│       ├── record_discussion.py# 讨论回复回写
│       ├── static/             # 前端页面
│       └── data/database.json  # 初始数据（首次运行迁往用户目录）
├── scripts/
│   ├── build.sh                # 一键构建 .app
│   ├── release.sh              # 一键生成 DMG
│   ├── 打开软件.command
│   ├── 启动事件中心.command
│   └── 下载文章.command
├── packaging/                  # .app 打包入口与图标
├── tests/smoke_test.py         # 冒烟测试
├── .vscode/                    # VS Code 调试配置
└── docs/                       # 使用手册 / 开发过程记录 / 架构说明
```

## 安装依赖

```bash
cd /Users/zhengboqiao/Documents/GitHub/shishipinglun-hub
python3 -m pip install -r requirements.txt
```

## 使用

### 安装版 macOS 应用

已打包好的独立应用位于：

```text
/Applications/时评与事件中心.app
```

直接双击即可运行（无需安装 Python）；首次启动会把仓库里的初始事件复制到
`~/Library/Application Support/ShishipinglunCenter/database.json`，此后所有
事件、评论与讨论都保存在这里。

需要重新打包时（在项目根目录执行）：

```bash
python3 -m pip install pyinstaller
python3 -m PyInstaller --noconfirm --clean --windowed \
  --name ShishipinglunCenter --icon packaging/icon.icns \
  --add-data 'shishipinglun:shishipinglun' packaging/launcher.py
mv dist/ShishipinglunCenter.app 'dist/时评与事件中心.app'
```

### 统一入口 main.py

```bash
python3 main.py                 # 查看帮助
python3 main.py doctor          # 检查依赖
python3 main.py desktop         # 以独立桌面窗口打开软件
python3 main.py download        # 下载文章到 ~/Desktop/时评文章下载
python3 main.py events          # 启动事件中心网页（http://127.0.0.1:8765）
python3 main.py sync-events     # 同步国内外最新事件
```

### 独立桌面窗口（推荐）

```bash
python3 main.py desktop
```

也可以双击 `scripts/打开软件.command`。会打开一个原生 macOS 窗口（pywebview），
不用再开浏览器标签；窗口里包含事件中心与“文章下载器”入口，“文章下载器”页可直接
设置篇数并一键下载（PDF + Word 到桌面），关闭窗口即自动停止本地服务。

### 文章下载（原工具用法不变）

```bash
python3 -m shishipinglun.downloader --format pdf --count 10
python3 -m shishipinglun.downloader --format docx --days 7
python3 -m shishipinglun.downloader --sources rmsp,jrt,qs,byt
python3 -m shishipinglun.downloader --out ~/Desktop/测试输出
```

栏目：`rmsp` 人民时评、`jrt` 今日谈、`qs` 求是社论评论、`byt` 半月谈评论、`nyt` 纽约时报 Opinion。

### 事件中心网页

```bash
python3 main.py events
```

浏览器打开 http://127.0.0.1:8765。也可以双击 `scripts/启动事件中心.command`。

网页功能：

- 事件列表：国内/国际筛选、搜索、查看原文；
- 手动添加事件；
- 事件详情里写评论；
- 每条评论可标记“想和 Codex 讨论”；
- “我的评论”汇总所有评论与讨论状态；
- “文章下载器”页放常用命令，方便找工具。

### 事件同步

网页上点“同步最新事件”，或执行：

```bash
python3 main.py sync-events
python3 main.py sync-events --limit 15
```

数据保存在 `~/Library/Application Support/ShishipinglunCenter/database.json`
（开发模式下仓库内 `shishipinglun/events/data/database.json` 会在首次运行时自动迁移）。

### 评论 → Codex 讨论 → 回写

1. 在事件详情里写下你的看法并发表；
2. 点评论下方的“想和 Codex 讨论”；
3. 回到 Codex 对话框说：“讨论事件 X 里我写的评论”；
4. Codex 给出看法后，把回复写回：

```bash
python3 main.py discuss --event <事件ID> --comment <评论ID> --text "讨论内容"
```

刷新事件中心页面即可看到讨论记录。

## 构建与上架

### 本机正式版（已上架）

```text
/Applications/时评与事件中心.app      ← 已安装
release/时评与事件中心-1.0.0.dmg      ← 可分发安装镜像
```

重新构建并生成 DMG：

```bash
bash scripts/build.sh       # 产出 dist/时评与事件中心.app
bash scripts/release.sh     # 产出 release/时评与事件中心-1.0.0.dmg
```

安装镜像内的“安装说明.txt”会引导把 .app 拖入“应用程序”。

### 上架 Mac App Store（需要额外条件）

当前版本为本地安装分发（DMG + /Applications）。若要在 App Store 上架，需要：

1. 苹果开发者账号（$99/年）；
2. 应用签名（Developer ID / App Store 证书）与公证（notarization）；
3. 沙盒权限与隐私描述（网络、用户数据目录说明）。

拿到开发者证书后，我可以在仓库里补充 entitlements 与公证脚本，再走 App Store Connect 提审。

## 测试

```bash
python3 -m tests.smoke_test
```

## 数据与隐私

- 所有数据只保存在本机（`database.json`、桌面文章文件夹）；
- 抓取频率默认较低（每篇文章间隔 0.8 秒）；
- 仅供个人学习、离线阅读使用；NYT 正文受订阅/反爬限制时，工具会自动保存“RSS 摘要 + 原文链接”，并在文件中标注。

## 定时任务

在 Codex 应用中已注册“每日时评文章自动下载与事件同步”，每天 8:30 自动执行文章下载与事件同步；频率可在 Codex 中暂停或修改。
