import re
import requests
import json
from urllib.parse import quote
import pandas as pd
import hashlib
import urllib
import time
import csv
import random_bil_cookie
import random
from tqdm import tqdm

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


def get_Header(cookie):
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


# 轮页爬取
def start(bv, aid, pageID, count, csv_writer, is_second, cookie, wts = int(time.time()), pbar=None,max_page = None,page_counter = 0):
    # 初始化评论处理器
    processor = CommentProcessor(csv_writer)
    processor.count = count

    page_counter += 1
    if max_page is not None and page_counter > max_page:
        print(f"已达到设定的最大页数限制: {max_page}页")
        return count
    
    # 获取当下时间戳
    if wts is None:
        wts = int(time.time())
    
    # 参数
    mode = 2
    plat = 1
    type = 1
    web_location = 1315875 

    # 获取当下时间戳
    wts = int(time.time())

    # 如果不是第一页
    if pageID != '':
        pagination_str = json.dumps({
            "offset": json.dumps({
                "type": 3,
                "direction": 1,
                "Data": {"cursor": int(pageID)}
            }, separators=(',', ':'))
        }, separators=(',', ':'))
    # 如果是第一页
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
    
    header = get_Header(cookie)
    try:
        response = requests.get(url=url, headers=header, timeout=5)
        response.encoding = 'utf-8'
        comment = response.text
        comment = json.loads(comment)
    except Exception as e:
        print("请求或解码失败，原始内容如下：")
        print(e)
        try:
            print("响应头：", response.headers)
            print("接口返回内容：", response.text[:500])
        except:
            pass
        return

    for reply in comment['data']['replies']:
        result = processor.process_reply(reply, pbar=pbar)
        rpid = result["rpid"]
        rereply = result["rereply_count"]

        # 二级评论(如果开启了二级评论爬取，且该评论回复数不为0，则爬取该评论的二级评论)
        if is_second and rereply != 0:
            # 创建二级评论的进度条
            with tqdm(total=rereply, desc=f"爬取ID:{rpid}的二级评论", leave=False) as second_pbar:
                for page in range(1,rereply//10+2):
                    second_url=f"https://api.bilibili.com/x/v2/reply/reply?oid={aid}&type=1&root={rpid}&ps=10&pn={page}&web_location=333.788"

                    response = requests.get(url=second_url, headers=header, timeout=10)
                    response.encoding = response.apparent_encoding
                    second_comment = json.loads(response.text)
                    
                    if not second_comment['data']['replies']:
                        continue
                        
                    for second in second_comment['data']['replies']:
                        processor.process_reply(second, parent_id=second["parent"], pbar=second_pbar)
        
    # 下一页的pageID
    next_pageID = comment['data']['cursor']['next']
    is_end = comment['data']['cursor']['is_end']

    should_stop = (is_end == 'true' or next_pageID == '')

    if should_stop:
        print(f"评论爬取完成！总共爬取{processor.count}条。")
        return processor.count
    else:
        # 随机等待
        time.sleep(random.uniform(1, 2))
        if pbar is None:
            print(f"当前爬取{count}条。")
        start(bv, aid, next_pageID, count, csv_writer, is_second, cookie, wts, pbar, max_page ,page_counter)


if __name__ == "__main__":
    bv = "BV1GeUUYREXy"
    aid = '113520163229242'
    title = '《崩坏：星穹铁道》黄金史诗PV：「翁法罗斯英雄纪」'
    next_pageID = ''
    count = 0

    wts = int(time.time())
    cookie = random_bil_cookie.get_random_cookies(scene='comment', timestamp=wts,format_as_string=True)
    is_second = False
    max_page = 5

    print(f"开始爬取视频 {title} (BV: {bv}) 的评论")
    
    # 创建CSV文件并写入表头
    with open(f'{title[:12]}_评论.csv', mode='w', newline='', encoding='utf-8-sig') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(['序号', '上级评论ID','评论ID', '用户ID', '用户名', '用户等级', '性别', '评论内容', '评论时间', '回复数', '点赞数', '个性签名', 'IP属地', '是否是大会员', '头像'])

        estimated_total = 5000
        print(f"预计评论数量: ~{estimated_total}条 (实际数量可能不同)")
        
        with tqdm(total=estimated_total, desc="爬取B站评论") as pbar:
            final_count = start(bv, aid, next_pageID, count, csv_writer, is_second, cookie, wts, pbar, max_page=max_page, page_counter=0)
            pbar.close()
            
        print(f"爬取完成！结果已保存至 {title[:12]}_评论.csv")