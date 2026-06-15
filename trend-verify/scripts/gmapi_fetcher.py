"""trend-verify 数据采集主脚本。

输入：股票代码（含交易所前缀，如 SZSE.002428）+ 日期范围
输出：
  1. JSON 数据包 → 股票分析数据/{today}/{symbol}_gmapi_package.json
  2. Markdown 报告 → 股票分析报告/{today}/{symbol}_gmapi_report.md
  3. fallback_needed 列表嵌入在 JSON 中（CDP 阶段读取）

设计原则：
- 每个 gmapi 调用独立 try/except（软失败），失败不中断主流程
- 北向资金接口已知返回空 → 直接记入 fallback
- 文本类数据（异动公告/新闻/问询函/行业数据）不在本脚本范围，全部记入 fallback

用法：
    python gmapi_fetcher.py SZSE.002428
    python gmapi_fetcher.py SHSE.600141 --start 2026-05-01 --end 2026-06-15
"""
import argparse
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# 让脚本既能直接运行又能作为模块导入
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from _common import setup_token, soft_fail, today_str, now_ts, write_json, CST
from gm.api import (
    stk_abnor_change_stocks, stk_abnor_change_detail,
    stk_get_symbol_sector, stk_get_sector_constituents, stk_get_symbol_industry,
    stk_get_money_flow, stk_get_finance_forecast,
    history, history_n, get_history_symbol,
)

# 项目根目录（用于输出位置）
PROJECT_ROOT = r"D:\workspace\股票工作站"


def fetch_sector_info(symbol, fallback):
    """1. 个股所属概念板块 + 行业分类。"""
    @soft_fail("个股所属概念板块", fallback)
    def _concepts():
        # stk_get_symbol_sector 实际返回 DataFrame，无 df 参数
        df = stk_get_symbol_sector(symbols=symbol, sector_type='1003')
        if df is None or (hasattr(df, "empty") and df.empty):
            return []
        result = []
        for _, row in df.iterrows():
            result.append({"sector_code": str(row.get("sector_code", "")),
                           "sector_name": str(row.get("sector_name", ""))})
        return result
    concepts_res = _concepts()
    concepts_list = concepts_res["data"] if concepts_res["ok"] else []

    @soft_fail("个股所属行业", fallback)
    def _industry():
        df_sw = stk_get_symbol_industry(symbols=symbol, source='sw2021', level=1)
        df_zjh = stk_get_symbol_industry(symbols=symbol, source='zjh2012', level=1)
        return {"sw": df_sw, "zjh": df_zjh}
    ind_res = _industry()
    industry = {}
    if ind_res["ok"] and ind_res["data"]:
        for k, v in ind_res["data"].items():
            if v is None or (hasattr(v, "empty") and v.empty):
                continue
            row = v.iloc[0] if hasattr(v, "iloc") else v[0]
            industry[k] = {
                "code": str(row.get("industry_code", "") or ""),
                "name": str(row.get("industry_name", "") or ""),
            }

    return {"concepts": concepts_list, "industry": industry,
            "concept_count": len(concepts_list)}


def fetch_abnor_changes(symbol, date_list, fallback):
    """2. 龙虎榜异动记录（逐日查询）。"""
    @soft_fail("龙虎榜异动记录", fallback)
    def _inner():
        records = []
        for d in date_list:
            r = stk_abnor_change_stocks(symbols=symbol, trade_date=d, df=True)
            if r is not None and not r.empty:
                for _, row in r.iterrows():
                    records.append({
                        "trade_date": str(row.get("trade_date", ""))[:10],
                        "change_type": row.get("change_type"),
                        "change_type_name": row.get("change_type_name"),
                        "close": row.get("close"),
                        "prc_change_rate": row.get("prc_change_rate"),
                        "cum_amount": row.get("cum_amount"),
                        "stat_value": row.get("stat_value"),
                    })
        return records
    res = _inner()
    return res["data"] or []


