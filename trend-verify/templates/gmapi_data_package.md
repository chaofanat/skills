# gmapi 数据包 Schema 定义

本文件定义 `gmapi_fetcher.py` 输出的 JSON 数据包结构。trend-verify 后续 Step 0~5 读取本包作为已知硬数据源，CDP 阶段只需补 `fallback_needed` 中的项。

---

## 调用方式

```bash
# 默认查最近 30 天
python .claude/skills/trend-verify/scripts/gmapi_fetcher.py SZSE.002428

# 指定日期范围
python .claude/skills/trend-verify/scripts/gmapi_fetcher.py SHSE.600141 --start 2026-05-01 --end 2026-06-15
```

股票代码必须含交易所前缀（`SZSE.` 深市 / `SHSE.` 沪市）。

## 输出位置

| 类型 | 路径 |
|------|------|
| JSON 数据包 | `股票分析数据/{YYYY-MM-DD}/{symbol}_gmapi_package.json` |
| Markdown 报告 | `股票分析报告/{YYYY-MM-DD}/{symbol}_gmapi_report.md` |

---

## JSON 数据包结构

### meta

```json
{
  "meta": {
    "symbol": "SZSE.002428",
    "fetch_time": "2026-06-15 19:09:13",
    "date_range": {"start": "2026-05-16", "end": "2026-06-15"},
    "gmapi_version": "3.0.184",
    "total_duration_s": 3.23
  }
}
```

### sector_info — 板块与行业归属

```json
{
  "sector_info": {
    "concepts": [
      {"sector_code": "007024", "sector_name": "稀缺资源"},
      {"sector_code": "007068", "sector_name": "光伏概念"},
      ...
    ],
    "industry": {
      "sw": {"code": "240000", "name": "有色金属"},
      "zjh": {"code": "C", "name": "制造业"}
    },
    "concept_count": 23
  }
}
```

**trend-verify 用途**: Layer 1.2 板块共振、1.2b 板块逻辑验证、Step 0 概念发现

### abnor_changes — 龙虎榜异动记录

```json
{
  "abnor_changes": [
    {
      "trade_date": "2026-06-15",
      "change_type": "113",
      "change_type_name": "连续三个交易日内，涨幅偏离值累计达到20%的证券",
      "close": 101.49,
      "prc_change_rate": 10.0043,
      "cum_amount": 12345678900.0,
      "stat_value": 20.69
    },
    ...
  ]
}
```

**trend-verify 用途**: Step 0 概念发现（从 `change_type_name` 提取上榜原因）

### sales_depts — 龙虎榜营业部明细

```json
{
  "sales_depts": {
    "trade_date": "2026-06-15",
    "details": [
      {
        "side": 0,  // 0=买入, 1=卖出
        "sales_dept": "深股通专用",
        "buy_amount": 1210430000.0,
        "sell_amount": 1241790000.0,
        "net_amount": -31360000.0,
        "rank": 1
      },
      ...
    ],
    "big_sellers": [
      // side=1 且 |net_amount| >= 3000万 的项
    ],
    "institution_seats": [
      // 含"机构专用"但不含"深股通/沪股通"的项
    ],
    "northbound_seats": [
      // 含"深股通专用"或"沪股通专用"的项
    ]
  }
}
```

**trend-verify 用途**:
- Layer 2.1 买卖结构：根据 institution_seats 占比判定 H_延续/H_中断
- Layer 2.2 大额卖出方：直接使用 `big_sellers`，按 net_amount 触发阈值
- 北向资金识别：`northbound_seats` 净额合计（gmapi 的 `stk_active_stock_top10_shszhk_info` NF 类型已知不可用，必须从这里反推）

### money_flow — 个股资金流

```json
{
  "money_flow": {
    "trade_date": "2026-06-15",
    "main_net_in": 1326000000.0,
    "main_net_in_rate": 13.80,
    "super_net_in": 1705000000.0,
    "large_net_in": -380000000.0,
    "mid_net_in": -805000000.0,
    "small_net_in": -521000000.0
  }
}
```

**trend-verify 用途**: Layer 2.3 板块资金流（板块级需通过成分股求和实现，详见 `gmapi_to_trend_verify_mapping.md`）

### sector_resonance — 板块共振判定（已自动算）

