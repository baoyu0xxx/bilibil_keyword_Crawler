import re
import json
import time
import csv
import asyncio
import random
import hashlib
import urllib
import pandas as pd
from urllib.parse import quote
from tqdm import tqdm
import random_bil_cookie
import aiohttp

class CommentProcessor:
    """
    B站评论处理器，用于提取和处理评论字段
    """
    def __init__(self, csv_writer):
        self.csv_writer = csv_writer
        self.count = 0
    
    def _extract_field(self, data, keys, default=None):
        """
        安全地从嵌套字典中提取字段
        """
        try:
            result = data
            for key in keys:
                result = result[key]
            return result
        except (KeyError, TypeError, IndexError):
            return default
    
    def _extract_rereply_count(self, reply):
        """提取回复数"""
        try:
            rereply_text = self._extract_field(reply, ["reply_control", "sub_reply_entry_text"], "")
            if rereply_text:
                return int(re.findall(r'\d+', rereply_text)[0])
            return 0
        except:
            return 0
    
    def _get_vip_status(self, reply):
        """获取会员状态"""
        vip_status = self._extract_field(reply, ["member", "vip", "vipStatus"], 0)
        return "是" if vip_status != 0 else "否"
    
    def _get_ip_location(self, reply):
        """获取IP属地"""
        try:
            location = self._extract_field(reply, ["reply_control", "location"], "")
            return location[5:] if location else "未知"
        except:
            return "未知"
    
    def process_reply(self, reply, parent_id=None, pbar=None):
        """
        处理单条评论并写入CSV
        返回处理后的评论数据
        """
        # 更新计数并进度条
        self.count += 1
        if pbar:
            pbar.update(1)
            pbar.set_description("爬取评论中")
        
        # 获取评论各字段
        parent = parent_id if parent_id else reply.get("parent", "")
        rpid = reply.get("rpid", "")
        uid = reply.get("mid", "")
        
        # 提取用户信息
        name = self._extract_field(reply, ["member", "uname"], "")
        level = self._extract_field(reply, ["member", "level_info", "current_level"], 0)
        sex = self._extract_field(reply, ["member", "sex"], "")
        avatar = self._extract_field(reply, ["member", "avatar"], "")
        sign = self._extract_field(reply, ["member", "sign"], "")
        
        # 提取评论内容相关信息
        vip = self._get_vip_status(reply)
        ip = self._get_ip_location(reply)
        context = self._extract_field(reply, ["content", "message"], "")
        reply_time = pd.to_datetime(reply.get("ctime", 0), unit='s')
        rereply = self._extract_rereply_count(reply)
        like = reply.get('like', 0)
        
        # 构建评论数据
        comment_data = [
            self.count, parent, rpid, uid, name, level, sex, 
            context, reply_time, rereply, like, sign, ip, vip, avatar
        ]
        
        # 写入CSV
        self.csv_writer.writerow(comment_data)
        
        # 返回处理结果
        return {
            "rpid": rpid,
            "rereply_count": rereply,
            "data": comment_data
        }

async def get_response(url, headers, max_retries=3):
    """异步获取响应+重试机制"""
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"请求返回状态码: {response.status}, URL: {url}")
                        if attempt < max_retries - 1:
                            delay = 1 * (attempt + 1)
                            print(f"将在{delay}秒后重试...")
                            await asyncio.sleep(delay)
                        else:
                            response.raise_for_status()
        except Exception as e:
            if attempt < max_retries - 1:
                delay = 1 * (attempt + 1)
                print(f"请求失败 ({attempt+1}/{max_retries}): {str(e)}, 将在{delay}秒后重试...")
                await asyncio.sleep(delay)
            else:
                print(f"请求最终失败: {str(e)}")
                raise


def get_header(cookie):
    # cookie = cookie

    header = {
        'authority': 'api.bilibili.com',
        'method': 'GET',
        'scheme': 'https',
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-TW;q=0.5',
        'dnt': '1',
        'origin': 'https://www.bilibili.com',
        'priority': 'u=1, i',
        'sec-ch-ua': f'"Microsoft Edge";v="{random.randint(120, 135)}", "Not-A.Brand";v="8", "Chromium";v="{random.randint(120, 135)}"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(120, 135)}.0.0.0 Safari/537.36 Edg/{random.randint(120, 135)}.0.0.0',
        # 'Cookie': cookie, # comment cookie尚存问题，暂时不使用
    }
    return header

async def fetch_second_comments(aid, rpid, rereply, processor, header, parent_pbar=None):
    """异步爬取二级评论，限制并发"""
    second_pbar = tqdm(total=rereply, desc=f"爬取ID:{rpid}的二级评论", leave=False) if parent_pbar else None
    
    # 计算需要的页数
    pages = (rereply - 1) // 10 + 1
    tasks = []
    
    # 分批处理，每批次不超过5个请求
    batch_size = 5
    for i in range(0, pages, batch_size):
        batch_tasks = []
        for page in range(i + 1, min(i + batch_size + 1, pages + 1)):
            second_url = f"https://api.bilibili.com/x/v2/reply/reply?oid={aid}&type=1&root={rpid}&ps=10&pn={page}&web_location=333.788"
            batch_tasks.append(fetch_second_page(second_url, header, processor, rpid, second_pbar))
        
        # 执行当前批次的任务
        await asyncio.gather(*batch_tasks)
        
        # 批次间短暂暂停
        await asyncio.sleep(0.5)
    
    if second_pbar:
        second_pbar.close()

