# 内容服务配置指南（场景 4.1 & 4.2）

## 概述

场景 4（情感陪伴场景）包含两个核心功能：
- **4.1 音乐与内容推荐**：根据用户情绪推荐音乐
- **4.2 新闻与资讯推送**：根据用户兴趣推送新闻

## 场景 4.1：音乐与内容推荐

### 功能描述

系统会根据用户的情绪状态推荐合适的音乐，提供情感陪伴。

### 支持的情绪类型

- `happy`（开心）：推荐流行、舞曲、电子音乐
- `sad`（难过）：推荐抒情、原声、独立音乐
- `relaxed`（放松）：推荐氛围、古典、爵士音乐
- `energetic`（精力充沛）：推荐摇滚、嘻哈、电音
- `tired`（疲惫）：推荐 Lo-fi、氛围、古典音乐
- `focused`（专注）：推荐器乐、Lo-fi、古典音乐
- `anxious`（焦虑）：推荐氛围、冥想、自然音

### 使用方式

#### 1. 初始化音乐推荐器

```python
from mcp_manager import get_mcp_manager

mcp = get_mcp_manager()
mcp.setup_music_recommender()
```

#### 2. 手动推荐音乐

```python
# 根据情绪推荐
recommendations = mcp.recommend_music_by_mood("happy")

for rec in recommendations:
    print(f"{rec.title} - {rec.artist}")
    print(f"推荐理由: {rec.reason}")
```

#### 3. 带用户偏好的推荐

```python
# 考虑用户喜欢的艺术家
recommendations = mcp.recommend_music_by_mood(
    "relaxed", 
    user_preferences=["周杰伦", "Yiruma"]
)
```

#### 4. 对话触发（自动）

用户可以通过对话触发音乐推荐：

**用户**："推荐一首歌"  
**Animus**："你看起来有点累，要不要听首轻松的歌？我推荐 River Flows in You - Yiruma（适合放松的心情）"

**用户**："我想听歌"  
**Animus**："你心情不错，要不要听首欢快的歌？我推荐 晴天 - 周杰伦（适合happy的心情，你喜欢的艺术家）"

### 情绪检测机制

系统会从对话历史中自动推断用户情绪：

- **关键词匹配**：检测"开心"、"累"、"难过"等情绪词
- **表情符号**：识别 😊、😢、😴 等表情
- **上下文分析**：结合最近3轮对话判断情绪

### 扩展音乐库

可以扩展本地音乐库或集成外部 API：

```python
# 在 content_providers.py 中添加音乐
recommender.local_music_library.append({
    "title": "歌曲名",
    "artist": "艺术家",
    "genre": "pop",
    "mood": "happy"
})
```

### 集成 Spotify/Apple Music（未来）

未来可以集成外部音乐服务：

```python
# 示例：Spotify API 集成
# 需要 OAuth 授权和 API Key
# mcp.setup_spotify_api(client_id, client_secret)
# recommendations = mcp.get_spotify_recommendations(mood="happy")
```

---

## 场景 4.2：新闻与资讯推送

### 功能描述

系统会根据用户兴趣聚合新闻，并在适当时机推送相关资讯。

### 支持的新闻分类

- `tech`（科技）：科技新闻、创业资讯
- `general`（综合）：时事新闻
- `science`（科学）：科学资讯、科普内容

### 使用方式

#### 1. 初始化新闻聚合器

```python
from mcp_manager import get_mcp_manager

mcp = get_mcp_manager()

# 设置用户兴趣
user_interests = ["AI", "科技", "机器学习"]
mcp.setup_news_aggregator(user_interests)
```

#### 2. 添加自定义 RSS 源

```python
# 添加科技类 RSS 源
mcp.add_news_feed("tech", "https://www.36kr.com/feed")
mcp.add_news_feed("tech", "https://sspai.com/feed")

# 添加科学类 RSS 源
mcp.add_news_feed("science", "https://www.guokr.com/rss/")
```

#### 3. 手动获取新闻

```python
# 获取科技新闻
news_items = mcp.get_news(category="tech", max_items=5)

for news in news_items:
    print(f"{news.title} - {news.source}")
    print(f"发布时间: {news.published_date}")
    print(f"相关性评分: {news.relevance_score}")
```

#### 4. 每日新闻摘要

```python
# 获取最相关的新闻摘要
news_aggregator = mcp.news_aggregator
daily_news = news_aggregator.get_daily_digest(max_items=3)
```

#### 5. 对话触发（自动）

用户可以通过对话触发新闻推送：

**用户**："今天有什么新闻？"  
**Animus**："今天有一些你可能感兴趣的新闻：
- AI 技术的最新进展 (科技日报)
- 机器学习在医疗领域的应用 (36氪)
- GPT-5 发布在即 (少数派)"

**用户**："最近有什么科技资讯？"  
**Animus**："最近科技圈挺热闹的！我看到几条你可能感兴趣的：..."

### 自动推送机制

系统会每24小时自动推送一次新闻：

- **触发时机**：定时检查（每2.5分钟）
- **推送条件**：距离上次推送超过24小时
- **推送内容**：最相关的3条新闻
- **推送语气**：符合"猫"的性格，温柔贴心

**示例推送**：
"今天有一些你可能感兴趣的新闻：
- AI 技术的最新进展
- 机器学习在医疗领域的应用"

### 相关性评分机制

系统会根据用户兴趣计算新闻相关性：

