import csv
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any

def generate_combinations(arra, arrb):
    """生成关键词笛卡尔积"""
    return [a + b for a in arra for b in arrb]


def mix_keywords(keywords, is_union=True):
    """
    混合关键词逻辑（AND/OR）
    
    Args:
        keywords: 关键词列表
        is_union: True表示OR逻辑(并集)，False表示AND逻辑(交集)
        
    Returns:
        处理后的关键词列表
    """
    if not is_union:  # AND 逻辑（笛卡尔积）
        result = [""]
        for keyword in keywords:
            if isinstance(keyword, str):
                sub = [keyword]
            else:
                sub = mix_keywords(keyword, is_union)
            result = generate_combinations(result, sub)
        return result
    else:  # OR 逻辑（扁平化）
        result = []
        for keyword in keywords:
            if isinstance(keyword, str):
                result.append(keyword)
            else:
                result.extend(mix_keywords(keyword, is_union))
        return list(set(result))  # 去重


def extract_comment_data(csv_path):
    """
    从CSV文件中提取评论数据
    
    Args:
        csv_path: 评论CSV文件路径
        
    Returns:
        评论数据列表
    """
    comments_data = []
    try:
        with open(csv_path, mode='r', encoding='utf-8-sig') as file:
            csv_reader = csv.reader(file)
            next(csv_reader)  # 跳过表头
            for row in csv_reader:
                comments_data.append(row)
        return comments_data
    except Exception as e:
        print(f"读取评论文件失败: {e}")
        return []


def prepare_full_video_data(video):
    """
    准备完整的视频数据（用于全字段导出）
    
    Args:
        video: 视频数据字典
        
    Returns:
        格式化后的视频完整数据
    """
    video_info = video["video"]
    owner_info = video["owner"]
    pages_info = video.get("pages", [])
    honors_info = video.get("honors", [])
    
    result = {
        # 基本信息
        "bvid": video_info.get("bvid", ""),
        "aid": video_info.get("aid", 0),
        "title": video_info.get("title", ""),
        "cover_url": video_info.get("cover_url", ""),
        
        # 分类信息
        "tid": video_info.get("tid", 0),
        "tname": video_info.get("tname", ""),
        "tid_v2": video_info.get("tid_v2", 0),
        "tname_v2": video_info.get("tname_v2", ""),
        
        # 视频描述
        "description": video_info.get("description", ""),
        "keywords": video_info.get("keywords", ""),
        "dynamic": video_info.get("dynamic", ""),
        
        # 时间信息
        "pubdate": video_info.get("pubdate", ""),
        "ctime": video_info.get("ctime", ""),
        
        # 视频属性
        "duration": video_info.get("duration", 0),
        "videos": video_info.get("videos", 0),
        
        # 版权信息
        "copyright": video_info.get("copyright", 0),
        "no_reprint": video_info.get("no_reprint", False),
        "is_downloadable": video_info.get("is_downloadable", False),
        "autoplay": video_info.get("autoplay", False),
        
        # 统计数据
        "view_count": video_info.get("view_count", 0),
        "danmaku_count": video_info.get("danmaku_count", 0),
        "reply_count": video_info.get("reply_count", 0),
        "favorite_count": video_info.get("favorite_count", 0),
        "coin_count": video_info.get("coin_count", 0),
        "share_count": video_info.get("share_count", 0),
        "like_count": video_info.get("like_count", 0),
        "dislike_count": video_info.get("dislike_count", 0),
        
        # UP主信息
        "owner_mid": video_info.get("owner_mid", 0),
        "owner_name": owner_info.get("name", ""),
        "owner_face": owner_info.get("face_url", ""),
        
        # 分P信息
        "page_count": len(pages_info),
        "page_info": json.dumps(pages_info, ensure_ascii=False) if pages_info else "[]",
        
        # 荣誉信息
        "honors": json.dumps(honors_info, ensure_ascii=False) if honors_info else "[]",
        
        # 其他信息
        "state": video_info.get("state", 0),
        "mission_id": video_info.get("mission_id", 0),
    }
    
    # 处理可能的 NaN 或特殊值
    for key, value in result.items():
        if pd.isna(value) or value == np.nan:
            result[key] = None
            
    return result


def prepare_simple_video_data(video):
    """
    准备简洁版的视频数据（用于简洁输出）
    
    Args:
        video: 视频数据字典
        
    Returns:
        格式化后的视频简洁数据
    """
    video_info = video["video"]
    owner_info = video["owner"]
    
    return {
        "BV号": video_info.get("bvid", ""),
        "标题": video_info.get("title", ""),
        "UP主": owner_info.get("name", ""),
        "分区": f"{video_info.get('tname', '')} ({video_info.get('tid', '')})",
        "播放量": video_info.get("view_count", 0),
        "弹幕数": video_info.get("danmaku_count", 0),
        "收藏": video_info.get("favorite_count", 0),
        "硬币": video_info.get("coin_count", 0),
        "分享": video_info.get("share_count", 0),
        "点赞": video_info.get("like_count", 0),
        "发布时间": video_info.get("pubdate", ""),
        "简介": video_info.get("description", ""),
        "AV号": video_info.get("aid", 0)
    }


def setup_logging(config):
    """
    设置日志记录
    
    Args:
        config: 配置信息
        
    Returns:
        logger对象
    """
    import logging
    log_level = getattr(logging, config.get("log_level", "INFO"))
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("bilibili_crawler.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("bilibili_crawler")