async def fetch_second_page(url, header, processor, parent_id, pbar=None):
    """获取单个二级评论页"""
    try:
        second_comment = await get_response(url, header)
        
        if not second_comment['data']['replies']:
            return
            
        for second in second_comment['data']['replies']:
            processor.process_reply(second, parent_id=second["parent"], pbar=pbar)
    except Exception as e:
        print(f"二级评论获取失败: {e}")

async def start_async(bv, aid, pageID, count, csv_writer, is_second, cookie, wts=None, pbar=None, max_page=None, page_counter=0):
    """异步版本的start函数"""
    # 初始化
    processor = CommentProcessor(csv_writer)
    processor.count = count
    all_tasks = []
    
    page_counter += 1
    if max_page is not None and page_counter > max_page:
        print(f"已达到设定的最大页数限制: {max_page}页")
        return count
    
    # 获取当下时间戳
    if wts is None:
        wts = int(time.time())
    
    # 参数设置
    mode = 2
    plat = 1
    type = 1
    web_location = 1315875

    # 构建分页参数
    if pageID != '':
        pagination_str = json.dumps({
            "offset": json.dumps({
                "type": 3, 
                "direction": 1,
                "Data": {"cursor": int(pageID)}
            }, separators=(',', ':'))
        }, separators=(',', ':'))
    else:
        pagination_str = '{"offset":""}'

    # MD5加密
    code = f"mode={mode}&oid={aid}&pagination_str={urllib.parse.quote(pagination_str)}&plat={plat}&seek_rpid=&type={type}&web_location={web_location}&wts={wts}" + 'ea1db124af3c7062474693fa704f4ff8'
    MD5 = hashlib.md5()
    MD5.update(code.encode('utf-8'))
    w_rid = MD5.hexdigest() 

    url = f"https://api.bilibili.com/x/v2/reply/wbi/main?oid={aid}&type={type}&mode={mode}&pagination_str={urllib.parse.quote(pagination_str, safe=':')}&plat=1&seek_rpid=&web_location=1315875&w_rid={w_rid}&wts={wts}"
    
    if pbar is None:
        print(f'正在请求: {url}')
    
    header = get_header(cookie)
    
    try:
        comment = await get_response(url, header)
    except Exception as e:
        print(f"请求或解码失败: {e}")
        return count
    
    # 处理主评论
    for reply in comment['data']['replies']:
        result = processor.process_reply(reply, pbar=pbar)
        rpid = result["rpid"]
        rereply = result["rereply_count"]

        # 如果需要爬取二级评论
        if is_second and rereply != 0:
            # 将二级评论任务添加到任务列表
            all_tasks.append(fetch_second_comments(aid, rpid, rereply, processor, header, pbar))
    
    if all_tasks:
        await asyncio.gather(*all_tasks)

    next_pageID = comment['data']['cursor']['next']
    is_end = comment['data']['cursor']['is_end']

    if is_end == 'true' or next_pageID == '':
        print(f"评论爬取完成！总共爬取{processor.count}条。")
        return processor.count
    else:
        await asyncio.sleep(random.uniform(0.5, 1.5))
        if pbar is None:
            print(f"当前爬取{processor.count}条。")
        return await start_async(bv, aid, next_pageID, processor.count, csv_writer, is_second, cookie, wts, pbar, max_page, page_counter)

async def async_crawler(): # 测试用
    """异步爬虫主函数"""
    bv = "BV1GeUUYREXy"
    aid = '113520163229242'
    title = '《崩坏：星穹铁道》黄金史诗PV：「翁法罗斯英雄纪」'
    next_pageID = ''
    count = 0

    wts = int(time.time())

    try:
        cookie = random_bil_cookie.get_random_cookies(scene='comment', timestamp=wts, format_as_string=True)
    except Exception as e:
        print(f"获取cookie失败: {e}，将使用无cookie方式访问")
        cookie = None
    
    is_second = False
    max_page = 5

    print(f"开始爬取视频 {title} (BV: {bv}) 的评论")
    
    # 创建CSV文件并写入表头
    with open(f'{title[:12]}_评论_异步.csv', mode='w', newline='', encoding='utf-8-sig') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(['序号', '上级评论ID','评论ID', '用户ID', '用户名', '用户等级', '性别', '评论内容', '评论时间', '回复数', '点赞数', '个性签名', 'IP属地', '是否是大会员', '头像'])

        estimated_total = 5000
        print(f"预计评论数量: ~{estimated_total}条 (实际数量可能不同)")
        
        with tqdm(total=estimated_total, desc="爬取B站评论") as pbar:
            final_count = await start_async(bv, aid, next_pageID, count, csv_writer, is_second, cookie, wts, pbar, max_page=max_page)
            pbar.close()
            
        print(f"爬取完成！结果已保存至 {title[:12]}_评论_异步.csv")

if __name__ == "__main__":
    asyncio.run(async_crawler())