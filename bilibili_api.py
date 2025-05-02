import aiohttp
import asyncio
import json
import time
import re
from urllib.parse import urlencode, quote
from bs4 import BeautifulSoup
from bil_search_page import bil_search_page
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import random
import random_bil_cookie
from tqdm import tqdm


class BilibiliAPI:
    def __init__(self, search_host = "search.bilibili.com"):
        self.search_host = search_host
        self.api_host = "api.bilibili.com"
        self.main_host = "www.bilibili.com"
        self.api_prefix = "/x"
        self.cookie = random_bil_cookie.get_random_cookies(scene='search',timestamp=int(time.time()))

    async def _get_html(self, url, referer="https://www.bilibili.com",cookie=None) -> str:
        """获取网页 HTML 内容"""
        headers = {
            'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(120, 135)}.0.0.0 Safari/537.36 Edg/{random.randint(120, 135)}.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-TW;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Microsoft Edge";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Cache-Control': 'max-age=0',
            'Referer': referer,
            'Priority': 'u=0, i',
        }

        # 添加随机Cookie
        if cookie is None:
            cookie = self.cookie
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, cookies=cookie) as response:
                if response.status != 200:
                    raise Exception(f"HTTP Error: {response.status}")
                return await response.text()
    
    async def search_videos(self, keyword, time_begin=None, time_end=None, pages=None) -> List[Dict]:
        """
        搜索视频获取基本信息，支持多页同时搜索
        
        参数:
            keyword: 关键词
            time_begin: 开始时间
            time_end: 结束时间
            pages: 页码列表，默认为[1]
        
        返回:
            包含基本视频信息的字典列表
        """
        if pages is None:
            pages = [1]
        elif isinstance(pages, int):
            pages = [pages]
            
        all_video_data = []
        
        for page in pages:
            # 构建搜索URL
            encoded_keyword = quote(keyword)
            search_url = f"https://{self.search_host}/video?keyword={encoded_keyword}&from_source=webtop_search&page={page}&search_source=3&order=click"
            
            # time_begin 和 time_end 是日期格式，并且必须同时存在
            if time_begin or time_end:
                if not time_begin or not time_end:
                    raise ValueError("time_begin 和 time_end 必须同时存在")
                # 将时间转换为时间戳
                try:
                    time_begin_ts = int(time.mktime(time.strptime(time_begin, "%Y-%m-%d %H:%M:%S")))
                    time_end_ts = int(time.mktime(time.strptime(time_end, "%Y-%m-%d %H:%M:%S")))
                    search_url += f"&pubtime_begin_s={time_begin_ts}&pubtime_end_s={time_end_ts}"
                except ValueError as e:
                    raise ValueError(f"时间格式错误: {e}")
            
            # 使用bil_search_page获取搜索结果
            try:
                video_df = bil_search_page(search_url)
                video_df = video_df.dropna(subset=['BV号'])
                video_df = video_df.drop_duplicates(subset=['BV号'], keep='first')
                
                if isinstance(video_df, pd.DataFrame) and not video_df.empty:
                    for _, video in video_df.iterrows():
                        # 基本信息
                        basic_info = {
                            "video": {
                                "bvid": video['BV号'],
                                "title": video.get('标题', ''),
                                "view_count": self._parse_view_count(video.get('播放量', '0')),
                                "pubdate": video.get('发布时间', ''),
                                "duration": video.get('时长', ''),
                                "description": video.get('视频介绍', ''),
                                "aid": 0,  # 初始值，详细信息获取时会更新
                                "_from_search": True,
                                "_search_keyword": keyword,
                                "_search_page": page
                            },
                            "owner": {
                                "name": video.get('作者', video.get('UP主', '')),
                                "mid": 0
                            }
                        }
                        all_video_data.append(basic_info)
                
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                print(f"搜索页 {page} 处理失败: {str(e)}")
                continue
        
        # 去重（基于BV号）
        unique_videos = {}
        for video in all_video_data:
            bvid = video["video"]["bvid"]
            if bvid not in unique_videos:
                unique_videos[bvid] = video
        
        return list(unique_videos.values())

    # ...existing code...
    
    async def get_videos_detail(self, videos, max_concurrent=3, show_progress=True) -> List[Dict]:
        """
        根据基本视频信息获取详细信息
        
        参数:
            videos: 包含基本信息的视频列表
            max_concurrent: 最大并发请求数
            show_progress: 是否显示进度条
        
        返回:
            包含详细信息的视频列表
        """
        detailed_videos = []
        failed_videos = []
        
        # 创建信号量限制并发请求数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_video_detail(video):
            async with semaphore:
                bv_id = video["video"]["bvid"]
                try:
                    # 构建视频页面URL
                    video_url = f"https://{self.main_host}/video/{bv_id}"
                    
                    # 获取视频页面HTML
                    html_content = await self._get_html(video_url)
                    
                    # 解析视频详细信息
                    video_data = self._parse_video_html(html_content)
                    
                    if video_data:
                        return video_data, None
                    else:
                        return video, "解析失败"
                except Exception as e:
                    return video, str(e)
        
        # 第一轮：视频详情
        total_videos = len(videos)
        if show_progress:
            print(f"开始获取 {total_videos} 个视频的详细信息...")
        
        # 创建任务
        tasks = []
        
        if show_progress:
            for video in tqdm(videos, desc="创建详情获取任务"):
                tasks.append(fetch_video_detail(video))
            print("等待详细信息获取任务完成...")
        else:
            for video in videos:
                tasks.append(fetch_video_detail(video))
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks)
        
        # 处理结果
        for video_data, error in results:
            if error is None:
                detailed_videos.append(video_data)
            else:
                failed_videos.append((video_data, error))
        
        # 第二轮：重试失败的视频
        if failed_videos:
            if show_progress:
                print(f"第一轮获取后有 {len(failed_videos)} 个视频需要重试...")
            
            random.shuffle(failed_videos)  # 随机打乱顺序
            
            retry_results = []
            
            if show_progress:
                for video, error in tqdm(failed_videos, desc="重试获取"):
                    # ...重试逻辑...
                    bv_id = video["video"]["bvid"]
                    try:
                        video_url = f"https://{self.main_host}/video/{bv_id}"
                        html_content = await self._get_html(
                            video_url, 
                            cookie=random_bil_cookie.get_random_cookies(scene='search', timestamp=int(time.time()))
                        )
                        
                        video_data = self._parse_video_html(html_content)
                        if video_data:
                            retry_results.append(video_data)
                        else:
                            retry_results.append(video)
                    except Exception:
                        retry_results.append(video)
                    
                    await asyncio.sleep(random.uniform(0.8, 1.4))
            else:
                for video, error in failed_videos:
                    # ...重试逻辑...
                    bv_id = video["video"]["bvid"]
                    try:
                        video_url = f"https://{self.main_host}/video/{bv_id}"
                        html_content = await self._get_html(
                            video_url, 
                            cookie=random_bil_cookie.get_random_cookies(scene='search', timestamp=int(time.time()))
                        )
                        
                        video_data = self._parse_video_html(html_content)
                        if video_data:
                            retry_results.append(video_data)
                        else:
                            retry_results.append(video)
                    except Exception:
                        retry_results.append(video)
                    
                    await asyncio.sleep(random.uniform(0.8, 1.4))
            
            # 添加重试成功的视频
            detailed_videos.extend(retry_results)
        
        if show_progress:
            print(f"详细信息获取完成，共 {len(detailed_videos)} 个视频")
        
        return detailed_videos

    async def search_and_get_video_info(self, keyword, time_begin=None, time_end=None, page=1) -> List[Dict]:
        """
        根据关键词搜索视频并获取详细信息（兼容旧版接口）
        """
        # 基本信息
        basic_videos = await self.search_videos(keyword, time_begin, time_end, [page])
        
        # 详细信息
        detailed_videos = await self.get_videos_detail(basic_videos)
        
        return detailed_videos
    
    def _parse_view_count(self, view_str):
        """解析播放量字符串为数字"""
        if not view_str or view_str == 'N/A':
            return 0
            
        view_str = str(view_str)
        if '万' in view_str:
            view_str = view_str.replace('万', '')
            try:
                return float(view_str) * 10000
            except ValueError:
                return 0
        else:
            try:
                return int(view_str.replace(',', ''))
            except ValueError:
                return 0
    
    def _parse_video_html(self, html_content) -> Dict[str, Any]:
        """
        从视频页面HTML中提取所需信息
        返回符合数据库结构的格式化结果
        """
        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取初始化数据
            # 查找包含视频数据的script标签
            script_tags = soup.find_all('script')
            video_data = None
            
            for script in script_tags:
                if script.string and "window.__INITIAL_STATE__" in script.string:
                    # 提取JSON数据
                    json_str = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});', script.string, re.DOTALL)
                    if json_str:
                        data = json.loads(json_str.group(1))
                        if 'videoData' in data:
                            video_data = data['videoData']
                            break
            
            if not video_data:
                return None
                
            # 构建返回数据结构
            result = {
                # 视频主表数据
                "video": {
                    "bvid": video_data.get("bvid", ""),
                    "aid": video_data.get("aid", 0),
                    "title": video_data.get("title", ""),
                    "cover_url": video_data.get("pic", ""),
                    "tid": video_data.get("tid", 0),
                    "tname": video_data.get("tname", ""),
                    "tid_v2": video_data.get("tid_v2", 0),
                    "tname_v2": video_data.get("tname_v2", ""),
                    "description": video_data.get("desc", ""),
                    "pubdate": self._timestamp_to_datetime(video_data.get("pubdate", 0)),
                    "ctime": self._timestamp_to_datetime(video_data.get("ctime", 0)),
                    "duration": video_data.get("duration", 0),
                    "copyright": video_data.get("copyright", 0),
                    "state": video_data.get("state", 0),
                    "mission_id": video_data.get("mission_id", 0),
                    "videos": video_data.get("videos", 0),
                    "dynamic": video_data.get("dynamic", ""),
                    "keywords": self._extract_keywords(soup),
                    
                    # 统计信息
                    "view_count": video_data.get("stat", {}).get("view", 0),
                    "danmaku_count": video_data.get("stat", {}).get("danmaku", 0),
                    "reply_count": video_data.get("stat", {}).get("reply", 0),
                    "favorite_count": video_data.get("stat", {}).get("favorite", 0),
                    "coin_count": video_data.get("stat", {}).get("coin", 0),
                    "share_count": video_data.get("stat", {}).get("share", 0),
                    "like_count": video_data.get("stat", {}).get("like", 0),
                    "dislike_count": video_data.get("stat", {}).get("dislike", 0),
                    
                    # 权限信息
                    "is_downloadable": bool(video_data.get("rights", {}).get("download", 0)),
                    "no_reprint": bool(video_data.get("rights", {}).get("no_reprint", 0)),
                    "autoplay": bool(video_data.get("rights", {}).get("autoplay", 0)),
                    
                    # 关联UP主ID
                    "owner_mid": video_data.get("owner", {}).get("mid", 0)
                },
                
                # UP主信息
                "owner": {
                    "mid": video_data.get("owner", {}).get("mid", 0),
                    "name": video_data.get("owner", {}).get("name", ""),
                    "face_url": video_data.get("owner", {}).get("face", "")
                },
                
                # 分P信息
                "pages": [self._parse_video_page(page, video_data.get("bvid", "")) 
                         for page in video_data.get("pages", [])],
                
                # 荣誉信息
                "honors": self._parse_honors(video_data)
            }
            
            return result
            
        except Exception as e:
            print(f"解析视频HTML时出错: {str(e)}")
            return None
    
    def _extract_keywords(self, soup) -> str:
        """提取关键词"""
        keywords_meta = soup.find('meta', attrs={"name": "keywords"})
        if keywords_meta and 'content' in keywords_meta.attrs:
            return keywords_meta['content']
        return ""
    
    def _timestamp_to_datetime(self, timestamp: int) -> str:
        """将时间戳转换为可读时间格式"""
        if timestamp == 0:
            return ""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
    
    def _parse_video_page(self, page_data, bvid) -> Dict:
        """解析视频分P信息"""
        return {
            "cid": page_data.get("cid", 0),
            "bvid": bvid,
            "page_number": page_data.get("page", 0),
            "part_title": page_data.get("part", ""),
            "duration": page_data.get("duration", 0),
            "width": page_data.get("dimension", {}).get("width", 0),
            "height": page_data.get("dimension", {}).get("height", 0),
            "first_frame_url": page_data.get("first_frame", ""),
            "page_ctime": self._timestamp_to_datetime(page_data.get("ctime", 0))
        }
    
    def _parse_honors(self, video_data) -> List[Dict]:
        """解析视频荣誉信息"""
        honors = []
        honor_data = video_data.get("honor_reply", {}).get("honor", [])
        
        for honor in honor_data:
            honors.append({
                "bvid": video_data.get("bvid", ""),
                "type": honor.get("type", 0),
                "description": honor.get("desc", "")
            })
        
        return honors
    

    def _create_basic_info(self, bv_id, video):
        """直接从搜索结果DataFrame行获取基本信息"""
        try:
            # 获取播放量并处理格式
            view_count = 0
            if '播放量' in video:
                view_str = str(video.get('播放量', '0'))
                if '万' in view_str:
                    view_str = view_str.replace('万', '')
                    try:
                        view_count = float(view_str) * 10000
                    except ValueError:
                        view_count = 0
                else:
                    try:
                        view_count = int(view_str.replace(',', ''))
                    except ValueError:
                        view_count = 0
            
            # 创建一个包含基本信息的字典
            return {
                "video": {
                    "bvid": bv_id,
                    "aid": 0,
                    "title": video.get('标题', '获取失败'),
                    "description": video.get('视频介绍', ''),
                    "pubdate": video.get('发布时间', ''),
                    "duration": video.get('时长', ''),
                    "cover_url": "",  # 搜索结果中通常没有封面URL
                    
                    # 统计信息
                    "view_count": view_count,
                    "like_count": int(video.get('点赞数', 0)) if video.get('点赞数', 'N/A') != 'N/A' else 0,
                    "favorite_count": int(video.get('收藏数', 0)) if video.get('收藏数', 'N/A') != 'N/A' else 0,
                    "reply_count": int(video.get('评论数', 0)) if video.get('评论数', 'N/A') != 'N/A' else 0,
                    
                    # 标记为失败
                    "_error": "详情获取失败"
                },
                "owner": {
                    "name": video.get('作者', video.get('UP主', '获取失败')),
                    "mid": 0,
                    "face_url": ""
                },
                "pages": [],
                "honors": []
            }
        except Exception as e:
            # 若处理失败，则返回最小化信息
            print(f"创建基本信息失败: {str(e)}")
            return {
                "video": {
                    "bvid": bv_id,
                    "title": str(video.get('标题', '获取失败')),
                    "_error": f"基本信息获取失败: {str(e)[:50]}"
                },
                "owner": {
                    "name": str(video.get('作者', video.get('UP主', '获取失败'))),
                    "mid": 0
                },
                "pages": [],
                "honors": []
            }

# 使用示例
if __name__ == "__main__":
    api = BilibiliAPI()
    keyword = "翁法罗斯"
    results = asyncio.run(api.search_and_get_video_info(keyword=keyword, page=1))
    
    print(f"共获取到 {len(results)} 个视频信息")
    
    for result in results:
        print(f"视频标题: {result['video']['title']}")
        print(f"UP主: {result['owner']['name']}")
        print(f"发布时间: {result['video']['pubdate']}")
        print(f"播放量: {result['video']['view_count']}")
        print("---------------------")