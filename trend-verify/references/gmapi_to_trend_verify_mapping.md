# gmapi 接口 → trend-verify 检查项映射表

本文件给出每个 trend-verify 检查项应该使用的 gmapi 数据字段，以及当 gmapi 失败时的 CDP 降级方案。

**核心策略**: gmapi 提供硬数据（数值型），CDP 提供软证据（文本型）。先用 gmapi 拉满，再让 CDP 补文本类证据。

---

## 数据采集优先级

```
trend-verify 工作流
    ↓
Step 0'（新增）: gmapi_fetcher.py 批量预采集
    ↓ 输出 JSON 数据包 + fallback_needed 清单
Step 0 ~ Step 5: 读取 JSON 包 + 按 fallback_needed 走 CDP
```

---

## 检查项 × gmapi 字段映射

### Step 0: 概念发现

| 检查内容 | gmapi 字段 | 是否覆盖 | CDP 降级 |
|---------|-----------|---------|---------|
| 上榜原因（异动类型） | `abnor_changes[].change_type_name` | ✅ 完整 | 巨潮/东财龙虎榜页面 |
| 所属概念板块清单 | `sector_info.concepts` | ✅ 完整（44+ 个） | 东财个股所属板块页 |
| 近期新闻标题中的概念词 | — | ❌ 不覆盖 | 东财新闻搜索（必查） |
| 涨停板数 | `history.limit_up_count` | ✅ 完整 | K线图 |

### Layer 1.1: 公司确认/否认（P0，权重 20/40）

| 检查内容 | gmapi 字段 | 是否覆盖 | CDP 降级 |
|---------|-----------|---------|---------|
| 业绩预告（确认业绩方向） | `finance_forecast[].fcst_content` + `change_reason` | ✅ 完整 | 巨潮资讯业绩预告页 |
| **异动公告/概念否认公告** | — | ❌ 不覆盖 | **巨潮资讯搜索（必查 P0）** |

**重要**: 概念否认/澄清公告是 Layer 1.1 的 P0 信号。gmapi 不提供该数据，**必须走 CDP**。如果只读 gmapi 数据包，会漏掉"催化剂坍塌"判定。

### Layer 1.2: 板块共振 vs 独狼（P1，权重 10/40）

| 检查内容 | gmapi 字段 | 是否覆盖 | CDP 降级 |
|---------|-----------|---------|---------|
| 个股所属概念板块 | `sector_info.concepts` | ✅ 完整 | — |
| 板块成分股清单 | （内部已调用 `stk_get_sector_constituents`） | ✅ 自动算 | — |
| 板块内个股涨幅分布 | `sector_resonance.top_gainers` + `top_losers` | ✅ 已自动算 | — |
| 涨幅 > 3% 个股数量 | `sector_resonance.up3_count` | ✅ 已自动算 | — |
| **共振判定** | `sector_resonance.resonance_level` | ✅ 直接用 | — |

**判定映射**:
- `resonance_level == "强"` (up3_count >= 5) → H_延续 +10 分
- `resonance_level == "中"` (up3_count 3~4) → H_延续 +6~+8 分
- `resonance_level == "弱/无"` (up3_count <= 2) → 转向 H_中断评估（独狼风险）

### Layer 1.2b: 板块趋势逻辑验证（条件触发）

| 检查内容 | gmapi 字段 | 是否覆盖 | CDP 降级 |
|---------|-----------|---------|---------|
| 板块是否触发共振（触发条件） | `sector_resonance.resonance == true` | ✅ 触发器 | — |
| 行业类型识别 | `sector_info.industry.sw.name`（如"有色金属"） | ✅ 提示 | — |
| **行业基本面数据（价格/开工率/产能）** | — | ❌ 不覆盖 | **行业专业平台（卓创/SMM/生意社等）** |
| **政策/监管动态** | — | ❌ 不覆盖 | 东财新闻 + 行业平台 |
| **板块龙头公告** | — | ❌ 不覆盖 | 巨潮资讯搜龙头 |

**触发条件**: 当 `sector_resonance.resonance == true` 时，自动追加该项到 `fallback_needed`，并标注行业类型供后续选择平台。

### Layer 1.3: 事件驱动 vs 主题驱动（P1，权重 10/40）

| 检查内容 | gmapi 字段 | 是否覆盖 | CDP 降级 |
|---------|-----------|---------|---------|
| 业绩预告存在性 | `finance_forecast.length > 0` | ✅ 部分提示 | — |
| **催化剂性质（事件/主题判定）** | — | ❌ 不覆盖 | 东财新闻分析（必查） |

### Layer 2.1: 龙虎榜买卖结构（P1，权重 15/35）

| 检查内容 | gmapi 字段 | 是否覆盖 | CDP 降级 |
|---------|-----------|---------|---------|
| 买入前5 / 卖出前5 明细 | `sales_depts.details`（已按 side 分组） | ✅ 完整 | 东财龙虎榜明细页 |
| 机构专用席位 | `sales_depts.institution_seats` | ✅ 已分类 | — |
| **北向资金席位** | `sales_depts.northbound_seats`（深股通/沪股通席位） | ✅ 已分类 | — |
| 北向资金净额占比 | 计算: `northbound_seats.net_amount 求和 / 总成交额` | ✅ 可算 | — |

**重要**: gmapi 的 `stk_active_stock_top10_shszhk_info(types='NF')` 北向资金接口**实际返回空**（文档说支持但实测不可用）。**必须从 `sales_depts.northbound_seats` 反推**。

