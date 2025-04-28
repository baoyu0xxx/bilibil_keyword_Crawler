import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import random
import time
import random_bil_cookie
from datetime import datetime


def decode_html_entities(text):
    # 替换unicode转义字符
    text = text.replace("\\u003Cem class=\\\"keyword\\\"\\u003E", "").replace("\\u003C\\u002Fem\\u003E", "")
    return text

def extract_video_info(html_content):
    videos = []
    
    # 使用正则表达式匹配视频信息
    patterns = {
        "BV号": r'bvid:"([^"]*)"',
        "标题": r'title:"(.*?)",',
        "作者": r'author:"(.*?)",',
        "发布时间": r'pubdate:(\d+)',
        "播放量": r'play:(\d+)',
        "点赞数": r'like:(\d+)',
        "收藏数": r'favorites:(\d+)',
        "时长": r'duration:"([^"]*)"',
        "视频介绍": r'description:"([^"]*)"',
        "标签": r'tag:"([^"]*)"',
        "评论数": r'review:(\d+)'
    }
    
    video_blocks = re.findall(r'{[^{}]*}', html_content)
    
    for block in video_blocks:
        try:
            video = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, block)
                if match:
                    value = match.group(1)
                    if key == "发布时间":
                        value = datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d %H:%M:%S")
                    elif key == "标题":
                        value = decode_html_entities(value)
                    video[key] = value
                else:
                    video[key] = "N/A"
            videos.append(video)
        except Exception as e:
            continue
            
    return videos

def bil_search_page(url,headers = {}) -> pd.DataFrame:
    if headers == {}:
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
            'Referer': 'https://www.bilibili.com/',
            'Priority': 'u=0, i',
        }
    else:
        pass

    # 随机生成cookie
    cookies = random_bil_cookie.get_random_cookies()

    try:
        response = requests.get(url, headers=headers, timeout=15, cookies=cookies)
        time.sleep(random.uniform(0.1, 1.0))  
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        if 'search.bilibili.com/video' in url:
            pattern = r'egg_hit:a\s*,result:\s*(\[.*?\])\s*,show'
            match = re.search(pattern, soup.prettify())
            
            if match:
                data_str = match.group(1)
                # 解析视频数据
                video_list = extract_video_info(data_str)
                video_data = pd.DataFrame(video_list)
                return video_data
            else:
                print("未找到匹配的数据")
                return pd.DataFrame()
                
        else:
            video_list = soup.find('div', class_='video-list row')
            if not video_list:
                print("未找到视频列表")
                return pd.DataFrame()
            
            results = []
            
            for item in video_list.find_all('div', class_=re.compile('^col_3')):
                try:
                    # 提取BV号
                    a_tag = item.find('a', href=re.compile(r'/video/BV\w+'))
                    bv = re.search(r'BV\w+', a_tag['href']).group() if a_tag else "N/A"
                    
                    # 提取标题
                    title_tag = item.find('h3', class_='bili-video-card__info--tit')
                    title = title_tag.get_text(strip=True).replace('\n', '') if title_tag else "N/A"
                    
                    # 提取发布者和时间
                    info_bottom = item.find('div', class_='bili-video-card__info--bottom')
                    author = "N/A"
                    publish_date = "N/A"
                    if info_bottom:
                        author_tag = info_bottom.find('span', class_='bili-video-card__info--author')
                        author = author_tag.get_text(strip=True) if author_tag else "N/A"
                        
                        date_tag = info_bottom.find('span', class_='bili-video-card__info--date')
                        publish_date = date_tag.get_text(strip=True).replace('·', '').strip() if date_tag else "N/A"
                    
                    results.append({
                        'BV号': bv,
                        '标题': title,
                        '作者': author,
                        '发布时间': publish_date
                    })
                    
                except Exception as e:
                    print(f"解析单个视频时出错: {str(e)}")
                    continue
        
        # 针对不同页面进行不同的处理后，我们应该有一个包含视频信息的results列表
        return pd.DataFrame(results)
        
    except Exception as e:
        print(f"请求出错: {str(e)}")
        return []

# 使用示例
if __name__ == "__main__":
    # search_url = "https://search.bilibili.com/all?vt=03590256&keyword=%E7%BF%81%E6%B3%95%E7%BD%97%E6%96%AF&from_source=webtop_search&spm_id_from=333.1007&search_source=3" \
    search_url = "https://search.bilibili.com/video?keyword=%E9%A3%9F%E7%89%A9%E8%AF%AD&page=1&search_source=3&order=click"
    
    video_data = bil_search_page(search_url)

    if video_data.empty:
        pass
    else:
        # 打印结果
        for idx, row in video_data.iterrows():
            print(f"\n视频 {idx+1}:")
            print(f"BV号: {row['BV号']}")
            print(f"标题: {row['标题']}")
            print(f"作者: {row['作者']}")
            print(f"发布时间: {row['发布时间']}")
    
    # 保存到CSV示例
    video_data.to_csv('bilibili_videos.csv', index=False, encoding='utf_8_sig')