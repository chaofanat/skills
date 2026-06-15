---
name: trend-verify
description: |
  趋势验证（Trend Verification）— 对连续涨停/趋势加速股进行系统性的趋势可持续性验证。
  核心原则：涨停=趋势起点。使用三层双假设框架（催化剂持续性、资金承接力、阻力清晰度），
  同时收集延续证据和中断证据，消除确认偏差。
  触发场景：(1) stock-analysis 报告判定为"趋势加速市 + 末期得分≥6"后需验证趋势；
  (2) 用户对连续涨停股要求验证趋势能否持续；
  (3) 用户说"验证趋势"、"趋势能走多远"、"这个板还能打吗"、"涨停还能继续吗"。
  输出验证评分和乘数，可回传至 stock-analysis 技术评分。
  依赖技能web-access，使用此技能时应同步加载web-access技能以规范信息采集流程。
---
# 趋势验证 — 三层双假设框架

## 核心原则

1. **涨停=趋势起点**：不预设趋势即将结束，系统检验趋势能否延续
2. **双假设并行**：每个检查项同时收集延续证据和中断证据，使偏差透明
3. **结构化优先**：按 P0→P1→P2 优先级搜索，避免漫无目的的自由探索
4. **催化剂为王**：如果上涨理由被公司否认，后续只评估下跌幅度
5. **gmapi 优先 + CDP 补充**：硬数据走 gmapi（数值精确、速度快），文本证据走 CDP（公告/新闻/函件）

---

## 触发条件

- stock-analysis 报告中出现"趋势加速市 + 末期得分≥6"
- 用户直接说"验证趋势 002354"、"002354 趋势能走多远"等
- 用户对连续涨停（2板及以上）股票提出验证需求

---

## 前置条件

- **gm SDK 环境**：项目根目录 `.venv/` 已安装 gm SDK 3.0.184+
- **GM_TOKEN 环境变量**：必须配置，供 `scripts/gmapi_fetcher.py` 使用
- 需要 web-access 技能进行文本类数据采集（CDP）
- 股票代码为6位数字的A股代码（如 002354、600141）

---

## 工作流

### Step 0'：gmapi 数据预采集（新增，自动）

**目的**：先用 gm SDK 批量拉硬数据（龙虎榜/资金流/概念板块/K线/业绩预告），减少后续 CDP 调用次数，并生成 `fallback_needed` 清单指导 CDP 阶段补哪些文本数据。

**执行方式**：

```bash
cd "D:/workspace/股票工作站"
.venv/Scripts/python.exe .claude/skills/trend-verify/scripts/gmapi_fetcher.py {交易所前缀.股票代码}
# 例如：SZSE.002354 或 SHSE.600141
# 可选参数：--start 2026-05-01 --end 2026-06-15
```

**单次调用覆盖的数据**（一次跑完，约 3~5 秒）：

| 数据项 | gmapi 接口 | 输出位置 |
|--------|-----------|---------|
| 板块与行业归属 | `stk_get_symbol_sector` + `stk_get_symbol_industry` | `sector_info` |
| 龙虎榜异动记录 | `stk_abnor_change_stocks`（逐日） | `abnor_changes` |
| 龙虎榜营业部明细 | `stk_abnor_change_detail` | `sales_depts`（含 `big_sellers`/`institution_seats`/`northbound_seats` 自动分类） |
| 个股资金流（五档） | `stk_get_money_flow` | `money_flow` |
| 板块共振判定（已自动算） | `sector_constituents` + `history_n` | `sector_resonance`（含 `up3_count`/`resonance_level`） |
| 业绩预告 | `stk_get_finance_forecast` | `finance_forecast`（含 `fcst_content`/`change_reason`） |
| 历史 K 线 + 涨停判定 | `history` + `get_history_symbol` | `history`（含 `is_limit_up` 精确判定） |

**输出位置**：
- JSON 数据包：`股票分析数据/{YYYY-MM-DD}/{symbol}_gmapi_package.json`
- Markdown 报告：`股票分析报告/{YYYY-MM-DD}/{symbol}_gmapi_report.md`

**JSON 数据包结构**详见 `templates/gmapi_data_package.md`。
**接口字段映射与判定阈值**详见 `references/gmapi_to_trend_verify_mapping.md`。

**fallback_needed 清单**：JSON 包末尾包含一个数组，列出 gmapi 无法覆盖、必须 CDP 补充的数据项。Step 0~5 应优先按此清单走 CDP。

