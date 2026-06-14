---
name: ai-frontier-observer
version: "1.0.0"
description: "AI前沿观察 - 追踪 Karpathy、Mollick、Andrew Ng、Jim Fan、Simon Willison 等 AI 实践者的公开分享，输出每日简报到本地文件"
argument-hint: "ai-frontier-observer | /AI前沿观察"
allowed-tools: Bash, Write, WebSearch, WebFetch
user-invocable: true
metadata:
  emoji: "🔭"
  tags:
    - AI
    - research
    - daily-briefing
    - frontier
---

# AI前沿观察 (ai-frontier-observer)

追踪 AI 领域关键实践者的公开分享，输出每日简报。

## 使用方式

直接运行即可执行一次完整扫描并生成当日简报文件。

## 关注名单

| 姓名 | 主要渠道 |
|------|----------|
| **Andrej Karpathy** | X/Twitter (@karpathy)、博客、GitHub |
| **Ethan Mollick** | X/Twitter (@emollick)、Substack "One Useful Thing" |
| **Andrew Ng** | X/Twitter (@AndrewYNg)、DeepLearning.ai The Batch |
| **Jim Fan** | X/Twitter (@jimfan)、NVIDIA/GEAR Lab |
| **Simon Willison** | X/Twitter (@simonw)、simonwillison.net |

## 执行步骤

### 1. 创建输出目录

```bash
mkdir -p /d/AI-前沿观察/
```

### 2. 获取当天日期

```bash
date +%Y-%m-%d
```

### 3. 搜索各渠道最新内容

对每位关注者执行 WebSearch 搜索最近 1-2 天的公开分享：

- `"Andrej Karpathy" latest`
- `"Ethan Mollick" "One Useful Thing"`
- `"Andrew Ng" latest`
- `"Jim Fan" AI research`
- `"Simon Willison" blog LLM`

同时 Fetch 博客源获取最新文章列表：
- `https://simonwillison.net/2026/` — Simon Willison
- `https://www.oneusefulthing.org/archive` — Ethan Mollick
- `https://deeplearning.ai/the-batch/` — Andrew Ng
- `https://karpathy.bearblog.dev/` — Karpathy

### 4. 整理并写入文件

将结果写入 `/d/AI-前沿观察/<日期>.md`，Markdown 格式，包含以下章节：

```markdown
# AI前沿观察 - YYYY年MM月DD日

## 1. Andrej Karpathy
- 今日分享的核心观点
- 技术实践或项目进展
- 相关链接

## 2. Ethan Mollick
- 今日文章/帖子核心观点
- AI 应用实践洞察
- 相关链接

## 3. Andrew Ng
- 今日分享的核心观点
- 学习资源/课程动态
- 相关链接

## 4. Jim Fan
- 今日分享的核心观点
- 研究/项目动态
- 相关链接

## 5. Simon Willison
- 今日分享的核心观点
- 技术实践（LLM 应用、工具链等）
- 相关链接

## 6. 今日要闻速览
- AI 领域其他值得关注的实践趋势（如有）

## 7. 我的思考
- 这些信息对保持 AI 实践敏感度的启发
```

### 5. 搜索原则

- 如果某位今日无更新 → 注明"今日无新公开分享"
- 重点关注有实践参考价值的内容，而非纯新闻
- 内容要精炼，便于快速阅读

## 输出示例

输出文件路径：`D:\AI-前沿观察\2026-06-14.md`

文件使用 UTF-8 编码，每个关注者一个区块，末尾附加今日要闻和个人思考。
