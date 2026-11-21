# MT5 黄金概况面板备份

2026-11-22 保存的 1.31 工作稿。Indicators/ICT_Trader 来自当前终端的安装目录。workspace-differences 单独保留工作区与安装件不同的文件。恢复屏幕上使用的指标请选 Indicators。

1. 在 Windows x64 解压整个 ZIP。在 MT5 的「文件 → 打开数据文件夹」中，将 Indicators/ICT_Trader 复制到 MQL5/Indicators 下。若目标已有同名文件，请先保存原件。
2. 把 CommonFiles/ICT_Trader 复制到 MetaTrader 公共文件目录 MetaQuotes/Terminal/Common/Files 下。H1Profiles.tsv 保留备份时的图表标注。终端需具备相应 XAUUSD 历史 K 线才能在对应时间显示。
3. 在当前 TMGM 终端打开 XAUUSD，选 M15，在导航器刷新后加载 ICT_H1_Profiles。选择需要的图层；纽约开/4H收控制纽约零点开盘线和美东四小时收盘线。
4. 需要持续更新时，先登录目标 TMGM 终端，再从解压目录运行 START_FEED.cmd。若电脑安装多个 MT5，请先确认 Python 连接的是目标终端。运行时已随包提供。工作区行情桥含最新 FVG 识别逻辑，启动后会用新读取的行情更新标注。SQLite 文件保留已有 DOL 记录。

MANIFEST.json 列出包内文件的 SHA-256。快照按原工作稿保存，磁盘上的行情桥源码与冻结的图表标注分别保留。周五尾盘和换季周末的时间按现有行情及项目时钟设置解释。

备份文件：ICT-MT5-XAUUSD-1.31-20261122.zip

SHA-256：77bb96018693919cd74931c27d4225527a7c0914bcce617665de42e23c189ffb
