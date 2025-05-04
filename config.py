config = {
    # 基础搜索配置
    "keywords": ["翁法罗斯"],  # 搜索关键词列表，支持多关键词
    "keywords_blacklist": [],  # 视频标题黑名单，含有这些词的视频将被过滤
    "tids": "",               # 分区ID，空字符串表示全部分区
    "is_union": True,         # True表示OR逻辑(并集)，False表示AND逻辑(交集)
    "file_path": "./bilibili_search.csv",  # 搜索结果保存路径
    "page": 30,               # 每关键词搜索页数(B站限制了搜索页数)
    
    # 时间范围筛选
    "time_begin": None,       # 起始时间，如 "2024-01-01 00:00:00"
    "time_end": None,         # 结束时间，如 "2024-06-01 23:59:59"
    "recent_hot_days": 7,     # 热门视频时间范围(天)，0表示不启用，此设置会覆盖time_begin/time_end
    
    # 评论采集配置
    "fetch_comments": False,  # 是否采集视频评论
    "comments_dir": "./comments",  # 评论保存目录
    "is_second_comments": False,  # 是否采集二级评论
    "comments_max_page": 5,   # 评论最大爬取页数
    "estimated_comments": 5000,  # 评论数量估计(用于进度条)
    
    # 异步爬取配置
    "max_concurrency": 10,    # 最大并发请求数
    "batch_size": 5,          # 批处理大小(每批次请求数)
    "retry_times": 2,         # 请求失败重试次数
    "delay_min": 0.5,         # 请求间隔最小延迟(秒)
    "delay_max": 1.5,         # 请求间隔最大延迟(秒)
    
    # Cookie与请求头配置
    "use_random_cookie": True,  # 是否使用随机Cookie
    "custom_cookie": "",        # 自定义Cookie字符串(当use_random_cookie=False时使用)
    
    # 代理设置(可选)
    "use_proxy": False,       # 是否使用代理
    "proxy_list": [           # 代理列表
        # "http://user:pass@host:port"
    ],
    
    # 输出与日志设置
    "show_progress": True,    # 是否显示进度条
    "verbose": True,          # 是否显示详细信息
    "output_format": "csv",   # 输出格式，支持 "csv", "xlsx"
    "output_mode": "full",  # 输出模式，"simple"简洁版或"full"全字段版
    
    # 高级选项
    "raw_data_dir": "./raw_data",  # 原始数据保存目录
    
    # 数据库配置
    "use_database": True,    # 是否使用数据库存储
    "db_config": {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "@13219488392Bao",
        "database": "bil_crawl_honkai",
        "charset": "utf8mb4"
    },
    "db_tables": {
        "videos": "bili_videos",      # 视频信息表名
        "owners": "bili_owners",      # UP主信息表名
        "comments": "bili_comments"   # 评论信息表名
    }
}