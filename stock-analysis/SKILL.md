---
name: stock-analysis
description: Chinese stock technical indicator analysis and report generation. Use when users provide a Chinese stock code or name and request: (1) Technical indicator analysis, (2) Stock price/moving average analysis, (3) MACD, KDJ, RSI indicators, (4) Trading volume analysis, (5) Bollinger Bands, ATR, or other technical indicators, (6) Comprehensive stock analysis reports, (7) Price trend analysis for A-share stocks. Supports 6-digit stock codes (e.g., 000001, 600036, 603259) for Chinese A-shares.
---

# Stock Technical Analysis

Analyzes Chinese A-share stocks and generates comprehensive technical indicator reports.

## Environment Setup

This skill uses an isolated virtual environment for all dependencies.

### Step 1: Install TA-Lib (System Dependency)

TA-Lib must be installed at the system level first:

- **Windows**: Download precompiled wheel from https://github.com/cgohlke/talib-build and install with pip
- **Linux**: `sudo apt-get install -y build-essential python3-dev ta-lib`
- **macOS**: `brew install ta-lib`

### Step 2: Run Setup Script

Create the virtual environment and install all dependencies:

```bash
python scripts/setup_venv.py
```

This creates a `venv/` directory with isolated Python environment and all required packages.

## Running Analysis

### Option A: Use Convenience Scripts (Recommended)

**Windows (PowerShell):**
```powershell
.\scripts\run.ps1 000001
```

**Windows (Batch):**
```bash
scripts\run.bat 000001
```

**Linux/macOS:**
```bash
chmod +x scripts/run.sh
./scripts/run.sh 000001
```

### Option B: Direct Python Execution

**Windows:**
```bash
venv\Scripts\python.exe scripts\analyze_stock.py 000001
```

**Linux/macOS:**
```bash
venv/bin/python scripts/analyze_stock.py 000001
```

## Example Stock Codes

- `000001` - Ping An Bank (平安银行)
- `600036` - China Merchants Bank (招商银行)
- `603259` - 药明康德
- `000858` - 五粮液

## Execution Instructions

**When invoking this skill from Claude Code:**

Always set the `USER_WORKING_DIR` environment variable to the user's current working directory before running the analysis script. This ensures reports are saved to the user's workspace.

**Example execution pattern:**
```bash
cd C:/Users/CHAOFAN/.claude/skills/stock-analysis
USER_WORKING_DIR={用户当前工作目录} venv/Scripts/python.exe scripts/analyze_stock.py {股票代码}
```

**After generating the analysis:**

1. Read the raw technical data from the script output
2. Generate the comprehensive five-dimensional analysis report in Markdown format
3. **Save the Markdown report** to the user's current working directory with filename: `{code}_{股票名称}_技术分析.md`
4. Inform the user that all reports have been saved to their current directory

## Output Format

Returns comprehensive technical indicator report with:

**Technical indicators included:**
- **Trend**: MA (5, 10, 20, 60), Bollinger Bands
- **Momentum**: MACD, RSI, KDJ, Williams %R, CCI
- **Volume**: OBV, VWMA, volume ratio
- **Volatility**: ATR, historical volatility
- **Money Flow**: Net capital inflow, DMI (+DI, -DI, ADX)

**Files automatically saved to user's current working directory:**
- `stock_report_{code}_{timestamp}.txt` - Plain text report with raw technical data
- `stock_data_{code}_{timestamp}.json` - Full JSON data for further analysis
- `{code}_{股票名称}_技术分析.md` - Markdown format comprehensive analysis report

> **重要**: 所有分析报告都会自动保存到用户当前工作目录，而非技能目录。调用脚本时需通过环境变量 `USER_WORKING_DIR` 传递用户工作目录路径。

## 五维技术分析框架

当用户请求股票分析时，请按以下流程执行：

1. **运行分析脚本**：使用 `USER_WORKING_DIR` 环境变量传递用户工作目录
2. **读取技术数据**：解析脚本输出的原始技术指标数据
3. **生成五维分析**：根据以下五个维度进行综合分析
4. **保存Markdown报告**：将完整的分析报告保存为 `{code}_{股票名称}_技术分析.md` 到用户当前工作目录
5. **确认文件保存**：告知用户所有报告文件已保存到其工作目录

请根据输出的技术数据，从以下五个维度进行综合分析：

### 一、趋势定方向 📈
**核心指标**: MA均线系统、MACD、DMI/ADX

分析要点：
- MA均线的排列形态（多头/空头/粘合）
- 价格相对均线的位置
- MACD的多空状态和动能变化
- ADX反映的趋势强度
- DI+/DI-显示的多空力量对比

### 二、动量找时机 ⚡
**核心指标**: RSI、KDJ、布林带

分析要点：
- RSI显示的超买超卖状态
- KDJ的金叉死叉信号
- 布林带位置反映的强弱
- 乖离率反映的短期超买超卖
- 综合判断当前是否适合介入

### 三、量能验真假 🔍
**核心指标**: 成交量、OBV、量比

分析要点：
- 量比反映的放量缩量情况
- OBV变化反映的资金趋势
- 是否存在量价背离
- 判断当前上涨/下跌的有效性

### 四、资金判持续性 💰
**核心指标**: 主力资金流、超大单

分析要点：
- 当日资金流向（主力、超大单、大单、小单）
- 5日累计资金流向
- 超大单（机构资金）的态度
- 判断资金面是否支撑趋势持续

### 五、波动率控风险 🎯
**核心指标**: ATR、布林带宽度

