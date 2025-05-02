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

# ------------ 主流程 ------------
async def main(max_page=20, fetch_details=True, fetch_comments=False, comments_max_page=None):
    api = BilibiliAPI()
    keywords_combined = mix_keywords(config["keywords"])
    print(f"关键词数量: {len(keywords_combined)}, 每关键词页数: {config['page']}")
    
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
                    pages=[page]  # 每次请求一页
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
    print("\n正在处理结果并保存到Excel...")
    rows = []
    for video in tqdm(detailed_results, desc="处理数据", position=0):
        stat = video["video"]
        rows.append({
            "BV号": stat["bvid"],
            "标题": stat["title"],
            "UP主": video["owner"]["name"],
            "分区": f"{stat.get('tname', '')} ({stat.get('tid', '')})",
            "播放量": stat.get("view_count", 0),
            "弹幕数": stat.get("danmaku_count", 0),
            "收藏": stat.get("favorite_count", 0),
            "硬币": stat.get("coin_count", 0),
            "分享": stat.get("share_count", 0),
            "点赞": stat.get("like_count", 0),
            "发布时间": stat.get("pubdate", ""),
            "简介": stat.get("description", ""),
            "AV号": stat.get("aid", 0)
        })
    
    # 保存Excel
    df = pd.DataFrame(rows)
    try:
        df.to_excel(config["file_path"], index=False)
        print(f"文件已保存至: {config['file_path']}")
    except Exception as e:
        print(f"保存失败: {str(e)}")
    
    # 第三步：获取视频评论（可选）
    if fetch_comments and len(rows) > 0:
        print("\n=== 第三阶段：获取视频评论数据 ===")
        comments_dir = os.path.join(os.path.dirname(config["file_path"]), "comments")
        os.makedirs(comments_dir, exist_ok=True)
        
        # 使用单层进度条
        comment_pbar = tqdm(total=len(rows), desc="评论爬取", position=0)
        
        for i, video in enumerate(rows):
            bvid = video["BV号"]
            aid = video["AV号"]
            title = video["标题"]
            
            comment_pbar.set_description(f"视频 {i+1}/{len(rows)}: {title[:15]}...")
            
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
                    is_second = False  # 不爬取二级评论
                    cookie = None  # 使用默认cookie
                    
                    await crawl_comments(bvid, aid, next_pageID, count, csv_writer, 
                                is_second, cookie, None, None, max_page=comments_max_page, page_counter=0)
                    
                except Exception as e:
                    print(f"获取评论失败: {str(e)}")
                    traceback.print_exc()
            
            # 更新进度条
            comment_pbar.update(1)
            
            # 添加随机延迟
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        comment_pbar.close()

if __name__ == "__main__":
    # 默认参数
    test_maxpage = 2
    fetch_details = True  # 是否获取视频详细信息
    fetch_comments = False  # 是否获取评论
    comments_max_page = 3   # 评论最大页数
    
    # 可以从命令行参数或配置文件读取这些参数
    
    asyncio.run(main(
        max_page=test_maxpage,
        fetch_details=fetch_details,
        fetch_comments=fetch_comments,
        comments_max_page=comments_max_page
    ))