**异常处理**：gmapi 单个接口失败时不中断主流程，自动记录到 `fallback_needed`（含 `error` 字段）。后续 CDP 阶段需补这些失败项。

---

### Step 0：概念发现（自动）

**目的**：自动识别驱动股价上涨的概念/催化剂，无需用户提供。

**执行步骤**：

1. **读取 Step 0' 的 JSON 数据包**，提取以下已知信息：
   - `abnor_changes[].change_type_name` → 龙虎榜上榜原因（如"日涨幅偏离值达到7%"）
   - `sector_info.concepts` → 个股所属的概念板块清单（如"人工智能"、"元宇宙"）
   - `history.limit_up_count` → 近期涨停板数

2. **CDP 补充新闻标题中的概念词**（gmapi 不提供新闻）：
   - URL: `https://so.eastmoney.com/news/s?keyword={代码}+{股票名称}`
   - 关注标题中出现的概念词（如"物理AI"、"世界杯"、"低空经济"等）
   - 这一步对应 `fallback_needed` 中的"近期新闻标题中的概念词"项

3. **综合 gmapi 概念清单 + CDP 新闻概念词**，形成完整**驱动概念列表**

4. 记录每个概念的信息来源（gmapi 板块 / 新闻标题+URL / 龙虎榜上榜原因）

**输出**：

- 驱动概念列表（如：物理AI、世界杯）
- 概念来源（gmapi 板块 / 新闻标题 + URL）
- 涨停原因分类（概念炒作 / 业绩驱动 / 事件驱动）

---

### Step 1：催化剂持续性（Layer 1，权重 40%）

**详细检查清单**见 `templates/verification_checklist.md` 的 Layer 1 部分。

**核心逻辑**：

| 检查项               | 优先级     | 数据源                                    | 说明                                           |
| -------------------- | ---------- | ----------------------------------------- | ---------------------------------------------- |
| 公司确认/否认        | P0         | gmapi 业绩预告（`finance_forecast`）+ CDP 异动公告 | 公司是否在异动公告中否认驱动概念               |
| 板块共振 vs 独狼     | P1         | gmapi `sector_resonance`（已自动算）       | 同概念板块是否有3只以上个股同步上涨            |
| 概念板块趋势逻辑验证 | P1（条件） | CDP 行业专业平台 + 东财辅助              | 仅当板块共振时：按行业映射表选择平台验证逻辑链 |
| 事件驱动 vs 主题驱动 | P1         | CDP 新闻分析 + gmapi 业绩预告辅助        | 催化剂是一次性消息还是持续性产业趋势           |

**提前停止规则**：若 P0 判定为"公司否认核心概念"，直接标记"催化剂坍塌"。

- Layer 1 评分直接为最低分（0-10分）
- Layer 2 和 Layer 3 转为评估下跌幅度，不再评估延续概率
- 跳到 Step 4 评分汇总

**条件子步骤**：若 1.2 判定为"板块共振"（H_延续得分 ≥ +6），自动触发 **1.2b 概念板块趋势逻辑验证**。该步骤独立搜索板块层面的驱动叙事，用双假设框架验证逻辑链是否成立，结果调整 1.2 的原始得分（±10 范围不变）。详见 `templates/verification_checklist.md` 的 1.2b 部分。

---

### Step 2：资金承接力（Layer 2，权重 35%）

**详细检查清单**见 `templates/verification_checklist.md` 的 Layer 2 部分。

| 检查项         | 优先级 | 数据源                                | 说明                           |
| -------------- | ------ | ------------------------------------- | ------------------------------ |
| 龙虎榜买卖结构 | P1     | gmapi `sales_depts`（含机构/北向分类） | 买方是深股通/机构还是游资/散户 |
| 大额卖出方     | P1     | gmapi `sales_depts.big_sellers`       | 是否有单营业部净卖出>5000万（已自动算阈值） |
| 板块资金流     | P2     | gmapi 成分股 money_flow 求和 / CDP 东财板块资金 | 板块整体资金流入还是流出 |

**重要**：gmapi 的 `stk_active_stock_top10_shszhk_info(types='NF')` 北向资金接口实测不可用，必须从 `sales_depts.northbound_seats` 反推北向席位净额。

---

### Step 3：阻力清晰度（Layer 3，权重 25%）