def fetch_sales_depts(symbol, date_list, fallback):
    """3. 龙虎榜营业部明细 + 大额卖出方自动识别。"""
    @soft_fail("龙虎榜营业部明细", fallback)
    def _inner():
        # 找该股最近的上榜日
        first_trade_date = None
        for d in date_list:
            r = stk_abnor_change_stocks(symbols=symbol, trade_date=d, df=True)
            if r is not None and not r.empty:
                first_trade_date = d
                break
        if not first_trade_date:
            return {"trade_date": None, "details": [], "big_sellers": [],
                    "institution_seats": [], "northbound_seats": []}

        df = stk_abnor_change_detail(symbols=symbol, trade_date=first_trade_date, df=True)
        if df is None or df.empty:
            return {"trade_date": first_trade_date, "details": [], "big_sellers": [],
                    "institution_seats": [], "northbound_seats": []}

        # 营业部明细
        details = []
        for _, row in df.iterrows():
            details.append({
                "side": int(row.get("side", -1)),  # 0=买入 1=卖出
                "sales_dept": str(row.get("sales_dept", "")),
                "buy_amount": float(row.get("buy_amount", 0) or 0),
                "sell_amount": float(row.get("sell_amount", 0) or 0),
                "net_amount": float(row.get("buy_amount", 0) or 0) - float(row.get("sell_amount", 0) or 0),
                "rank": int(row.get("rank", 0) or 0),
            })

        # 大额卖出方识别（≥3000万）
        sells = [d for d in details if d["side"] == 1]
        big_sellers = [s for s in sells if abs(s["net_amount"]) >= 3000_0000]

        # 机构席位识别
        inst_keywords = ['机构专用', '沪股通', '深股通', '北向']
        institution_seats = [d for d in details
                              if any(k in d["sales_dept"] for k in inst_keywords)
                              and "深股通" not in d["sales_dept"]
                              and "沪股通" not in d["sales_dept"]]
        # 北向资金席位单独识别（深股通/沪股通专用）
        northbound_seats = [d for d in details
                            if "深股通" in d["sales_dept"] or "沪股通" in d["sales_dept"]]

        return {"trade_date": first_trade_date, "details": details,
                "big_sellers": big_sellers,
                "institution_seats": institution_seats,
                "northbound_seats": northbound_seats}
    res = _inner()
    return res["data"] or {"trade_date": None, "details": [], "big_sellers": [],
                           "institution_seats": [], "northbound_seats": []}


def fetch_money_flow(symbol, trade_date, fallback):
    """4. 个股资金流（单日五档）。"""
    @soft_fail("个股资金流", fallback)
    def _inner():
        df = stk_get_money_flow(symbols=symbol, trade_date=trade_date)
        if df is None or (hasattr(df, "empty") and df.empty):
            return None
        row = df.iloc[0] if hasattr(df, "iloc") else df[0]
        return {
            "trade_date": str(row.get("trade_date", ""))[:10],
            "main_net_in": float(row.get("main_net_in", 0) or 0),
            "main_net_in_rate": float(row.get("main_net_in_rate", 0) or 0),
            "super_net_in": float(row.get("super_net_in", 0) or 0),
            "large_net_in": float(row.get("large_net_in", 0) or 0),
            "mid_net_in": float(row.get("mid_net_in", 0) or 0),
            "small_net_in": float(row.get("small_net_in", 0) or 0),
        }
    res = _inner()
    return res["data"]