分析要点：
- ATR反映的波动水平
- 给出具体的止损位建议
- 给出仓位控制建议
- 给出目标位建议

## 分析报告格式

请按以下Markdown格式输出五维分析报告，使用标准Markdown语法（表格、引用、代码块等）：

```markdown
# XXXXXX 股票名称 - 五维技术分析

**当前价格**: XX.XX 元 | **分析日期**: YYYY-MM-DD | **所属行业**: XXXX

---

## 一、趋势定方向 📈

### 📊 核心指标

| 指标 | 数值 | 解读 |
|------|------|------|
| MA排列 | MA5>MA10>... | 多头/空头/粘合 |
| MACD | DIF:XX DEA:XX | 多头/空头动能 |
| ADX/DI | ADX:XX DI+>DI- | 趋势强度/多空力量 |

### 💡 综合分析

[详细分析均线、MACD、DMI等指标的综合表现，判断趋势方向和强度]

**✅ 趋势判断**: [明确看多/偏多/中性/偏空/明确看空]

---

## 二、动量找时机 ⚡

### 📊 核心指标

| 指标 | 数值 | 状态 |
|------|------|------|
| RSI(14) | XX.XX | 超买/健康/超卖 |
| KDJ | K:XX D:XX | 金叉/死叉 |
| 布林带位置 | 上/中/下轨 | 强势/中性/弱势 |

### 💡 综合分析

[分析RSI、KDJ、布林带等指标，判断当前是否适合介入]

**⏰ 时机判断**: [良好时机/观望等待/风险较大]
**📍 建议介入价位**: [具体价格区间]

---

## 三、量能验真假 🔍

### 📊 核心指标

| 指标 | 数值 | 解读 |
|------|------|------|
| 量比 | X.XX | 放量/缩量/正常 |
| OBV 5日 | +XX.XX% | 大幅上升/上升/下降 |
| OBV 20日 | +XX.XX% | 持续流入/变化/流出 |

### 💡 综合分析

[分析量价配合情况，判断上涨/下跌的有效性，检查是否存在背离]

**📈 量能判断**: [量价健康/存在隐忧/背离需谨慎]

---

## 四、资金判持续性 💰

### 💰 当日资金流

| 类型 | 净流入 | 占比 |
|------|--------|------|
| 主力资金 | ±XXXX万元 | ±X.XX% |
| 超大单 | ±XXXX万元 | ±X.XX% |
| 大单 | ±XXXX万元 | ±X.XX% |
| 小单 | ±XXXX万元 | ±X.XX% |

### 💰 5日累计资金流

| 类型 | 累计净流入 | 均值占比 |
|------|-----------|----------|
| 主力资金 | ±XXXX万元 | ±X.XX% |
| 超大单 | ±XXXX万元 | ±X.XX% |

### 💡 综合分析

[分析当日和5日资金流向，判断机构态度和资金面能否支撑趋势持续]

**💎 资金判断**: [资金强劲/支撑有力/分歧加大/持续流出]

---

## 五、波动率控风险 🎯

### 📊 核心指标

| 指标 | 数值 | 等级 |
|------|------|------|
| ATR(14) | X.XXXX元 | 日均波动 |
| ATR比率 | X.XX% | 低/中/高波动 |
| 布林带宽度 | XX.XX% | 收口/适中/扩张 |

### 🛡️ 风险控制建议

- **止损位**: [具体价格，如 MA20/布林下轨]
- **仓位建议**: [建议仓位范围，如 30-40%]
- **目标位**: [目标价格，如 布林上轨/前高]

---

## 综合操作建议

### 📊 综合评级

⭐⭐⭐⭐⭐ (X/5星) - [优秀/良好/一般/较弱]

### 📋 操作策略

#### 稳健型

[详细建议，包括介入价位、止损位、持仓周期等]

#### 激进型

[详细建议，包括试探仓位、加仓条件、目标位等]

### ⚠️ 风险提示

- [风险点1]
- [风险点2]
- [风险点3]

---

> 💡 **免责声明**: 以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎！

---
*报告生成时间: [当前系统时间]*
*数据来源: akshare (中国股票市场)*
*技术指标数据来源：AIShareTxt*
```

**格式要点**：
- 使用标准Markdown标题（# ## ###）
- 使用Markdown表格展示核心指标
- 使用引用块（>）突出免责声明
- 使用分隔线（---）分隔各个维度
- 使用emoji图标增强可读性（📈⚡🔍💰🎯💡⚠️✅）
- 综合评级用星星数量直观展示
- 操作策略使用子标题（####）分类
- 风险提示用无序列表（-）列出

## Environment Structure

```
stock-analysis/
├── venv/                 # Isolated Python environment (created by setup)
├── scripts/
│   ├── setup_venv.py    # Environment setup script
│   ├── run.ps1          # Windows PowerShell convenience wrapper
│   ├── run.bat          # Windows Batch convenience wrapper
│   ├── run.sh           # Linux/macOS convenience wrapper
│   └── analyze_stock.py # Main analysis script
└── requirements.txt      # Python dependencies
```

## Error Handling

- If virtual environment is missing, script returns setup instructions
- If TA-Lib is not installed, script returns installation link
- Invalid stock codes return helpful error messages

## Notes

- Stock codes must be exactly 6 digits
- Data sourced from akshare (Chinese stock market)
- Analysis based on historical OHLCV data
- Reports for reference only, not investment advice
- **All analysis reports are automatically saved to the user's current working directory**
- Report files include: raw data (.txt), JSON data (.json), and Markdown analysis report (.md)
- Remember to set `USER_WORKING_DIR` environment variable when calling the script from Claude Code
