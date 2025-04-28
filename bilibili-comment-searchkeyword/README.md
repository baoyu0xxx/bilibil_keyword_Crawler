# Bilibili视频信息采集工具

## 项目简介
这是一个基于Python的B站视频信息采集工具，可以根据关键词搜索相关视频并获取视频的基本信息。目前支持采集视频标题、UP主信息、播放量、弹幕数等基础数据。

## 功能特性
- 支持关键词搜索视频
- 支持多个关键词的AND/OR逻辑组合查询
- 支持按时间范围筛选视频
- 支持视频标题黑名单过滤
- 自动处理Cookie和请求头，避免被反爬
- 数据导出为Excel格式

## 环境要求
```
Python 3.7+
pandas
aiohttp
beautifulsoup4
tqdm
```

## 使用方法
1. 配置搜索参数（config.py）:
```python
config = {
    "keywords": ["关键词1", "关键词2"],  # 支持多关键词
    "keywords_blacklist": [],  # 标题黑名单
    "is_union": True,  # True为OR逻辑，False为AND逻辑
    "file_path": "./bilibili_search.xlsx",  # 输出文件路径
    "page": 1,  # 每个关键词搜索的页数
    "time_begin": None,  # 起始时间，格式："2024-01-01 00:00:00"
    "time_end": None,  # 结束时间，格式同上
}
```

2. 运行程序：
```bash
python main.py
```

## 项目结构
```
├── main.py              # 主程序入口
├── config.py            # 配置文件
├── bilibili_api.py      # B站API接口封装
├── bil_search_page.py   # 搜索页面解析
└── random_bil_cookie.py # Cookie生成工具
```

## 开发计划
1. **评论区数据采集**
   - 实现视频评论区内容的抓取
   - 支持评论区关键词筛选
   - 评论区数据情感分析

2. **数据存储优化**
   - 将数据存储迁移至SQL数据库
   - 设计合理的数据库结构
   - 实现增量更新机制

3. **采集逻辑优化**
   - 优化信息采集顺序
   - 添加并发控制
   - 完善错误处理机制
   - 添加断点续传功能

## 贡献指南
欢迎提交Issue和Pull Request！

## 免责声明
本工具仅用于学习研究，请勿用于商业用途。使用本工具时请遵守B站相关规定。

## 许可证
[MIT License](https://opensource.org/licenses/MIT)

_注意：本项目仍在开发中，部分功能可能不稳定。_