**详细检查清单**见 `templates/verification_checklist.md` 的 Layer 3 部分。

| 检查项       | 优先级 | 数据源                              | 说明                           |
| ------------ | ------ | ----------------------------------- | ------------------------------ |
| 历史相似案例 | P1     | gmapi `history.klines` + CDP 案例库 | N连板+概念否认后的历史走势基线 |
| 监管风险     | P2     | CDP 深交所/上交所官网               | 交易所问询函、停牌核查         |

---

### Step 4：评分汇总

**详细评分规则**见 `templates/scoring_rules.md`。

三层各自按 P0/P1/P2 权重计算子分，加总后映射为验证乘数：

| 验证得分 | 乘数  | 含义                             |
| -------- | ----- | -------------------------------- |
| 75-100   | ×1.0 | 趋势有支撑，技术评分不变         |
| 55-74    | ×0.9 | 信号混合，技术评分适度下调       |
| 35-54    | ×0.8 | 趋势偏弱，技术评分显著下调       |
| 0-34     | ×0.7 | 趋势大概率中断，技术评分大幅下调 |

乘数应用于 stock-analysis 第四步最终得分：`adjusted_score = technical_score × multiplier`

---

### Step 5：报告生成

**报告模板**见 `templates/verification_report.md`。

保存到用户工作目录的 `股票分析报告/{日期}/` 子目录：

- 文件名：`{代码}_{名称}_趋势验证_{时间戳}.md`

报告中应包含"数据来源声明"，标注每个判定来自 gmapi 数据包还是 CDP 采集。

---

## 双假设协议（核心行为约束）

在执行 Step 1-3 的每个检查项时，必须同时记录：

```
H_延续（趋势继续的证据）：[发现/未发现] + 具体内容 + [gmapi/CDP]
H_中断（趋势中断的证据）：[发现/未发现] + 具体内容 + [gmapi/CDP]
净判定：延续 / 中断 / 中性
```

**禁止行为**：

- 禁止只搜索负面信息（如只找"利空"、"否认"、"出逃"）
- 禁止忽略正面信号（如深股通大额买入、机构净买入）
- 禁止在收集完所有证据前下结论
- 禁止在单一平台搜索无果后直接判定"未发现"而不换平台
- 禁止忽略 `fallback_needed` 清单中的必查项（特别是 P0 的异动公告）

**搜索穷尽规则**（适用于 1.2b 和所有需要行业数据的检查项）：

- 在任一平台搜索无果时，必须记录"在{平台}搜索{关键词}，结果为{具体情况}"
- 必须至少搜索2个不同类型的平台后，才能判定"未发现"
  - 类型1：证券财经平台（东财、巨潮等）
  - 类型2：行业专业平台（卓创、生意社、SMM等，按 `references/data_sources.md` 中的行业与平台映射表选择）
- 报告中必须记录完整的搜索执行过程（搜索了哪些平台、用了什么关键词、得到什么结果）
- "未发现"必须基于真实的搜索行为，而非"懒得搜"或"搜错平台"
- **关键认知**：东财搜不到行业数据 ≠ 行业数据不存在。东财是证券平台，不是行业数据平台。

**采集优先级**（详见 `references/cdp_search_strategy.md`）：

```
1. gmapi 硬数据 → 2. 目标网站直连 → 3. WebSearch MCP 工具 → 4. CDP 搜索引擎降级
```

- **目标网站直连 > 搜索引擎**：除"历史相似案例"外，trend-verify 的数据都有明确目标站点（巨潮/东财/生意社/SMM等），第一步直连目标站点而非打开搜索引擎
- **搜索引擎降级顺序**：WebSearch（配额内）> Bing > 360/搜狗 > 百度（易触发反爬）> Google（需代理）
- **反爬触发应对**：百度图形验证码 → 换 Bing/360；Bing DOM 抓取为空 → fallback 到 `body.innerText` 整体提取；WebSearch 429 → CDP 直连替代
- **公告正文获取**：巨潮公告详情页是 PDF 不可提取 → 改用东财公告详情页（含完整文本）`https://data.eastmoney.com/notices/detail/{code}/{AN编号}.html`
- **禁止**：搜索引擎单一失败后判定"未发现" — 必须按降级顺序换源

**目的**：使偏差透明化。如果最终判定为"中断"，必须能看到 H_延续一侧也做了充分搜索但未找到有力证据。

---

## 与 web-access 技能集成