### Layer 2.2: 大额卖出方（P1，权重 10/35）

| 检查内容 | gmapi 字段 | 是否覆盖 | CDP 降级 |
|---------|-----------|---------|---------|
| 单营业部净卖出额 | `sales_depts.big_sellers[].net_amount` | ✅ 完整 | — |
| 阈值分级 | 已自动计算 | ✅ | — |

**判定映射**（自动）:
- `|net_amount| >= 1 亿` → H_中断 -10 分
- `|net_amount| 5000万-1亿` → H_中断 -7 分
- `|net_amount| 3000万-5000万` → H_中断 -4 分
- 无 ≥3000万 卖出方 → H_延续 +10 分

### Layer 2.3: 板块资金流（P2，权重 10/35）

| 检查内容 | gmapi 字段 | 是否覆盖 | CDP 降级 |
|---------|-----------|---------|---------|
| 个股资金流（五档） | `money_flow` | ✅ 完整 | 东财个股资金流页 |
| **板块整体资金流** | （gmapi 无直接接口） | ⚠️ 需自实现 | 东财板块资金流页 |

**自实现思路**（在 Step 0' 之外的扩展脚本中）:
```python
# 拿板块所有成分股
constituents = stk_get_sector_constituents(sector_code=sector_code)
symbols = constituents["symbol"].tolist()

# 批量拉资金流并求和
total_main_net = 0
for sym in symbols:
    mf = stk_get_money_flow(symbols=sym, trade_date=date)
    if mf is not None and not mf.empty:
        total_main_net += mf.iloc[0]["main_net_in"]

# 判定
if total_main_net > 10e8:  # >10亿
    H_延续 +10
```

### Layer 3.1: 历史相似案例（P1，权重 15/25）

| 检查内容 | gmapi 字段 | 是否覆盖 | CDP 降级 |
|---------|-----------|---------|---------|
| 个股近期 K 线模式 | `history.klines[]`（含 is_limit_up/down） | ✅ 完整 | — |
| 涨停板数统计 | `history.limit_up_count` | ✅ | — |
| **历史相似案例库（事件标注）** | — | ❌ 不覆盖 | **搜索引擎（财经媒体）** |

**判定映射**:
- K 线模式可由 `history.klines` 自动提取（如连续 N 日涨停 + 高换手）
- 但"N 连板 + 概念否认后历史走势"需要文本搜索

### Layer 3.2: 监管风险（P2，权重 10/25）

| 检查内容 | gmapi 字段 | 是否覆盖 | CDP 降级 |
|---------|-----------|---------|---------|
| **问询函/关注函** | — | ❌ 不覆盖 | 深交所/上交所官网 |
| **停牌核查** | — | ❌ 不覆盖 | 同上 |
| 财务审计意见（间接信号） | （可用 `stk_get_finance_audit` 扩展） | ⚠️ 部分 | 巨潮资讯审计意见 |

---

## CDP 采集顺序建议

读取 `fallback_needed` 后，按以下顺序在 CDP 阶段补数据：

1. **P0 必查（先做）**:
   - 异动公告/概念否认公告（巨潮资讯）— 关系到"催化剂坍塌"判定
   - 问询函/关注函（交易所官网）— 关系到 Layer 3.2 直接扣分

2. **P1 应查**:
   - 新闻标题中的概念词（东财新闻）— Step 0 必备
   - 板块驱动逻辑链（行业平台）— 仅当 1.2 判定为共振时

3. **P2 可查**:
   - 板块资金流（东财）— 如未在 gmapi 阶段自实现
   - 历史相似案例库（搜索引擎）

---

## 异常处理与软失败

`fallback_needed` 中可能包含软失败项（gmapi 调用异常），结构如下：

```json
{
  "name": "个股所属概念板块",
  "error": "TypeError: ...",
  "time": "2026-06-15T19:09:13",
  "duration_s": 0.05
}
```

处理策略：
- 软失败项同样需要在 CDP 阶段补
- 通过 `error` 字段可判断失败原因（网络问题 vs 参数问题）
- 多次软失败需检查 token 是否过期

---

## 完整的 gmapi 函数清单（已验证可用）

| 接口 | 用途 | 签名关键点 |
|------|------|-----------|
| `stk_abnor_change_stocks` | 龙虎榜异动 | `(symbols, change_types, trade_date, fields, df)` 仅单日 |
| `stk_abnor_change_detail` | 营业部明细 | 同上，按 side 区分买卖 |
| `stk_get_sector_category` | 板块分类列表 | `(sector_type)` 1003=概念 |
| `stk_get_symbol_sector` | 个股所属板块 | `(symbols, sector_type)` 无 df 参数 |
| `stk_get_sector_constituents` | 板块成分股 | `(sector_code)` 无 df 参数 |
| `stk_get_symbol_industry` | 个股所属行业 | `(symbols, source, level, date)` |
| `stk_get_money_flow` | 个股资金流 | `(symbols, trade_date)` |
| `stk_get_finance_forecast` | 业绩预告 | `(symbols, rpt_type, date, df)` |
| `stk_get_finance_audit` | 财务审计 | `(symbols, date, rpt_date, df)` |
| `history` / `history_n` | K 线 | 含 `df=True` |
| `get_history_symbol` | 涨跌停价 | `(symbol, start_date, end_date, df=True)` |

**已知不可用**:
- `stk_active_stock_top10_shszhk_info(types='NF')` 北向资金类型 → 返回空，必须用 `sales_depts.northbound_seats` 反推
