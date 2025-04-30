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

# 获取B站的Header
def get_Header():
    cookie = random_bil_cookie.get_random_cookies(format_as_string=True)

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
        'referer': 'https://www.bilibili.com',
        'sec-ch-ua': f'"Microsoft Edge";v="{random.randint(120, 135)}", "Not-A.Brand";v="8", "Chromium";v="{random.randint(120, 135)}"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(120, 135)}.0.0.0 Safari/537.36 Edg/{random.randint(120, 135)}.0.0.0',
        'Cookie': cookie,
    }
    return header


# 轮页爬取
def start(bv, aid, pageID, count, csv_writer, is_second):
    # 参数
    mode = 2
    plat = 1
    type = 1
    web_location = 1315875 

    # 获取当下时间戳
    wts = time.time()

    # 如果不是第一页
    if pageID != '':
        pagination_str = f'{{"offset":"{{\\\"type\\\":3,\\\"direction\\\":1,\\\"data\\\":{{\\\"cursor\\\":{pageID}}}}}"}}'
        # pagination_str = '{"offset":"{\\\"type\\\":3,\\\"direction\\\":1,\\\"Data\\\":{\\\"cursor\\\":%d}}"}' % pageID
    # 如果是第一页
    else:
        pagination_str = '{"offset":""}'

    # MD5加密
    code = f"mode={mode}&oid={aid}&pagination_str={urllib.parse.quote(pagination_str)}&plat={plat}&seek_rpid=&type={type}&web_location={web_location}&wts={wts}" + 'ea1db124af3c7062474693fa704f4ff8'
    MD5 = hashlib.md5()
    MD5.update(code.encode('utf-8'))
    w_rid = MD5.hexdigest()

    url = f"https://api.bilibili.com/x/v2/reply/wbi/main?oid={aid}&type={type}&mode={mode}&pagination_str={urllib.parse.quote(pagination_str, safe=':')}&plat=1&web_location=1315875&w_rid={w_rid}&wts={wts}"
    # comment = requests.get(url=url, headers=get_Header()).content.decode('utf-8')
    # comment = json.loads(comment)
    header = get_Header()
    try:
        response = requests.get(url=url, headers=header, timeout=10)
        
        # # 保存网页-调试用
        # with open(f'bilibili_comment_page_{pageID}.html', 'w', encoding='utf-8') as f:
        #     f.write(response.text)

        response.encoding = response.apparent_encoding 
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
        # 评论数量+1
        count += 1
        # 上级评论ID
        parent=reply["parent"]
        # 评论ID
        rpid = reply["rpid"]
        # 用户ID
        uid = reply["mid"]
        # 用户名
        name = reply["member"]["uname"]
        # 用户等级
        level = reply["member"]["level_info"]["current_level"]
        # 性别
        sex = reply["member"]["sex"]
        # 头像
        avatar = reply["member"]["avatar"]
        # 是否是大会员
        if reply["member"]["vip"]["vipStatus"] == 0:
            vip = "否"
        else:
            vip = "是"
        # IP属地
        try:
            IP = reply["reply_control"]['location'][5:]
        except:
            IP = "未知"
        # 内容
        context = reply["content"]["message"]
        # 评论时间
        reply_time = pd.to_datetime(reply["ctime"], unit='s')
        # 相关回复数
        try:
            rereply = reply["reply_control"]["sub_reply_entry_text"]
            rereply = int(re.findall(r'\d+', rereply)[0])
        except:
            rereply = 0
        # 点赞数
        like = reply['like']

        # 个性签名
        try:
            sign = reply['member']['sign']
        except:
            sign = ''

        # 写入CSV文件
        csv_writer.writerow([count, parent, rpid, uid, name, level, sex, context, reply_time, rereply, like, sign, IP, vip, avatar])

        # 二级评论(如果开启了二级评论爬取，且该评论回复数不为0，则爬取该评论的二级评论)
        if is_second and rereply !=0:
            for page in range(1,rereply//10+2):
                second_url=f"https://api.bilibili.com/x/v2/reply/reply?oid={aid}&type=1&root={rpid}&ps=10&pn={page}&web_location=333.788"

                response = requests.get(url=second_url, headers=header, timeout=10)
                response.encoding = response.apparent_encoding
                second_comment = response.text
                second_comment = json.loads(second_comment)
                # second_comment=requests.get(url=second_url,headers=get_Header()).content.decode('utf-8')
                # second_comment=json.loads(second_comment)
                for second in second_comment['data']['replies']:
                    # 评论数量+1
                    count += 1
                    # 上级评论ID
                    parent=second["parent"]
                    # 评论ID
                    second_rpid = second["rpid"]
                    # 用户ID
                    uid = second["mid"]
                    # 用户名
                    name = second["member"]["uname"]
                    # 用户等级
                    level = second["member"]["level_info"]["current_level"]
                    # 性别
                    sex = second["member"]["sex"]
                    # 头像
                    avatar = second["member"]["avatar"]
                    # 是否是大会员
                    if second["member"]["vip"]["vipStatus"] == 0:
                        vip = "否"
                    else:
                        vip = "是"
                    # IP属地
                    try:
                        IP = second["reply_control"]['location'][5:]
                    except:
                        IP = "未知"
                    # 内容
                    context = second["content"]["message"]
                    # 评论时间
                    reply_time = pd.to_datetime(second["ctime"], unit='s')
                    # 相关回复数
                    try:
                        rereply = second["reply_control"]["sub_reply_entry_text"]
                        rereply = re.findall(r'\d+', rereply)[0]
                    except:
                        rereply = 0
                    # 点赞数
                    like = second['like']
                    # 个性签名
                    try:
                        sign = second['member']['sign']
                    except:
                        sign = ''

                    # 写入CSV文件
                    csv_writer.writerow([count, parent, second_rpid, uid, name, level, sex, context, reply_time, rereply, like, sign, IP, vip, avatar])
            
    # 下一页的pageID
    next_pageID = comment['data']['cursor']['next']
    is_end = comment['data']['cursor']['is_end']
    # 判断是否是最后一页
    if is_end == 'true'or next_pageID == '':
        print(f"评论爬取完成！总共爬取{count}条。")
        return
    # 如果不是最后一页
    else: # 随机等待0.5-1.2秒
        time.sleep(random.uniform(0.4, 1.2))
        print(f"当前爬取{count}条。")
        start(bv, aid, next_pageID, count, csv_writer,is_second)

if __name__ == "__main__":
    # 获取视频bv
    bv = "BV1GeUUYREXy"
    # 获取视频oid和标题
    aid = '113520163229242'
    title = '《崩坏：星穹铁道》黄金史诗PV：「翁法罗斯英雄纪」'
    # 评论起始页（默认为空）
    next_pageID = ''
    # 初始化评论数量
    count = 0

    # 是否开启二级评论爬取，默认开启
    is_second = False

    # 创建CSV文件并写入表头
    with open(f'{title[:12]}_评论.csv', mode='w', newline='', encoding='utf-8-sig') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(['序号', '上级评论ID','评论ID', '用户ID', '用户名', '用户等级', '性别', '评论内容', '评论时间', '回复数', '点赞数', '个性签名', 'IP属地', '是否是大会员', '头像'])

        # 开始爬取
        start(bv, aid, next_pageID, count, csv_writer,is_second)