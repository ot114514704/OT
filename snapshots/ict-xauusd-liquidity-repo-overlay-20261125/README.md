[下载完整 ZIP](ICT-XAUUSD-Liquidity-Repo-Overlay-20261125.zip) · [SHA-256](SHA256.txt)

# XAUUSD 流动性预选与仓库补漏

以原本地 M5 IRL／ERL、四根提前候选和现有扫荡判词为基础。整合方案用于对齐 H1 截点的 ERL 预选回放。保留本地第一名。从仓库原排序前两个不同价位中取第一个可补位的价位，要求它在现价同侧并位于已有外沿内侧，或补足本地前二没有覆盖的一侧。候选比本地第二名更近才进入整合前二。另有保留本地前二并加一个仓库备选的对照。IRL 沿用本地预选。

| 样本 | 窗口 | 仓库前二 | 本地前二 | 整合前二 | 增加／丢失 |
|---|---|---:|---:|---:|---:|
| 10/1–11/20 H1 | 5 分钟 | 5/148 | 8/148 | 10/148 | +2／−0 |
| 10/1–11/20 H1 | 15 分钟 | 8/148 | 14/148 | 17/148 | +3／−0 |
| 10/1–11/20 H1 | 60 分钟 | 29/148 | 32/148 | 44/148 | +12／−0 |
| 11/23 起 H1 | 5 分钟 | 0/58 | 4/58 | 4/58 | +0／−0 |
| 11/23 起 H1 | 15 分钟 | 3/57 | 8/57 | 10/57 | +2／−0 |
| 11/23 起 H1 | 60 分钟 | 9/57 | 14/57 | 16/57 | +2／−0 |

15 分钟新增分别来自时段高低点、等高等低和结构摆动点。回放使用两组已有的 TMGM 样本，属于回顾性验证。表中命中为榜单可用后逐笔 Bid 严格扫过至少一个候选外沿。仓库 H4 只有 13 个配对截点，继续保留在独立对照。整合前二保留为研究方案，稳定性须用后续新样本验证。归档没有发送交易指令。

- [对比页](output/visualizations/ict-liquidity-window-preselection.html)
- [逐窗回放与新增命中](output/research/ict_repo_vs_local_forecast_20261125/repo_overlay.json)
- [逻辑实现](ict_ai/liquidity_repo_overlay.py)
- [此前本地版本、课程索引和 MT5 交接](LOCAL_BASELINE.md)
- [逐文件 SHA-256](MANIFEST.json)

在解压根目录用 Python 3.11+ 复跑离线逐笔回放。它会重新验证 Bid 数据与每个候选的扫荡时间并写出同名结果。

```powershell
python -m pip install numpy tzdata
python -B -m scripts.audit_ict_liquidity_repo_overlay
```

仓库模型来源为 `alexander094683-projects/forex-ai-source` 的 `7a5e44156397a45d102d54db86f7ec140b1b123a`。原 Git 源可在有权限的 checkout 上由 `scripts.audit_ict_repo_vs_local_forecast --upstream-git` 提取。随包提供已冻结候选、重训模型及其验证输出，补漏复跑从冻结候选和逐笔报价开始。
