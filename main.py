import asyncio
import pandas as pd
from config import config
from bilibili_api import BilibiliAPI
import re
import os
from bil_comment_crawl import start_async as crawl_comments
import csv
import logging
import time
import random
from tqdm import tqdm
import traceback
import sys
import argparse
import json
from typing import List, Dict, Any

# 引入数据库处理模块
try:
    from db_handler import DatabaseHandler
except ImportError:
    print("警告：未找到db_handler模块，数据库功能将不可用。请确保已安装mysql-connector-python库并创建db_handler.py文件。")
    DatabaseHandler = None

# 配置日志
def setup_logging():
    """设置日志记录"""
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


# ------------ 工具函数 ------------
def generate_combinations(arra, arrb):
    """生成关键词笛卡尔积"""
    return [a + b for a in arra for b in arrb]

def mix_keywords(keywords):
    """混合关键词逻辑（AND/OR）"""
    if not config["is_union"]:  # AND 逻辑（笛卡尔积）
        result = [""]
        for keyword in keywords:
            if isinstance(keyword, str):
                sub = [keyword]
            else:
                sub = mix_keywords(keyword)
            result = generate_combinations(result, sub)
        return result
    else:  # OR 逻辑（扁平化）
        result = []
        for keyword in keywords:
            if isinstance(keyword, str):
                result.append(keyword)
            else:
                result.extend(mix_keywords(keyword))
        return list(set(result))  # 去重
    
def extract_comment_data(csv_path):
    """从CSV文件中提取评论数据"""
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
    """准备完整的视频数据（用于全字段导出）"""
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
    """准备简洁版的视频数据（用于简洁输出）"""
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