def fetch_sector_resonance(symbol, sector_info, end_date, fallback):
    """5. 板块共振判定：取第一个概念板块，对成分股算当日涨幅>3% 数量。"""
    @soft_fail("板块共振判定", fallback)
    def _inner():
        if not sector_info.get("concepts"):
            return {"resonance": False, "reason": "无所属概念板块"}
        first = sector_info["concepts"][0]
        sector_code = first["sector_code"]
        sector_name = first["sector_name"]

        # 拉成分股
        constituents = stk_get_sector_constituents(sector_code=sector_code)
        if constituents is None or (hasattr(constituents, "empty") and constituents.empty):
            return {"resonance": False, "reason": f"板块 {sector_name} 无成分股",
                    "sector_code": sector_code, "sector_name": sector_name}
        symbols = constituents["symbol"].tolist()
        # 抽样最多 30 只（避免接口调用过多）
        sample = symbols[:30]

        # 批量算涨幅
        chg_list = []
        for sym in sample:
            try:
                bars = history_n(symbol=sym, frequency='1d', count=2,
                                 end_time=end_date, df=True)
                if bars is not None and len(bars) >= 2:
                    pre, cur = float(bars.iloc[-2]['close']), float(bars.iloc[-1]['close'])
                    chg = (cur - pre) / pre * 100 if pre > 0 else 0
                    chg_list.append({"symbol": sym, "chg_pct": round(chg, 2)})
            except Exception:
                pass

        up3 = sum(1 for x in chg_list if x["chg_pct"] > 3)
        up2 = sum(1 for x in chg_list if x["chg_pct"] > 3)
        return {
            "sector_code": sector_code, "sector_name": sector_name,
            "total_constituents": len(symbols),
            "sampled": len(sample),
            "calculated": len(chg_list),
            "up3_count": up3,
            "up3_pct": round(up3 / max(len(chg_list), 1) * 100, 1),
            "resonance": up3 >= 3,
            "resonance_level": "强" if up3 >= 5 else ("中" if up3 >= 3 else "弱/无"),
            "top_gainers": sorted(chg_list, key=lambda x: -x["chg_pct"])[:5],
            "top_losers": sorted(chg_list, key=lambda x: x["chg_pct"])[:5],
        }
    res = _inner()
    return res["data"] or {"resonance": False, "reason": "计算失败"}


def fetch_finance_forecast(symbol, fallback):
    """6. 业绩预告（含 fcst_content + change_reason 业务说明）。"""
    @soft_fail("业绩预告", fallback)
    def _inner():
        df = stk_get_finance_forecast(symbols=symbol, df=True)
        if df is None or df.empty:
            return []
        key_cols = ['pub_date', 'rpt_type', 'fcst_type', 'fcst_field',
                    'increase_pct_min', 'increase_pct_max',
                    'fcst_content', 'change_reason']
        avail = [c for c in key_cols if c in df.columns]
        result = []
        for _, row in df.iterrows():
            item = {c: row.get(c) for c in avail}
            # pub_date 截断到日期
            if 'pub_date' in item and item['pub_date']:
                item['pub_date'] = str(item['pub_date'])[:10]
            result.append(item)
        return result
    res = _inner()
    return res["data"] or []


def fetch_history(symbol, end_date, days=30, fallback=None):
    """7. 历史 K 线 + 涨停板识别。"""
    if fallback is None:
        fallback = []

    @soft_fail("历史K线", fallback)
    def _inner():
        end = datetime.strptime(end_date, "%Y-%m-%d")
        start = end - timedelta(days=days * 2)  # 留 buffer 跳过非交易日
        df = history(symbol=symbol, frequency='1d',
                     start_time=start.strftime("%Y-%m-%d"),
                     end_time=end_date, df=True)
        if df is None or df.empty:
            return {"klines": [], "limit_up_count": 0, "limit_down_count": 0}

        # 取最近 N 个交易日
        df = df.tail(days).copy()
        df['pct_chg'] = (df['close'].pct_change() * 100).round(2)

        # 用 get_history_symbol 拿 upper_limit/lower_limit 精确判定
        limit_df = get_history_symbol(symbol=symbol,
                                       start_date=df['eob'].iloc[0].strftime("%Y-%m-%d"),
                                       end_date=df['eob'].iloc[-1].strftime("%Y-%m-%d"),
                                       df=True)
        # 合并涨跌停价
        if limit_df is not None and not limit_df.empty:
            limit_df['trade_date'] = limit_df['trade_date'].dt.strftime("%Y-%m-%d")
            df['trade_date_str'] = pd.to_datetime(df['eob']).dt.strftime("%Y-%m-%d")
            merged = df.merge(limit_df[['trade_date', 'upper_limit', 'lower_limit']],
                              left_on='trade_date_str', right_on='trade_date', how='left')
        else:
            merged = df.copy()
            merged['upper_limit'] = None
            merged['lower_limit'] = None

        # 涨停判定：close == upper_limit（精确）或 pct_chg >= 9.8（兜底）
        merged['is_limit_up'] = (
            (merged['close'] == merged['upper_limit']) |
            ((merged['upper_limit'].isna()) & (merged['pct_chg'] >= 9.8))
        ).astype(bool)
        merged['is_limit_down'] = (
            (merged['close'] == merged['lower_limit']) |
            ((merged['lower_limit'].isna()) & (merged['pct_chg'] <= -9.8))
        ).astype(bool)

        klines = []
        for _, row in merged.iterrows():
            klines.append({
                "trade_date": str(row.get('eob', ''))[:10],
                "open": float(row.get('open', 0)),
                "high": float(row.get('high', 0)),
                "low": float(row.get('low', 0)),
                "close": float(row.get('close', 0)),
                "volume": float(row.get('volume', 0)),
                "amount": float(row.get('amount', 0)),
                "pct_chg": float(row.get('pct_chg', 0)),
                "is_limit_up": bool(row.get('is_limit_up', False)),
                "is_limit_down": bool(row.get('is_limit_down', False)),
            })

        return {
            "klines": klines,
            "limit_up_count": int(merged['is_limit_up'].sum()),
            "limit_down_count": int(merged['is_limit_down'].sum()),
            "latest_close": float(merged.iloc[-1]['close']) if len(merged) else 0,
        }
    res = _inner()
    return res["data"] or {"klines": [], "limit_up_count": 0, "limit_down_count": 0}


