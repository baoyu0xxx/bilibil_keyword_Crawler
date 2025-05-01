import asyncio
import pandas as pd
from config import config
from bilibili_api import BilibiliAPI
import re
import os
from bil_comment_crawl import start as crawl_comments
import csv

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
async def main(max_page=20, fetch_comments=False, comments_max_page=None):
    api = BilibiliAPI()
    keywords_combined = mix_keywords(config["keywords"])
    print(f"关键词数量: {len(keywords_combined)}, 每关键词页数: {config['page']}")
    
    all_results = []
    actual_pages = min(config.get('page', 1), max_page)
    # 遍历关键词和页数
    for idx, keyword in enumerate(keywords_combined, 1):
        print(f"处理关键词 [{idx}/{len(keywords_combined)}]: {keyword}")
        for page in range(1, actual_pages + 1):
            try:
                # 第 ？ 页 / 共 ？ 页/ 关键词
                print(f"关键词 '{keyword}' 第 {page} 页 / 共 {actual_pages} 页")
                # 调用BilibiliAPI的搜索方法
                results = await api.search_and_get_video_info(
                    keyword=keyword,
                    time_begin=config.get("time_begin", None),
                    time_end=config.get("time_end", None),
                    page=page
                )
                
                # 数据清洗和黑名单过滤
                filtered = []
                for video in results:
                    # 清洗标题中的HTML标签
                    title = video["video"]["title"]
                    title = re.sub(r"<.*?>", "", title)
                    video["video"]["title"] = title
                    
                    # 黑名单过滤
                    if not any(black in title for black in config["keywords_blacklist"]):
                        filtered.append(video)
                
                all_results.extend(filtered)
                
            except Exception as e:
                print(f"关键词 '{keyword}' 第 {page} 页失败: {str(e)}")
                continue
    
    # 去重（基于BV号）
    unique_videos = {}
    for video in all_results:
        bvid = video["video"]["bvid"]
        if bvid not in unique_videos:
            unique_videos[bvid] = video
    print(f"去重后视频数: {len(unique_videos)}")
    
    # 提取需要导出的字段
    rows = []
    for video in unique_videos.values():
        stat = video["video"]
        rows.append({
            "BV号": stat["bvid"],
            "标题": stat["title"],
            "UP主": video["owner"]["name"],
            "分区": f"{stat['tname']} ({stat['tid']})",
            "播放量": stat["view_count"],
            "弹幕数": stat["danmaku_count"],
            "收藏": stat["favorite_count"],
            "硬币": stat["coin_count"],
            "分享": stat["share_count"],
            "点赞": stat["like_count"],
            "发布时间": stat["pubdate"],
            "简介": stat["description"],
            "AV号": stat["aid"]  # 添加AV号，用于评论爬取
        })
    
    # 生成Excel
    df = pd.DataFrame(rows)
    try:
        df.to_excel(config["file_path"], index=False)
        print(f"文件已保存至: {config['file_path']}")
    except Exception as e:
        print(f"保存失败: {str(e)}")
    
    # 如果需要获取评论
    if fetch_comments and len(rows) > 0:
        print(f"\n开始获取视频评论数据，共 {len(rows)} 个视频")
        comments_dir = os.path.join(os.path.dirname(config["file_path"]), "comments")
        os.makedirs(comments_dir, exist_ok=True)
        
        for i, video in enumerate(rows):
            bvid = video["BV号"]
            aid = video["AV号"]
            title = video["标题"]
            
            print(f"\n[{i+1}/{len(rows)}] 正在获取视频评论: {title} (BV: {bvid})")
            
            # 创建评论CSV文件
            csv_path = os.path.join(comments_dir, f"{bvid}_comments.csv")
            with open(csv_path, mode='w', newline='', encoding='utf-8-sig') as file:
                csv_writer = csv.writer(file)
                csv_writer.writerow(['序号', '上级评论ID', '评论ID', '用户ID', '用户名', '用户等级', 
                                      '性别', '评论内容', '评论时间', '回复数', '点赞数', 
                                      '个性签名', 'IP属地', '是否是大会员', '头像'])
                
                try:
                    # 调用评论爬取函数
                    count = 0
                    next_pageID = ''
                    is_second = False  # 不爬取二级评论
                    cookie = None  # 使用默认cookie
                    
                    crawl_comments(bvid, aid, next_pageID, count, csv_writer, 
                                 is_second, cookie, None, None, max_page=comments_max_page, page_counter=0)
                    
                    print(f"评论已保存至: {csv_path}")
                except Exception as e:
                    print(f"获取评论失败: {str(e)}")

if __name__ == "__main__":
    # 默认参数
    test_maxpage = 1
    fetch_comments = False  # 是否获取评论
    comments_max_page = 3   # 评论最大页数
    
    # 可以从命令行参数或配置文件读取这些参数
    # 这里为了示例，直接设置参数
    if config.get("fetch_comments", False):
        fetch_comments = True
        comments_max_page = config.get("comments_max_page", 3)
    
    asyncio.run(main(
        max_page=test_maxpage,
        fetch_comments=fetch_comments,
        comments_max_page=comments_max_page
    ))