# ------------ 主流程 ------------
async def main(max_page=20, fetch_details=True, fetch_comments=False, comments_max_page=None,
               output_format=None, output_mode=None, use_database=None):
    # 使用参数覆盖配置
    if output_format is not None:
        config["output_format"] = output_format
    if output_mode is not None:
        config["output_mode"] = output_mode
    if use_database is not None:
        config["use_database"] = use_database
    
    
    api = BilibiliAPI()
    keywords_combined = mix_keywords(config["keywords"])
    print(f"关键词数量: {len(keywords_combined)}, 每关键词页数: {config['page']}")

    # 初始化数据库处理器
    db_handler = None
    if config["use_database"] and DatabaseHandler:
        db_handler = DatabaseHandler(config)
        if not db_handler.connect() or not db_handler.init_database():
            print("数据库初始化失败，将仅保存到文件")
            config["use_database"] = False
    
    # 第一步：获取视频基本信息
    print("\n=== 第一阶段：获取视频基本信息 ===")
    all_videos = []
    actual_pages = min(config.get('page', 1), max_page)
    
    keyword_pbar = tqdm(keywords_combined, desc="关键词进度", position=0)
    for idx, keyword in enumerate(keyword_pbar):
        keyword_pbar.set_description(f"处理关键词 [{idx+1}/{len(keywords_combined)}]: {keyword}")
        pages_list = list(range(1, actual_pages + 1))
        
        try:
            videos_for_keyword = []
            for page in pages_list:
                keyword_pbar.set_postfix({"页面": f"{page}/{actual_pages}"})
                page_videos = await api.search_videos(
                    keyword=keyword,
                    time_begin=config.get("time_begin", None),
                    time_end=config.get("time_end", None),
                    pages=[page] 
                )
                videos_for_keyword.extend(page_videos)
                await asyncio.sleep(random.uniform(0.3, 0.8))
            
            # 数据清洗和黑名单过滤
            filtered = []
            for video in videos_for_keyword:
                title = video["video"]["title"]
                title = re.sub(r"<.*?>", "", title)
                video["video"]["title"] = title
                
                # 黑名单过滤
                if not any(black in title for black in config["keywords_blacklist"]):
                    filtered.append(video)
            
            all_videos.extend(filtered)
            
        except Exception as e:
            print(f"关键词 '{keyword}' 处理失败: {str(e)}")
            traceback.print_exc()
    
    # 去重（基于BV号）
    unique_videos = {}
    for video in all_videos:
        bvid = video["video"]["bvid"]
        if bvid not in unique_videos:
            unique_videos[bvid] = video
    
    basic_results = list(unique_videos.values())
    print(f"基本信息获取完成，去重后共 {len(basic_results)} 个视频")
    
    # 第二步：获取视频详细信息（可选）
    detailed_results = []
    if fetch_details and basic_results:
        print("\n=== 第二阶段：获取视频详细信息 ===")
        
        # 分批处理
        batch_size = 20
        total_batches = (len(basic_results) + batch_size - 1) // batch_size
        
        # 单层进度条显示批次处理进度
        batch_pbar = tqdm(total=total_batches, desc="详细信息批次处理", position=0)
        
        processed_videos = []
        for i in range(total_batches):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, len(basic_results))
            batch = basic_results[start_idx:end_idx]
            
            batch_pbar.set_description(f"批次 {i+1}/{total_batches} ({start_idx+1}-{end_idx}/{len(basic_results)})")
            
            # 获取这一批次的视频详情
            batch_results = await api.get_videos_detail(batch, show_progress=False)  # 在API中禁用进度条
            processed_videos.extend(batch_results)
            
            # 更新进度条
            batch_pbar.update(1)
            
            # 添加批次间的延迟
            if i < total_batches - 1:  # 不是最后一批
                await asyncio.sleep(random.uniform(0.4, 1.2))
        
        batch_pbar.close()
        detailed_results = processed_videos
    else:
        detailed_results = basic_results
    
    # 处理结果并保存到Excel
    print("\n正在处理结果并保存...")
    if config["output_mode"] == "full":
        print("使用全字段输出模式")
        rows = [prepare_full_video_data(video) for video in tqdm(detailed_results, desc="处理数据")]
    else:
        print("使用简洁输出模式")
        rows = [prepare_simple_video_data(video) for video in tqdm(detailed_results, desc="处理数据")]
    
    df = pd.DataFrame(rows)

    file_path = config["file_path"]
    file_base, file_ext = os.path.splitext(file_path)

    if config["output_format"] == "xlsx":
        output_path = f"{file_base}.xlsx" if file_ext != ".xlsx" else file_path
        try:
            df.to_excel(output_path, index=False)
            print(f"数据已保存到Excel文件: {output_path}")
        except Exception as e:
            print(f"保存Excel失败: {str(e)}")
            try:
                csv_path = f"{file_base}.csv"
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                print(f"已备选保存为CSV文件: {csv_path}")
            except Exception as csv_e:
                print(f"保存CSV失败: {str(csv_e)}")
    else:
        # 默认CSV格式
        output_path = f"{file_base}.csv" if file_ext != ".csv" else file_path
        try:
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"数据已保存到CSV文件: {output_path}")
        except Exception as e:
            print(f"保存CSV失败: {str(e)}")
    
    # 如果启用了数据库存储，将数据保存到数据库
    if config["use_database"] and db_handler:
        print("\n=== 将数据保存到MySQL数据库 ===")
        db_handler.insert_videos(detailed_results)
    
    # 第三步：获取视频评论（可选）
    comment_files = []
    if fetch_comments and len(rows) > 0:
        print("\n=== 第三阶段：获取视频评论数据 ===")
        comments_dir = os.path.join(os.path.dirname(output_path), "comments")
        os.makedirs(comments_dir, exist_ok=True)
        
        # 使用单层进度条
        comment_pbar = tqdm(total=len(rows), desc="评论爬取", position=0)
        
        for i, video in enumerate(rows):
            # 获取视频ID - 根据输出模式获取字段
            if config["output_mode"] == "full":
                bvid = video["bvid"]
                aid = video["aid"]
                title_field = "title"
            else:
                bvid = video["BV号"]
                aid = video["AV号"]
                title_field = "标题"
            
            title = video.get(title_field, "未知标题")[:15]  # 标题前15个字符
            comment_pbar.set_description(f"视频 {i+1}/{len(rows)}: {title}...")
            
            # 创建评论CSV文件
            csv_path = os.path.join(comments_dir, f"{bvid}_comments.csv")
            with open(csv_path, mode='w', newline='', encoding='utf-8-sig') as file:
                csv_writer = csv.writer(file)
                csv_writer.writerow(['序号', '上级评论ID', '评论ID', '用户ID', '用户名', '用户等级', 
                                    '性别', '评论内容', '评论时间', '回复数', '点赞数', 
                                    '个性签名', 'IP属地', '是否是大会员', '头像'])
                
                try:
                    count = 0
                    next_pageID = ''
                    is_second = config.get("is_second_comments", False)
                    cookie = None  # 使用默认cookie
                    
                    # 爬取评论
                    await crawl_comments(bvid, aid, next_pageID, count, csv_writer, 
                                is_second, cookie, None, None, 
                                max_page=comments_max_page or config.get("comments_max_page", 5), 
                                page_counter=0)
                    
                    # 保存评论文件路径
                    comment_files.append((bvid, aid, csv_path))
                    
                except Exception as e:
                    print(f"获取评论失败: {str(e)}")
                    traceback.print_exc()
            
            # 更新进度条
            comment_pbar.update(1)
            
            # 添加随机延迟
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        comment_pbar.close()
        
        # 如果需要保存到数据库
        if config["use_database"] and db_handler and comment_files:
            print("\n=== 将评论数据保存到MySQL数据库 ===")
            for bvid, aid, csv_path in tqdm(comment_files, desc="导入评论到数据库"):
                comments_data = extract_comment_data(csv_path)
                if comments_data:
                    db_handler.insert_comments(comments_data, bvid, aid)
    
    # 关闭数据库连接
    if config["use_database"] and db_handler:
        db_handler.close()

    print("\n任务完成!")
    return {
        "video_count": len(detailed_results),
        "output_file": output_path,
        "comment_files": len(comment_files)
    }

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="B站视频爬虫")
    parser.add_argument("--max-page", type=int, default=None, help="最大爬取页数")
    parser.add_argument("--no-details", action="store_true", help="不获取视频详情")
    parser.add_argument("--comments", action="store_true", help="爬取评论")
    parser.add_argument("--comments-max-page", type=int, default=None, help="评论最大页数")
    parser.add_argument("--format", choices=["csv", "xlsx"], default=None, help="输出文件格式")
    parser.add_argument("--output-mode", choices=["simple", "full"], default=None, help="输出模式: simple或full")
    parser.add_argument("--use-db", action="store_true", help="保存到MySQL数据库")
    parser.add_argument("--no-db", action="store_false", dest="use_db", help="不保存到数据库")
    parser.add_argument("--keyword", type=str, default=None, help="搜索关键词，覆盖config中的设置")
    
    args = parser.parse_args()
    
    # 如果指定了关键词，更新配置
    if args.keyword:
        config["keywords"] = [args.keyword]
    
    return args


if __name__ == "__main__":
    args = parse_args()
    
    # 设置默认参数
    max_page = args.max_page if args.max_page is not None else config.get("page", 5)
    fetch_details = not args.no_details
    fetch_comments = args.comments or config.get("fetch_comments", False)
    comments_max_page = args.comments_max_page or config.get("comments_max_page", 5)
    output_format = args.format
    output_mode = args.output_mode
    use_database = args.use_db if args.use_db is not None else config.get("use_database", False)
    
    # 运行主程序
    result = asyncio.run(main(
        max_page=max_page,
        fetch_details=fetch_details,
        fetch_comments=fetch_comments,
        comments_max_page=comments_max_page,
        output_format=output_format,
        output_mode=output_mode,
        use_database=use_database
    ))
    
    print(f"\n任务统计:")
    print(f"- 获取视频数量: {result['video_count']}")
    print(f"- 输出文件: {result['output_file']}")
    print(f"- 评论文件数: {result['comment_files']}")