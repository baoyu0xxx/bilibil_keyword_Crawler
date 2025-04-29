import asyncio
import pandas as pd
from config import config
from bilibili_api import BilibiliAPI
import re

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
async def main(max_page = 20):
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
            "简介": stat["description"]
        })
    
    # 生成Excel
    df = pd.DataFrame(rows)
    try:
        df.to_excel(config["file_path"], index=False)
        print(f"文件已保存至: {config['file_path']}")
    except Exception as e:
        print(f"保存失败: {str(e)}")

if __name__ == "__main__":
    test_maxpage = 1
    asyncio.run(main(max_page = test_maxpage))