1. **关键词匹配**：检测新闻标题和摘要中是否包含用户兴趣关键词
2. **评分规则**：每匹配一个关键词 +0.3 分（最高 1.0）
3. **排序**：按相关性评分降序排列

### 推荐的 RSS 源

#### 中文科技新闻

- 36氪：`https://www.36kr.com/feed`
- 少数派：`https://sspai.com/feed`
- 果壳网：`https://www.guokr.com/rss/`
- 虎嗅网：`https://www.huxiu.com/rss/0.xml`
- 爱范儿：`https://www.ifanr.com/feed`

#### 综合新闻

- 人民网：`http://www.people.com.cn/rss/politics.xml`
- 新华网：`http://www.xinhuanet.com/politics/news_politics.xml`

#### 国际科技新闻（英文）

- TechCrunch：`https://techcrunch.com/feed/`
- The Verge：`https://www.theverge.com/rss/index.xml`
- Ars Technica：`https://feeds.arstechnica.com/arstechnica/index`

### 隐私与安全

- **只读取公开 RSS 源**：不需要用户授权
- **无个人信息收集**：只基于用户主动设置的兴趣
- **本地处理**：所有推荐逻辑在本地运行

---

## 集成到系统

### 在 `mcp_setup.py` 中配置

```python
import asyncio
from mcp_manager import get_mcp_manager

async def setup_content_services():
    mcp = get_mcp_manager()
    
    # 初始化音乐推荐器
    mcp.setup_music_recommender()
    
    # 初始化新闻聚合器
    user_interests = ["AI", "科技", "机器学习"]
    mcp.setup_news_aggregator(user_interests)
    
    # 添加自定义新闻源
    mcp.add_news_feed("tech", "https://www.36kr.com/feed")
    mcp.add_news_feed("science", "https://www.guokr.com/rss/")
    
    print("✅ 内容服务配置完成")

asyncio.run(setup_content_services())
```

### 在对话中自动触发

系统会在 `reasoning_node` 中自动检测音乐和新闻请求：

- **音乐请求关键词**：推荐、听歌、音乐、放首歌、来首歌、想听
- **新闻请求关键词**：新闻、资讯、今天有什么、最近发生、热点

当检测到这些关键词时，系统会自动调用相应的服务并将结果注入到 LLM 的上下文中。

---

## 测试

### 运行单元测试

```bash
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:.
pytest tests/unit/test_content_providers.py -v
```

### 手动测试

```python
from content_providers import create_music_recommender, create_news_aggregator

# 测试音乐推荐
music = create_music_recommender()
recs = music.recommend_by_mood("happy")
for r in recs:
    print(f"{r.title} - {r.artist}")

# 测试新闻聚合
news = create_news_aggregator()
news.set_user_interests(["AI", "科技"])
items = news.fetch_news(category="tech", max_items=3)
for n in items:
    print(f"{n.title} - {n.source}")
```

---

## 偏好学习机制（已实现）

### 自动学习用户偏好

系统会自动从对话中学习用户的音乐和新闻偏好，并保存到记忆系统中。

#### 音乐偏好学习

**正面反馈示例**：
- 用户："这首歌真好听，我喜欢周杰伦的歌"
- 系统：保存偏好 "用户喜欢周杰伦的音乐" → 后续推荐会优先考虑周杰伦

**负面反馈示例**：
- 用户："我不喜欢这种类型的音乐，太吵了"
- 系统：保存偏好 "用户不喜欢摇滚类型的音乐" → 后续推荐会过滤掉摇滚音乐

**自动检测**：
- 系统会检测对话中的关键词（喜欢、不喜欢、好听、难听等）
- 自动提取艺术家名称和音乐类型
- 保存到记忆系统，置信度 > 0.6 才保存

#### 新闻偏好学习

**正面反馈示例**：
- 用户："我对AI和科技类的新闻很感兴趣"
- 系统：保存偏好 "用户对AI、科技相关的新闻感兴趣" → 后续推送会优先AI和科技新闻

**负面反馈示例**：
- 用户："我不喜欢看娱乐新闻，别推给我"
- 系统：保存偏好 "用户对娱乐相关的新闻不感兴趣" → 后续推送会过滤娱乐新闻

#### 偏好应用

**音乐推荐**：
- 系统会从记忆中读取用户喜欢的艺术家和类型
- 优先推荐用户喜欢的音乐
- 自动过滤掉用户不喜欢的类型

**新闻推送**：
- 系统会从记忆中读取用户感兴趣的主题
- 计算新闻相关性时，用户感兴趣的主题会获得更高评分
- 自动过滤掉用户不感兴趣的主题

#### 偏好持久化

- 所有偏好都保存在向量数据库（ChromaDB）中
- 分类为 `music` 或 `news`
- 包含情感标签（positive/negative）
- 支持元数据（艺术家、类型、主题等）

---

## 未来扩展

### 场景 4.1 扩展

1. **集成 Spotify API**：支持真实的音乐播放控制
2. **集成 Apple Music API**：支持 iOS 生态
3. **情感分析模型**：使用深度学习模型更准确地识别情绪
4. **偏好学习优化**：使用更复杂的NLP模型提取偏好信息

### 场景 4.2 扩展

1. **深度学习推荐**：使用 NLP 模型提取新闻主题和关键词
2. **多语言支持**：支持英文、日文等多语言新闻源
3. **时间敏感推送**：根据新闻时效性调整推送优先级
4. **用户反馈学习**：根据用户点击和阅读行为优化推荐

---

**文档版本**：v1.0  
**最后更新**：2025-01-04  
**维护者**：Project Animus 开发团队

