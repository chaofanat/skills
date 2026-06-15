# CDP 搜索策略与反爬应对

本文件总结 CDP 数据采集的实操经验，明确搜索引擎可靠性、降级顺序和直连 URL 优先级。**核心原则：目标网站直连 > 搜索引擎**。

---

## 一、搜索引擎可靠性表（实测，2026-06-15）

| 搜索源 | 反爬触发条件 | 表现 | 国内可用性 | 评分 |
|--------|------------|------|-----------|------|
| **百度** baidu.com | **极易**触发图形验证码（tuxing_v2） | 中等频率查询即跳转验证码页面 | 直连 | ⭐ |
| **Bing 国内版** cn.bing.com | 较少触发反爬，但 DOM 结构不稳定 | `.b_algo` 选择器经常返回空，需用 `body.innerText` 整体提取 | 直连 | ⭐⭐⭐ |
| **Google** google.com | 高频查询触发 reCAPTCHA，阈值比百度宽 | 触发概率低 | **需代理**（CDP 浏览器是否走代理取决于启动参数） | ⭐⭐⭐⭐ |
| **360 搜索** so.com | 中等 | DOM 较稳定 | 直连 | ⭐⭐ |
| **搜狗** sogou.com | 中等 | 微信文章搜索可补充 | 直连 | ⭐⭐ |
| **WebSearch MCP 工具** | API 配额（每周/每月） | 429 错误，配额耗尽后不可用直至重置 | 直连 | ⭐⭐⭐⭐（配额内最优） |

**实测要点**：
- 百度对**重复查询 + 特定金融关键词**组合特别敏感，第二次或第三次搜索就可能跳验证码
- Bing 国内版不报错但 DOM 抓取经常失败，需要 fallback 到 `body.innerText` 整体扫描
- Google 国内不能直连；先 `proxy` 开代理后再访问
- WebSearch MCP 工具最稳定但有配额，建议留给"必须搜索引擎"的场景（如历史相似案例）

---

## 二、采集优先级（核心策略）

```
1. gmapi 硬数据（数值型，必查）
   ↓ 失败/不覆盖
2. 目标网站直连（公告/新闻/行业数据）
   ↓ 仍无法满足
3. WebSearch MCP 工具（配额内最优）
   ↓ 配额耗尽
4. CDP 搜索引擎（按可靠性表降级）
   Bing > 360/搜狗 > 百度 > Google（需代理）
```

**禁止行为**：
- ❌ 第一步就打开搜索引擎（除历史相似案例外，trend-verify 的数据都有明确目标站点）
- ❌ 搜索引擎单一失败后放弃（必须按降级顺序换源）
- ❌ 抓取 DOM 选择器失败后直接判定"未发现"（必须 fallback 到 `body.innerText`）

---

## 三、反爬触发应对清单

### 1. 百度图形验证码（tuxing_v2）

**症状**：URL 跳转至 `wappass.baidu.com/static/captcha/tuxing_v2.html`，页面要求识别图形

**应对**：
- 立即停止用百度，切换到 Bing 或 360
- 如果必须用百度：换关键词组合、降低查询频率、间隔 30 秒以上
- 不要尝试 solve 验证码（自动化破解违反 ToS）

### 2. Bing 国内版 DOM 抓取为空

**症状**：`document.querySelectorAll('.b_algo')` 返回 0 个元素，但页面肉眼可见有结果

**应对**：fallback 到整体文本提取
```javascript
() => {
  const text = document.body.innerText;
  return text.substring(0, 4000);  // 截前 4000 字符
}
```
然后用关键词匹配从文本中切出标题+摘要。

### 3. WebSearch 工具 429 错误

**症状**：返回 `MCP error -429: Weekly/Monthly Limit Exhausted`

**应对**：
- 切换到 CDP 搜索引擎（按可靠性表）
- 优先用 CDP 直连目标站点（如生意社、东财）替代搜索引擎
- 记录到报告中"WebSearch 配额耗尽，使用 CDP 直连替代"

### 4. 巨潮公告详情页是 PDF

**症状**：访问 `cninfo.com.cn/new/disclosure/detail?...` 后页面只有标题，正文需 PDF 下载

**应对**：改用东方财富公告详情页，有完整文本：
```
http://data.eastmoney.com/notices/detail/{code}/{AN编号}.html
```
- AN 编号可通过东财公告搜索页 (`so.eastmoney.com/ann/s?keyword=...`) 获取
- 东财页面 `body.innerText` 包含完整公告正文

### 5. 卓创资讯需要登录

**症状**：sci99.com 部分深度内容需付费会员

**应对**：
- 切换到生意社 (100ppi.com)，免费可达
- 或用东方财富研报/新闻作为辅助
- 报告中记录"卓创需登录，使用生意社替代"

### 6. CDP 浏览器无法访问 Google

**症状**：访问 google.com 超时或连接失败

**应对**：
- 终端执行 `proxy` 命令开启代理（用户预定义命令）
- 确认 CDP 浏览器进程是否使用系统代理（启动参数决定）
- 若 CDP 不走代理：放弃 Google，用 Bing/360 或 WebSearch 工具

---

## 四、目标网站直连 URL 清单

按检查项分类的"首选直连 URL"，避免每次都走搜索引擎。

### Layer 1.1 公司确认/否认

