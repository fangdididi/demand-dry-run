# demand-dry-run（需求彩排）

[English](README.md) | **简体中文**

> 在动手做之前，先弄清楚陌生人是否愿意为你的想法做出承诺；而且判断标准一旦定下，事后改不了。

`demand-dry-run` 是一个 Agent Skill，适用于 Claude Code、Codex、Cursor 以及其他能读取 `SKILL.md` 的智能体。它把“先挂个等待名单看看”变成一次小而诚实的实验：冻结的下注卡、只提一个请求且写明真实价格与真实状态的报价页、有计划的流量、基于区间的结论，以及干净的收尾。

## 为什么需要它

做之前的验证，通常根本不可能失败：朋友出于好意报名；页面藏起价格，点击只代表好奇；成功标准在数据出来后才定；精美的页面抢走了本该属于产品的功劳；想法放弃之后，留了邮箱或交了定金的人再也收不到任何消息。

这个 skill 逐一解决：

| 问题 | 做法 |
|---|---|
| 事后挪动标准 | 通过线和放弃线写在下注卡上，在第一个访客之前用哈希锁定 |
| 把好奇当需求 | 页面必须写明真实价格；选定一个承诺级别（邮箱、表单、定金、预订）并只统计它 |
| 页面误导 | 检查会拦下：缺价格或状态、编造稀缺或人数、无来源的评价、倒计时、收钱却不提退款 |
| 朋友拉高转化 | 熟人渠道照常记录，但不计入结论 |
| “40 个里有 3 个！” | 结论用 95% Wilson 区间，并要求每个格子达到最少访客数 |
| 转化不错但获客太贵 | 单个承诺成本上限会把过贵的 GO 降为 RESHAPE |
| 报名者被晾着 | 收尾步骤提供退款、通知、删除数据的模板 |

## 功能

- **下注卡**（`bet.json`）：人群、痛点、产品、价格、状态句、承诺级别、通过线与放弃线、样本下限、预算、截止日期、渠道、版本。
- **样本量估算**：`dryrun.py size` 告诉你每个格子需要多少访客才能区分两条线。
- **冻结与锁定**：`dryrun.py freeze` 校验下注卡并写入哈希；冻结后再改，结论作废。
- **页面规格**：首屏五个位置，以及“各版本精致度一致”的规则。
- **诚实检查**：`dryrun.py lint` 对照下注卡检查做好的 HTML，中英文文案都能识别。
- **结论**：`dryrun.py verdict` 对每个“版本 × 渠道”格子和每个版本给出 GO、STOP、KEEP、RESHAPE 或 UNLOCKED，并提示渠道结论相反、超预算等情况。
- **收尾模板**：中英双语，覆盖“做”“停”“调整”三种结果。

## 安装

把整个文件夹复制到智能体的 skills 目录。

| 智能体 | 位置 |
|---|---|
| Claude Code | `~/.claude/skills/demand-dry-run/`（或项目内 `.claude/skills/`） |
| Codex | `~/.codex/skills/demand-dry-run/`（或项目内 `.agents/skills/`） |
| Cursor | 项目内 `.cursor/skills/demand-dry-run/` |
| 其他智能体 | 放在它读取 skill 的位置，或直接让它读 `SKILL.md` |

```bash
git clone https://github.com/fangdididi/demand-dry-run.git ~/.claude/skills/demand-dry-run
```

辅助脚本只需要 Python 3.8+ 和标准库。中文说明在 `SKILL.zh-CN.md`，两个文件都可以作为 skill 入口。

## 用法

可以这样对智能体说：

- “开发之前，帮我给一个每月 29 美元、给记账员用的催票据工具设计一次需求彩排。”
- “我的等待名单有 400 人，老实告诉我这到底说明了什么。”
- “这门课定 49 还是 99？帮我规划一次彩排。”

也可以直接用脚本：

```bash
python3 scripts/dryrun.py init bet.json                       # 空白下注卡
python3 scripts/dryrun.py size --pass-line 0.04 --kill-line 0.015 --cpc 0.8
python3 scripts/dryrun.py freeze bet.json                     # 校验并锁定
python3 scripts/dryrun.py lint bet.json page.html             # 诚实检查
python3 scripts/dryrun.py verdict bet.json log.csv            # GO / STOP / KEEP / RESHAPE
python3 scripts/dryrun.py verdict bet.json log.csv --json     # 机器可读输出
```

退出码：`0` 正常（任何结论），`1` 检查未通过（lint 有 FAIL、下注卡有误或结论为 UNLOCKED），`2` 输入错误。

## 示例

`examples/` 中是一次完整的彩排：记账员工具，两个版本、两个付费渠道，外加一个朋友渠道：

```
  A      bookkeeper_forum    6/270    [1.0% .. 4.8%]  KEEP
  A      linkedin_ads       11/490    [1.3% .. 4.0%]  KEEP
  B      bookkeeper_forum   15/285    [3.2% .. 8.5%]  KEEP
  B      linkedin_ads       30/498    [4.3% .. 8.5%]  GO
VARIANT A: 17/760 [1.4% .. 3.6%] cost/commit 22.94 -> RESHAPE
VARIANT B: 45/783 [4.3% .. 7.6%] cost/commit 8.73 -> GO
excluded visitors (warm or off-card): 60
VERDICT GO (best: B)
```

60 位转化率高达 15% 的朋友，没有影响结论。

## 文件结构

```
demand-dry-run/
├── SKILL.md              # skill 说明（英文）
├── SKILL.zh-CN.md        # skill 说明（中文）
├── README.md
├── README.zh-CN.md
├── LICENSE
├── scripts/
│   └── dryrun.py         # init、size、freeze、lint、verdict
├── templates/
│   ├── page-spec.md      # 首屏五位置规格与目检清单
│   └── close-out.md      # 做 / 停 / 调整 三种消息与结果记录
├── examples/
│   ├── bet.json          # 填好的下注卡
│   ├── bet.lock          # 对应哈希
│   ├── page.html         # 通过检查的报价页
│   ├── log.csv           # 流量记录
│   └── verdict.txt       # 结论输出
└── tests/
    └── test_dryrun.py    # 71 个单元测试
```

运行测试：`python3 -m unittest discover -s tests`。

## 许可

MIT