def run_fetch(symbol, start_date, end_date):
    """主流程：执行所有 gmapi 采集，输出 JSON + MD。"""
    print(f"\n>>> trend-verify gmapi 数据采集")
    print(f"    股票代码: {symbol}")
    print(f"    日期范围: {start_date} ~ {end_date}\n")

    setup_token()

    # 生成候选交易日列表（只取工作日）
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    date_list = []
    cur = end_dt
    while cur >= start_dt and len(date_list) < 15:
        if cur.weekday() < 5:  # 周一~周五
            date_list.append(cur.strftime("%Y-%m-%d"))
        cur -= timedelta(days=1)
    date_list = sorted(date_list, reverse=True)  # 最新在前

    fallback = []
    t_total = datetime.now()

    # === 1. 板块与行业 ===
    print("[1/7] 板块与行业分类 ...")
    sector_info = fetch_sector_info(symbol, fallback)
    print(f"      命中 {sector_info.get('concept_count', 0)} 个概念板块")

    # === 2. 龙虎榜异动 ===
    print("[2/7] 龙虎榜异动记录 ...")
    abnor = fetch_abnor_changes(symbol, date_list, fallback)
    print(f"      {len(abnor)} 条异动记录")

    # === 3. 营业部明细 ===
    print("[3/7] 龙虎榜营业部明细 ...")
    sales = fetch_sales_depts(symbol, date_list, fallback)
    print(f"      {len(sales.get('details', []))} 条营业部记录")
    if sales.get('big_sellers'):
        print(f"      识别大额卖出方 {len(sales['big_sellers'])} 个")
    if sales.get('northbound_seats'):
        nb_net = sum(s['net_amount'] for s in sales['northbound_seats'])
        print(f"      北向席位净额: {nb_net/1e8:.2f} 亿")

    # === 4. 个股资金流 ===
    print(f"[4/7] 个股资金流（{end_date}） ...")
    money = fetch_money_flow(symbol, end_date, fallback)
    if money:
        print(f"      主力净流入: {money['main_net_in']/1e8:.2f} 亿 ({money['main_net_in_rate']:.2f}%)")

    # === 5. 板块共振判定 ===
    print("[5/7] 板块共振判定 ...")
    resonance = fetch_sector_resonance(symbol, sector_info, end_date, fallback)
    if resonance.get("resonance") is not None:
        print(f"      板块 {resonance.get('sector_name', '?')}: "
              f"涨幅>3% 共 {resonance.get('up3_count', 0)}/{resonance.get('calculated', 0)} 只"
              f" → {resonance.get('resonance_level', '?')}共振")

    # === 6. 业绩预告 ===
    print("[6/7] 业绩预告 ...")
    forecast = fetch_finance_forecast(symbol, fallback)
    print(f"      {len(forecast)} 条业绩预告")

    # === 7. 历史 K 线 ===
    print("[7/7] 历史 K 线 + 涨停判定 ...")
    history_data = fetch_history(symbol, end_date, days=30, fallback=fallback)
    print(f"      {len(history_data.get('klines', []))} 条 K 线, "
          f"涨停 {history_data.get('limit_up_count', 0)} 次, "
          f"跌停 {history_data.get('limit_down_count', 0)} 次")

    # === 永远需要 CDP 的项目 ===
    cdnp_must_have = [
        {"name": "异动公告/概念否认公告",
         "source": "巨潮资讯 cninfo.com.cn",
         "reason": "gmapi 仅提供业绩预告，无概念否认/澄清公告文本"},
        {"name": "近期新闻标题中的概念词",
         "source": "东财新闻搜索 so.eastmoney.com/news/s",
         "reason": "gmapi 无新闻接口"},
        {"name": "问询函/关注函/停牌核查",
         "source": "深交所/上交所官网",
         "reason": "gmapi 无监管函件接口"},
        {"name": "板块级资金流",
         "source": "成分股 money_flow 求和（已实现）/ 东财板块资金流",
         "reason": "gmapi 无直接板块资金流接口"},
        {"name": "历史相似案例库",
         "source": "搜索引擎（财经媒体）",
         "reason": "gmapi 有 K线但无历史事件标注"},
    ]

    # === 1.2b 板块逻辑验证（条件触发）===
    if resonance.get("resonance"):
        cdnp_must_have.append({
            "name": "板块驱动逻辑链（行业基本面）",
            "source": "行业专业平台（卓创/SMM/生意社等）",
            "reason": f"板块 {resonance.get('sector_name')} 触发共振，需验证逻辑",
            "industry": sector_info.get("industry", {}).get("sw", {}).get("name", "")
        })

    total_fallback = fallback + cdnp_must_have

    package = {
        "meta": {
            "symbol": symbol,
            "fetch_time": now_ts(),
            "date_range": {"start": start_date, "end": end_date},
            "gmapi_version": "3.0.184",
            "total_duration_s": round((datetime.now() - t_total).total_seconds(), 2),
        },
        "sector_info": sector_info,
        "abnor_changes": abnor,
        "sales_depts": sales,
        "money_flow": money,
        "sector_resonance": resonance,
        "finance_forecast": forecast,
        "history": history_data,
        "fallback_needed": total_fallback,
        "fallback_count": len(total_fallback),
    }

    # === 落盘 ===
    today = today_str()
    data_dir = os.path.join(PROJECT_ROOT, "股票分析数据", today)
    report_dir = os.path.join(PROJECT_ROOT, "股票分析报告", today)
    json_path = write_json(package, os.path.join(data_dir, f"{symbol}_gmapi_package.json"))
    md_path = generate_markdown_report(package, os.path.join(report_dir, f"{symbol}_gmapi_report.md"))

    print(f"\n>>> 输出:")
    print(f"    JSON 数据包: {json_path}")
    print(f"    MD 报告:    {md_path}")
    print(f"    软失败 {len(fallback)} 项 + 必查 CDP {len(cdnp_must_have)} 项 = 共 {len(total_fallback)} 项待补")
    print(f"    总耗时: {package['meta']['total_duration_s']}s")
    return package


