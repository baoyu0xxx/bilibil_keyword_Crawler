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
        self.cookie = random_bil_cookie.get_random_cookies()

    
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
    
    async def search_and_get_video_info(self, keyword, time_begin = None, time_end = None, page=1,) -> List[Dict]:
        """
        根据关键词搜索视频并获取详细信息
        返回符合数据库结构的格式化结果
        """
        
        # 构建搜索URL - 使用quote确保中文关键词正确编码
        encoded_keyword = quote(keyword)
        search_url = f"https://{self.search_host}/video?keyword={encoded_keyword}&from_source=webtop_search&page={page}&search_source=3&order=click"
        
        # time_begin 和 time_end 是 日期格式，并且必须同时存在
        if time_begin or time_end:
            if not time_begin or not time_end:
                raise ValueError("time_begin 和 time_end 必须同时存在")
            # 将时间转换为时间戳
            try:
                time_begin = int(time.mktime(time.strptime(time_begin, "%Y-%m-%d %H:%M:%S")))
                time_end = int(time.mktime(time.strptime(time_end, "%Y-%m-%d %H:%M:%S")))

                search_url += f"&pubtime_begin_s={time_begin}&pubtime_end_s={time_end}"
            except ValueError as e:
                raise ValueError(f"时间格式错误: {e}")

        # print(f"搜索URL: {search_url}")
        
        # 使用bil_search_page获取搜索结果
        video_df = bil_search_page(search_url)
        # 去重并删除空值
        video_df = video_df.dropna(subset=['BV号'])
        video_df = video_df.drop_duplicates(subset=['BV号'], keep='first')
        
        # 正确处理DataFrame返回值
        if isinstance(video_df, pd.DataFrame):
            if video_df.empty:
                print(f"未找到与关键词 '{keyword}' 相关的视频")
                return []
        else:
            # 如果返回的不是DataFrame（可能是空列表）
            print(f"搜索结果格式不正确或为空: {type(video_df)}")
            return []
        
        # 结果存储
        results = []
        
        # 对每个BV号获取详细信息
        total_videos = len(video_df)
        with tqdm(total=total_videos, desc="获取视频信息") as pbar:
            for _, video in video_df.iterrows():
                bv_id = video['BV号']
                if bv_id == "N/A":
                    pbar.update(1)
                    continue
                
                try:
                    # 更新进度条描述，显示当前处理的BV号
                    pbar.set_description(f"处理 {bv_id}")
                    
                    # 构建视频页面URL
                    video_url = f"https://{self.main_host}/video/{bv_id}"
                    
                    # 获取视频页面HTML
                    html_content = await self._get_html(video_url)
                    
                    # 解析视频信息
                    video_data = self._parse_video_html(html_content)
                    
                    if video_data:
                        results.append(video_data)
                        pbar.set_postfix({"状态": "成功"})
                    else:
                        pbar.set_postfix({"状态": "解析失败"})
                    
                except Exception as e:
                    pbar.set_postfix({"状态": f"错误: {str(e)[:30]}..."})
                    continue
                finally:
                    pbar.update(1)
                    # 添加延迟避免请求过于频繁
                    await asyncio.sleep(0.5 + 0.5 * random.random())
        
        return results
    
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

# 使用示例
async def main():
    api = BilibiliAPI()
    keyword = "翁法罗斯"
    results = await api.search_and_get_video_info(keyword=keyword,page=1)
    
    
    print(f"共获取到 {len(results)} 个视频信息")
    
    for result in results:
        print(f"视频标题: {result['video']['title']}")
        print(f"UP主: {result['owner']['name']}")
        print(f"发布时间: {result['video']['pubdate']}")
        print(f"播放量: {result['video']['view_count']}")
        print("---------------------")

if __name__ == "__main__":
    asyncio.run(main())