本技能依赖 web-access 进行所有 CDP 数据采集（gmapi 之外的部分）。

**执行方式**：

1. 先运行 web-access 的依赖检查：`node "C:/Users/CHAOFAN/.claude/skills/web-access-2.5.1/scripts/check-deps.mjs"`
2. 通过 CDP 浏览器访问数据源（详见 `references/data_sources.md`）
3. 使用 `/eval` 提取页面内容
4. 任务完成后关闭所有创建的 tab

**统一工具策略：gmapi（硬数据）+ CDP（软证据）混合采集**

| 数据类型               | 首选采集方式             | 备选/降级                          |
| ---------------------- | ------------------------ | ---------------------------------- |
| 龙虎榜异动/营业部明细  | **gmapi**（精确）        | CDP 东财龙虎榜                     |
| 个股资金流             | **gmapi**（含五档）      | CDP 东财资金流                     |
| 板块成分股 + 共振判定  | **gmapi**（已自动算）    | CDP 东财板块行情                   |
| 历史 K 线 + 涨停判定   | **gmapi**（精确涨跌停）  | CDP K线图                          |
| 业绩预告               | **gmapi**（含业务说明）  | CDP 巨潮资讯                       |
| 公司异动公告/概念否认  | **CDP 巨潮资讯**（必查） | —                                  |
| 新闻标题概念词         | **CDP 东财新闻**（必查） | —                                  |
| 问询函/关注函/停牌核查 | **CDP 交易所官网**       | —                                  |
| 板块资金流             | gmapi 成分股求和 / CDP   | 两者皆可                           |
| 行业基本面数据（1.2b） | **CDP 行业专业平台**     | 东财辅助（必查两个来源）           |
| 历史相似案例库         | **CDP 搜索引擎**         | —                                  |

**降级规则**：

- gmapi 调用失败 → 记录到 `fallback_needed`，CDP 阶段补
- CDP 页面加载超时或无响应 → 换一个同类型平台
- CDP 页面内容为空（需登录/付费）→ 换一个同类型平台
- WebReader 不支持中文 URL，不适用于国内数据源

行业基本面数据的获取流程（仅当 1.2 判定板块共振时触发）：

1. 识别概念所属行业类型（从 `sector_info.industry.sw.name` 读取）
2. 查 `references/data_sources.md` 中的"行业与平台映射表"
3. 优先在对应行业平台搜索（卓创/SMM/生意社等）
4. 补充东财新闻/机构调研作为辅助

---

## 与 stock-analysis 技能集成

### 输入（来自 stock-analysis）

- 股票代码
- 当前技术评分（可选）
- 末期得分（可选）
- 连续涨停天数（可选）

### 输出（回传至 stock-analysis）

- 验证得分（0-100）
- 验证乘数（0.7-1.0）
- 调整后技术得分
- 关键验证点确认/否认

### 集成方式

验证报告末尾包含"技术评分调整建议"块：

```
技术评分调整建议：
- 原始技术得分：__分
- 验证乘数：×__
- 调整后得分：__分
- 调整原因：[简要说明]
```

---

## 文件结构

```
trend-verify/
├── SKILL.md                                   # 本文件
├── scripts\
│   ├── _common.py                             # 公共模块（token/软失败/JSON工具）
│   └── gmapi_fetcher.py                       # Step 0' 主采集脚本
├── templates\
│   ├── verification_checklist.md              # 三层检查清单（双假设槽位）
│   ├── scoring_rules.md                       # 评分规则 + 乘数映射
│   ├── verification_report.md                 # 报告输出模板
│   └── gmapi_data_package.md                  # gmapi JSON 数据包 Schema
└── references\
    ├── data_sources.md                        # 数据源 URL 目录
    ├── cdp_search_strategy.md                 # CDP 搜索策略与反爬应对（搜索引擎可靠性表/降级顺序/直连URL清单）
    ├── gmapi_to_trend_verify_mapping.md       # gmapi 字段 → 检查项映射
    └── historical_patterns.md                 # 历史模式基线表
```

---

## 重要说明

- 本技能不执行任何交易操作，仅供分析参考
- 验证评分是概率判断，非绝对预测
- 催化剂坍塌是最强的趋势中断信号，优先级高于所有技术指标
- gmapi 仅覆盖硬数据（数值型），文本类证据（公告/新闻/函件）必须走 CDP
- 报告不构成投资建议