def generate_markdown_report(package, filepath):
    """从 JSON 数据包生成 Markdown 报告。"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    s = package["sector_info"]
    a = package["abnor_changes"]
    sd = package["sales_depts"]
    m = package["money_flow"]
    r = package["sector_resonance"]
    f = package["finance_forecast"]
    h = package["history"]
    fb = package["fallback_needed"]

    sym = package["meta"]["symbol"]
    name = "（未获取）"  # 名称可从 sector_info 的 concepts 推断或后续 CDP 补充
    concepts_str = "、".join(c["sector_name"] for c in s.get("concepts", [])[:8])
    if s.get("concepts"):
        # 尝试从第一条概念记录反推（不一定准）
        pass

    lines = [
        f"# {sym} - gmapi 数据采集报告",
        "",
        f"**采集时间**: {package['meta']['fetch_time']}",
        f"**日期范围**: {package['meta']['date_range']['start']} ~ {package['meta']['date_range']['end']}",
        f"**总耗时**: {package['meta']['total_duration_s']}s",
        f"**待 CDP 补充项**: {package['fallback_count']}",
        "",
        "---",
        "",
        "## 1. 板块与行业归属",
        "",
        f"- **所属概念板块**: 共 {s.get('concept_count', 0)} 个",
    ]
    for c in s.get("concepts", [])[:15]:
        lines.append(f"  - {c.get('sector_code', '')} {c.get('sector_name', '')}")
    if s.get("concept_count", 0) > 15:
        lines.append(f"  - ... 还有 {s['concept_count'] - 15} 个")
    ind = s.get("industry", {})
    if ind:
        sw = ind.get("sw", {})
        zjh = ind.get("zjh", {})
        lines.append(f"- **申万行业**: {sw.get('code', '')} {sw.get('name', '')}")
        lines.append(f"- **证监会行业**: {zjh.get('code', '')} {zjh.get('name', '')}")

    # 2. 龙虎榜异动
    lines += ["", "## 2. 龙虎榜异动记录（近期）", ""]
    if a:
        lines += ["| 日期 | 异动类型 | 收盘价 | 涨跌幅% |",
                  "|------|---------|--------|---------|"]
        for item in a[:10]:
            lines.append(f"| {item.get('trade_date', '')} | {item.get('change_type_name', '')} | "
                         f"{item.get('close', '')} | {item.get('prc_change_rate', '')} |")
    else:
        lines.append("近期无龙虎榜异动。")

    # 3. 营业部明细
    lines += ["", f"## 3. 龙虎榜营业部明细（{sd.get('trade_date', '无')}）", ""]
    details = sd.get("details", [])
    if details:
        lines += ["| 方向 | 排名 | 营业部 | 买入(万) | 卖出(万) | 净额(万) |",
                  "|------|------|--------|---------|---------|---------|"]
        for d in sorted(details, key=lambda x: (x["side"], x["rank"])):
            side_str = "买" if d["side"] == 0 else "卖"
            lines.append(f"| {side_str} | {d['rank']} | {d['sales_dept'][:30]} | "
                         f"{d['buy_amount']/1e4:.0f} | {d['sell_amount']/1e4:.0f} | "
                         f"{d['net_amount']/1e4:+.0f} |")

        # 大额卖出方
        bigs = sd.get("big_sellers", [])
        if bigs:
            lines += ["", f"### ⚠️ 大额卖出方（净卖出 ≥ 3000万）", ""]
            lines += ["| 营业部 | 净额(万) | 阈值触发 |", "|--------|---------|---------|"]
            for b in bigs:
                net = b['net_amount']
                threshold = "≥1亿" if abs(net) >= 1e8 else ("≥5000万" if abs(net) >= 5e7 else "≥3000万")
                lines.append(f"| {b['sales_dept'][:30]} | {net/1e4:+.0f} | {threshold} |")

        # 北向席位
        nbs = sd.get("northbound_seats", [])
        if nbs:
            nb_net = sum(s_['net_amount'] for s_ in nbs)
            lines += ["", f"### 北向资金席位", "",
                      f"深股通/沪股通席位净额: **{nb_net/1e8:+.2f} 亿**"]
    else:
        lines.append("当日未上榜。")

    # 4. 资金流
    lines += ["", f"## 4. 个股资金流（{m.get('trade_date', '')}）", ""]
    if m:
        lines += [
            "| 类别 | 净流入(亿) | 净流入率(%) |",
            "|------|-----------|------------|",
            f"| 主力 | {m['main_net_in']/1e8:+.2f} | {m['main_net_in_rate']:+.2f} |",
            f"| 超大单 | {m['super_net_in']/1e8:+.2f} | - |",
            f"| 大单 | {m['large_net_in']/1e8:+.2f} | - |",
            f"| 中单 | {m['mid_net_in']/1e8:+.2f} | - |",
            f"| 小单 | {m['small_net_in']/1e8:+.2f} | - |",
        ]
    else:
        lines.append("未取到资金流数据。")

    # 5. 板块共振
    lines += ["", "## 5. 板块共振判定", ""]
    if r:
        if r.get("resonance") is True or r.get("resonance") is False:
            lines += [
                f"- **测试板块**: {r.get('sector_code', '')} {r.get('sector_name', '')}",
                f"- **成分股数**: {r.get('total_constituents', 0)} 只（抽样 {r.get('sampled', 0)}，成功计算 {r.get('calculated', 0)}）",
                f"- **涨幅>3%**: {r.get('up3_count', 0)}/{r.get('calculated', 0)} 只（{r.get('up3_pct', 0)}%）",
                f"- **判定**: {r.get('resonance_level', '')}共振",
            ]
            if r.get("top_gainers"):
                lines.append("- **Top 涨幅**:")
                for g in r["top_gainers"][:3]:
                    lines.append(f"  - {g['symbol']} +{g['chg_pct']:.2f}%")
        else:
            lines.append(f"- {r.get('reason', '未知原因')}")

    # 6. 业绩预告
    lines += ["", "## 6. 业绩预告", ""]
    if f:
        for item in f[:3]:
            lines += [
                f"### {item.get('pub_date', '')} - {item.get('fcst_type', '')}（{item.get('fcst_field', '')}）",
                f"- 增长幅度: {item.get('increase_pct_min', '?')}% ~ {item.get('increase_pct_max', '?')}%",
            ]
            content = item.get('fcst_content', '')
            if content:
                lines.append(f"- **内容**: {content[:200]}{'...' if len(content) > 200 else ''}")
            reason = item.get('change_reason', '')
            if reason:
                lines.append(f"- **变更原因**: {reason[:300]}{'...' if len(reason) > 300 else ''}")
            lines.append("")
    else:
        lines.append("无业绩预告记录。")

    # 7. 历史 K 线
    lines += ["", "## 7. 历史 K 线 + 涨停统计（近30日）", ""]
    if h and h.get("klines"):
        lines += [
            f"- **涨停板数**: {h['limit_up_count']} 次",
            f"- **跌停板数**: {h['limit_down_count']} 次",
            f"- **最新收盘**: {h['latest_close']}",
            "",
            "近期 K 线（最新 10 日）:",
            "",
            "| 日期 | 开 | 高 | 低 | 收 | 涨跌幅% | 涨停 | 跌停 |",
            "|------|----|----|----|----|---------|------|------|",
        ]
        for k in h["klines"][-10:]:
            lines.append(f"| {k['trade_date']} | {k['open']:.2f} | {k['high']:.2f} | "
                         f"{k['low']:.2f} | {k['close']:.2f} | {k['pct_chg']:+.2f} | "
                         f"{'是' if k['is_limit_up'] else ''} | {'是' if k['is_limit_down'] else ''} |")

    # 8. 待 CDP 补充
    lines += ["", "## 8. ⚠️ 待 CDP 补充的数据项", ""]
    if fb:
        lines += ["| 数据项 | 数据源 | 原因 |", "|--------|--------|------|"]
        for item in fb:
            lines.append(f"| {item.get('name', '')} | {item.get('source', '')} | {item.get('reason', '')} |")
        lines += ["",
                  "**下一阶段**（trend-verify Step 0~5）应优先通过 web-access/CDP 采集上述数据，"
                  "本 gmapi 报告中未涵盖。"]
    else:
        lines.append("无（gmapi 已覆盖全部所需数据）。")

    lines += ["", "---",
              f"*报告由 gmapi_fetcher.py 自动生成 · gm SDK 3.0.184*"]

    with open(filepath, "w", encoding="utf-8") as f_out:
        f_out.write("\n".join(lines))
    return filepath


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="trend-verify gmapi 数据采集")
    parser.add_argument("symbol", help="股票代码（含交易所前缀），如 SZSE.002428")
    parser.add_argument("--start", default=None,
                        help="开始日期 YYYY-MM-DD（默认：end_date 前 30 天）")
    parser.add_argument("--end", default=None,
                        help="结束日期 YYYY-MM-DD（默认：今天）")
    args = parser.parse_args()

    end_date = args.end or today_str()
    if args.start:
        start_date = args.start
    else:
        # 默认前 30 天
        from datetime import datetime as _dt, timedelta as _td
        start_date = (_dt.strptime(end_date, "%Y-%m-%d") - _td(days=30)).strftime("%Y-%m-%d")

    run_fetch(args.symbol, start_date, end_date)