```json
{
  "sector_resonance": {
    "sector_code": "007024",
    "sector_name": "稀缺资源",
    "total_constituents": 78,
    "sampled": 30,
    "calculated": 30,
    "up3_count": 11,
    "up3_pct": 36.7,
    "resonance": true,
    "resonance_level": "强",
    "top_gainers": [
      {"symbol": "SZSE.002428", "chg_pct": 10.0},
      ...
    ],
    "top_losers": [...]
  }
}
```

**共振判定阈值**:
- `up3_count >= 5` → 强共振（H_延续 +10）
- `up3_count 3~4` → 中共振（H_延续 +6~+8）
- `up3_count <= 2` → 弱/无共振（H_中断 风险）

**trend-verify 用途**: Layer 1.2 板块共振 vs 独狼的核心判定

### finance_forecast — 业绩预告

```json
{
  "finance_forecast": [
    {
      "pub_date": "2026-01-31",
      "rpt_type": "12",
      "fcst_type": "预减",
      "fcst_field": "归属于上市公司股东的净利润",
      "increase_pct_min": -71.75,
      "increase_pct_max": -58.57,
      "fcst_content": "预计2025年1-12月...盈利:1,500万元至2,200万元...",
      "change_reason": "1、报告期内,随着国内低轨通信卫星组网的推进..."
    },
    ...
  ]
}
```

**trend-verify 用途**: Layer 1.1 公司确认/否认的辅助证据 — 从 `fcst_content` 和 `change_reason` 提取业务进展

### history — 历史 K 线 + 涨停统计

```json
{
  "history": {
    "klines": [
      {
        "trade_date": "2026-06-15",
        "open": 95.00,
        "high": 101.49,
        "low": 93.00,
        "close": 101.49,
        "volume": 12345678,
        "amount": 1234567890.0,
        "pct_chg": 10.0,
        "is_limit_up": true,
        "is_limit_down": false
      },
      ...
    ],
    "limit_up_count": 5,
    "limit_down_count": 1,
    "latest_close": 101.49
  }
}
```

**涨停判定逻辑**: `close == upper_limit`（来自 `get_history_symbol`），失败时回退到 `pct_chg >= 9.8`

**trend-verify 用途**: Step 0 识别连续涨停、Layer 3.1 历史相似案例（K 线模式匹配）

### fallback_needed — 待 CDP 补充的数据项

```json
{
  "fallback_needed": [
    {
      "name": "异动公告/概念否认公告",
      "source": "巨潮资讯 cninfo.com.cn",
      "reason": "gmapi 仅提供业绩预告，无概念否认/澄清公告文本"
    },
    {
      "name": "板块驱动逻辑链（行业基本面）",
      "source": "行业专业平台（卓创/SMM/生意社等）",
      "reason": "板块 稀缺资源 触发共振，需验证逻辑",
      "industry": "有色金属"
    },
    ...
  ],
  "fallback_count": 6
}
```

**类型**:
1. **永久型 fallback**（gmapi 永远不提供）：
   - 异动公告/概念否认公告
   - 新闻标题中的概念词
   - 问询函/关注函/停牌核查
   - 历史相似案例库

2. **条件型 fallback**（仅当满足条件时触发）：
   - 板块驱动逻辑链：仅当 `sector_resonance.resonance == true`

3. **软失败 fallback**（gmapi 调用异常时记录）：
   - 字段 `error` 包含异常类型和消息
   - 同样需要在 CDP 阶段补充

---

## 读取示例

```python
import json

# Step 0' 之后，trend-verify 各 Step 读 JSON 包
with open("股票分析数据/2026-06-15/SZSE.002428_gmapi_package.json", encoding="utf-8") as f:
    pkg = json.load(f)

# 拿大额卖出方判定 Layer 2.2
big_sellers = pkg["sales_depts"]["big_sellers"]
for s in big_sellers:
    net = s["net_amount"]
    if abs(net) >= 1e8:
        print(f"H_中断 -10: {s['sales_dept']} 净卖出 {net/1e8:+.2f} 亿")
    elif abs(net) >= 5e7:
        print(f"H_中断 -7: {s['sales_dept']} 净卖出 {net/1e8:+.2f} 亿")
    elif abs(net) >= 3e7:
        print(f"H_中断 -4: {s['sales_dept']} 净卖出 {net/1e8:+.2f} 亿")

# 拿板块共振判定 Layer 1.2
r = pkg["sector_resonance"]
if r["resonance"]:
    if r["up3_count"] >= 5:
        print("Layer 1.2 H_延续 +10（强共振）")
    elif r["up3_count"] >= 3:
        print("Layer 1.2 H_延续 +6~+8（中共振）")
```
