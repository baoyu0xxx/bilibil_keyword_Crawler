# Bilibili视频及评论采集工具

## 项目简介

这是一个基于Python的B站视频信息与评论采集工具，可以根据关键词搜索相关视频、获取视频详情信息以及爬取视频评论。采用异步IO技术大幅提升评论爬取效率，支持视频基本信息和评论数据的导出，采用随机Cookie生成技术避免被反爬封禁。支持MySQL数据库存储功能，以及灵活的数据输出配置。新增按天搜索功能，可以获取最近几天内的视频数据。

## 功能特性

- **视频信息采集**
  - 支持关键词搜索视频
  - 支持多个关键词的AND/OR逻辑组合查询
  - 支持按时间范围筛选视频
  - **新增按天搜索功能，可获取最近N天的视频**
  - 支持视频标题黑名单过滤
  - 自动获取视频详情页信息(播放量、点赞数等)

- **评论采集**
  - 支持一级评论和二级评论采集
  - 可控制采集页数和深度
  - 异步高效采集技术

- **反爬与优化**
  - 自动生成随机Cookie和请求头
  - 随机延时请求避免触发频率限制
  - 自动处理请求失败和重试机制
  - 分批次处理请求，控制并发数量
  - 优化的资源管理，防止请求过载
  - 进度条显示采集状态

- **数据导出**
  - 支持多种格式：Excel（xlsx）和CSV
  - 支持简洁模式与全字段模式
  - 支持MySQL数据库存储
  - 评论数据CSV导出（支持UTF-8编码）

## 环境要求

```
Python 3.7+
pandas
aiohttp
requests
beautifulsoup4
tqdm
mysql-connector-python (可选，用于数据库支持)
openpyxl (可选，用于Excel输出)
```

## 安装依赖

```bash
pip install pandas aiohttp requests beautifulsoup4 tqdm mysql-connector-python openpyxl
```

## 使用方法

### 1. 配置参数

编辑 `config.py` 文件配置搜索参数和输出选项:

```python
config = {
    # 基础搜索配置
    "keywords": ["关键词1", "关键词2"],  # 搜索关键词列表，支持多关键词
    "keywords_blacklist": [],  # 标题黑名单
    "is_union": True,  # True为OR逻辑，False为AND逻辑
    "file_path": "./bilibili_search.csv",  # 输出文件路径
    "page": 5,  # 每个关键词搜索的页数
    
    # 输出与数据库设置
    "output_format": "csv",   # 输出格式，支持 "csv", "xlsx"
    "output_mode": "simple",  # 输出模式，"simple"简洁版或"full"全字段版
    "use_database": False,    # 是否使用数据库存储
    
    # 数据库配置 (仅当 use_database=True 时有效)
    "db_config": {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "your_password",
        "database": "bilibili_data",
        "charset": "utf8mb4"
    },
    "db_tables": {
        "videos": "bili_videos",      # 视频信息表名
        "owners": "bili_owners",      # UP主信息表名
        "comments": "bili_comments"   # 评论信息表名
    }
}
```

### 2. 命令行参数

可以通过命令行参数覆盖配置文件中的设置:

```bash
python main.py --keyword "搜索关键词" --max-page 3 --format xlsx --output-mode full --comments --use-db --recent-days 7
```

主要参数:
- `--keyword`: 设置搜索关键词
- `--max-page`: 设置最大页数
- `--format`: 输出格式，可选 "csv" 或 "xlsx"
- `--output-mode`: 输出模式，可选 "simple" 或 "full"
- `--comments`: 启用评论采集
- `--use-db`: 启用数据库存储
- `--no-db`: 禁用数据库存储
- `--no-details`: 不获取视频详情
- `--comments-max-page`: 设置评论最大页数
- `--recent-days`: 设置获取最近几天的数据，启用按天搜索功能

### 3. 数据库设置

如果要使用MySQL数据库存储功能，需要先创建数据库:

```sql
CREATE DATABASE bilibili_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

程序会自动创建所需的表结构。

## 数据输出说明

### 简洁输出模式 (simple)

包含以下字段:
- BV号: 视频的BV号
- 标题: 视频标题
- UP主: UP主名称
- 分区: 视频分区和ID
- 播放量: 播放次数
- 弹幕数: 弹幕数量
- 收藏、硬币、分享、点赞数
- 发布时间
- 简介: 视频简介
- AV号: 视频AV号

### 完整输出模式 (full)

包含所有可获取的字段，包括:
- 基本信息 (BV号、AV号、标题等)
- 分类信息 (分区ID、分区名称等)
- 视频描述、关键词、动态文本
- 时间信息 (发布时间、创建时间)
- 视频属性 (时长、分P数等)
- 版权信息
- 统计数据 (播放量、弹幕数等详细统计)
- UP主详细信息
- 分P信息 (JSON格式)
- 荣誉信息 (JSON格式)

### 数据库表结构

使用数据库存储时，程序会创建以下表:

1. **bili_videos**: 存储视频信息
2. **bili_owners**: 存储UP主信息
3. **bili_comments**: 存储评论数据

## 示例SQL查询

```sql
-- 获取播放量前10的视频
SELECT title, view_count, owner_mid, pubdate
FROM bili_videos
ORDER BY view_count DESC
LIMIT 10;

-- 获取特定UP主的视频统计
SELECT o.name, COUNT(*) as video_count, 
       SUM(v.view_count) as total_views, 
       AVG(v.like_count) as avg_likes
FROM bili_videos v
JOIN bili_owners o ON v.owner_mid = o.mid
GROUP BY v.owner_mid
ORDER BY total_views DESC;

-- 统计评论数量最多的视频
SELECT v.title, COUNT(c.id) as comment_count
FROM bili_videos v
JOIN bili_comments c ON v.bvid = c.bvid
GROUP BY v.bvid
ORDER BY comment_count DESC
LIMIT 10;
```

## 新增功能：按天搜索

### 使用方法

在命令行中使用 `--recent-days` 参数指定要获取的最近天数：

```bash
python main.py --keyword "崩铁" --recent-days 7 --max-page 3 --comments
```

这将分别获取最近7天内每天发布的视频，每天最多搜索3页结果。此功能适合获取时间跨度较大的数据，或按日期观察视频发布趋势。

## 项目结构

```
├── main.py                # 主程序入口
├── config.py              # 配置文件
├── bilibili_api.py        # B站API接口封装
├── bil_search_page.py     # 搜索页面解析
├── bil_comment_crawl.py   # 评论采集模块(异步实现)
├── random_bil_cookie.py   # Cookie生成工具
├── db_handler.py          # 数据库处理模块
└── test_effiency.ipynb    # 效率测试模块
```

## 免责声明

本工具仅用于学习研究，请勿用于商业用途。使用本工具时请遵守B站相关规定和服务条款，不要进行高频次、大规模的数据采集。对因使用本工具造成的任何直接或间接损失，作者不承担任何责任。

## 许可证

[MIT License](https://opensource.org/licenses/MIT)