# Claude Code Skills Collection

这是一个用于 Claude Code 的技能包集合仓库。

## 技能列表

### celery-task
异步任务派发和管理技能，支持跨平台部署（Windows/Linux/macOS）：

- **任务队列** - 基于 Celery + Redis 的分布式任务队列
- **延时调度** - 支持延时执行和定时任务（eta 参数）
- **服务管理** - 自动检查并启动 Redis/Memurai、Celery Worker、Flower 监控
- **命令执行** - 异步执行 shell 命令或 Python 脚本
- **任务监控** - Flower Web 界面实时查看任务状态
- **通知推送** - 集成 ntfy 推送任务完成通知

### stock-analysis
中国A股技术分析技能，提供五维技术分析框架：

- **趋势定方向** - MA均线系统、MACD、DMI/ADX
- **动量找时机** - RSI、KDJ、布林带
- **量能验真假** - 成交量、OBV、量比
- **资金判持续性** - 主力资金流、超大单
- **波动率控风险** - ATR、布林带宽度

支持生成 Markdown 格式的综合分析报告。

## 使用方法

1. 将技能文件夹复制到 `C:\Users\{用户名}\.claude\skills\` 目录
2. 重启 Claude Code
3. 通过 `/技能名` 命令调用对应技能

## 仓库地址

https://github.com/chaofanat/skills

## 更新日志

- 2025-02-17: 添加 celery-task 技能
- 2025-02-05: 添加 stock-analysis 技能