| 数据 | 直连 URL | 说明 |
|------|---------|------|
| 公司最新公告列表 | `http://www.cninfo.com.cn/new/disclosure/stock?stockCode={code}&orgId={orgId}` | orgId 格式：沪市 `gssh0{code}`，深市 `gssz0{code}` |
| **公告正文文本**（推荐） | `http://data.eastmoney.com/notices/detail/{code}/{AN编号}.html` | **PDF 替代方案**，body.innerText 直接含正文 |
| 公告搜索 | `https://so.eastmoney.com/ann/s?keyword={code}+{名称}+{关键词}` | 用于找 AN 编号 |

### Layer 1.2b 板块逻辑验证

| 行业 | 直连 URL | 关键路径 |
|------|---------|---------|
| 化工（首选） | `https://www.100ppi.com/bai/list-70.html` | 化工榜 + 黄磷/磷酸等品种动态 |
| 化工（备选） | `https://www.100ppi.com/` 首页 | 滚动新闻含每日价格变动 |
| 化工（深度） | `https://www.sci99.com/` | 卓创需登录，免费内容有限 |
| 有色金属 | `https://www.smm.cn/{品种}` | SMM 价格页面 |
| 钢铁 | `https://www.mysteel.com/` | 我的钢铁网 |
| 综合 | `https://www.100ppi.com/bai/list-{id}.html` | list-70=化工，list-10=能源等 |

**生意社分榜 ID 参考**（用于直接访问，避免从首页导航）：
- 能源：list-10
- 化工：list-70
- 橡塑：list-80
- 纺织：list-90
- 有色：list-40
- 钢铁：list-20
- 建材：list-30
- 农副：list-50

### Layer 3.2 监管风险

| 数据 | 直连 URL | 说明 |
|------|---------|------|
| 上交所监管函 | `https://www.sse.com.cn/disclosure/listingsinfo/regulatory/` | 上交所官网监管栏目 |
| 深交所监管函 | `https://www.szse.cn/disclosure/listed/notice/index.html` | 深交所官网 |
| 个股公告（含问询函） | 巨潮个股披露页（同 1.1） | 问询函通常作为公司公告发布 |

**优先级**：先用巨潮个股披露页搜索"问询/关注/停牌"关键词，比搜索引擎更精准。

### 东方财富综合信息入口

| 数据 | 直连 URL |
|------|---------|
| 个股新闻 | `https://so.eastmoney.com/news/s?keyword={code}+{名称}` |
| 个股公告 | `https://data.eastmoney.com/notices/stock/{code}.html` |
| 个股龙虎榜 | `https://data.eastmoney.com/stock/lhb/{code}.html` |
| 个股资金流 | `https://data.eastmoney.com/zjlx/{code}.html` |
| 个股综合（含题材/研报/股东） | `https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={SH\|SZ}{code}` |

**实操技巧**：东方财富个股公告详情页（`data.eastmoney.com/notices/detail/...`）页面侧边栏同时显示：龙虎榜、股东研究、研报、十大股东、核心题材 — 一次访问可覆盖多项数据需求。

---

## 五、CDP evaluate_script 实用模板

### 整体文本提取（DOM 选择器失败时 fallback）

```javascript
() => {
  const text = document.body.innerText;
  return text.substring(0, 5000);
}
```

### 关键词扫描（按行匹配）

```javascript
() => {
  const keywords = ['化工', '磷', '草甘膦', '上涨', '下跌'];
  const lines = document.body.innerText.split('\n');
  const matched = [];
  lines.forEach(line => {
    if (line.trim() && keywords.some(k => line.includes(k))) {
      matched.push(line.trim().substring(0, 200));
    }
  });
  return { total: lines.length, matched: matched.slice(0, 30) };
}
```

### 搜索结果批量提取（Bing 失败时 fallback）

```javascript
() => {
  const results = [];
  // Bing 主要选择器
  document.querySelectorAll('.b_algo, .b_caption, [data-annotator-class="result"]').forEach((r, i) => {
    if (i < 10) {
      const title = r.querySelector('h2, h3, .b_focusTextLarge')?.innerText || '';
      const snippet = r.querySelector('p, .b_caption p')?.innerText.substring(0, 300) || '';
      if (title || snippet) results.push({ title, snippet });
    }
  });
  // Fallback: 整体文本
  if (results.length === 0) {
    return { fallback: true, text: document.body.innerText.substring(0, 3000) };
  }
  return { count: results.length, results };
}
```

---

## 六、报告中的搜索穷尽声明模板

当搜索引擎受限时，报告中应明确记录：

```markdown
**搜索穷尽说明**：
- WebSearch 工具因配额耗尽（429错误）无法使用，但通过 CDP 直接访问{目标站点}获取了关键数据
- {行业平台} 因 {原因} 未深入，但 {替代平台} 数据已覆盖关键{品种/数据点}
- {搜索引擎} 搜索通过 CDP 执行（{N}条结果，{具体情况}）
```

**目的**：使搜索过程透明，避免"未发现"被误判为"未搜索"。

---

## 相关文件

- `references/data_sources.md` — 数据源 URL 目录（基础清单）
- `templates/verification_checklist.md` — 检查项映射
- 本文件 (`references/cdp_search_strategy.md`) — CDP 实操经验与策略
