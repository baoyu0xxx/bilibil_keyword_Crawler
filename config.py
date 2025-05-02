config = {
    # 基础搜索配置
    "keywords": ["翁法罗斯"],  # 搜索关键词列表，支持多关键词
    "keywords_blacklist": [],  # 视频标题黑名单，含有这些词的视频将被过滤
    "tids": "",               # 分区ID，空字符串表示全部分区
    "is_union": True,         # True表示OR逻辑(并集)，False表示AND逻辑(交集)
    "file_path": "./bilibili_search.xlsx",  # 搜索结果保存路径
    "page": 5,               # 每关键词搜索页数(B站限制了搜索页数)
    
    # 时间范围筛选
    "time_begin": None,       # 起始时间，如 "2024-01-01 00:00:00"
    "time_end": None,         # 结束时间，如 "2024-06-01 23:59:59"
    
    # 评论采集配置
    "fetch_comments": False,  # 是否采集视频评论
    "comments_dir": "./comments",  # 评论保存目录
    "is_second_comments": False,  # 是否采集二级评论
    "comments_max_page": 5,   # 评论最大爬取页数
    "estimated_comments": 5000,  # 评论数量估计(用于进度条)
    
    # 异步爬取配置
    "max_concurrency": 10,    # 最大并发请求数
    "batch_size": 5,          # 批处理大小(每批次请求数)
    "retry_times": 3,         # 请求失败重试次数
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
    
    # 高级选项
    "raw_data_dir": "./raw_data",  # 原始数据保存目录
}