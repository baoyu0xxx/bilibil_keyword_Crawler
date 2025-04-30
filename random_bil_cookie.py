import uuid
import hashlib
import time
import random
import base64
import json
from typing import Dict, Tuple, List, Optional, Union

class BiliCookieGenerator:
    """B站Cookie生成器 - 适用于多种场景下的请求模拟"""
    
    # Cookie配置项 - 用于控制不同场景下需要的Cookie项
    COOKIE_CONFIG = {
        "basic": [
            "buvid_fp_plain", "buvid4", "DedeUserID", "DedeUserID__ckMd5",
            "header_theme_version", "enable_web_push", "CURRENT_BLACKGAP", "PVID",
            "buvid3", "b_nut", "_uuid", "match_float_version", "LIVE_BUVID", 
            "share_source_origin", "bsource", "rpdid", "CURRENT_QUALITY", 
            "enable_feed_channel", "hit-dyn-v2", "fingerprint", "timeMachine",
            "home_feed_column", "browser_resolution", "bp_t_offset_", "sid"
        ],
        "search": [
            "CURRENT_BLACKGAP", "browser_resolution", "b_lsid", "LIVE_BUVID", 
            "CURRENT_QUALITY"
        ],
        "video": [
            "CURRENT_FNVAL", "home_feed_column", "enable_web_push", 
            "CURRENT_BLACKGAP", "SESSDATA", "bili_jct", "CURRENT_QUALITY"
        ],
        "comment": [
            "bili_ticket", "bili_ticket_expires", "CURRENT_FNVAL", "SESSDATA",
            "bili_jct", "sid", "b_lsid", "buvid_fp"
        ]
    }
    
    @staticmethod
    def _generate_device_fingerprint(timestamp: int) -> Dict[str, str]:
        """生成设备指纹相关的Cookie"""
        # 生成UUID格式的buvid3 (格式: 0E4B4FD9-19C1-0324-888F-FDDD880BA0F502858infoc)
        buvid3_uuid = str(uuid.uuid4()).upper()
        buvid3 = f"{buvid3_uuid}-{timestamp}infoc"
        
        # buvid4格式: 76FE0526-6A09-D1EB-4EE2-E5064AB1196832708-022062006-Cdf9mZshzhpqT%2FO1fDtfpw%3D%3D
        uuid_part = str(uuid.uuid4()).upper()
        random_part = base64.b64encode(f"{random.random()}".encode()).decode().replace("=", "")
        timestamp_year = time.strftime("%Y", time.localtime(timestamp))[-2:]
        timestamp_month = time.strftime("%m", time.localtime(timestamp))
        timestamp_day = time.strftime("%d", time.localtime(timestamp))
        buvid4 = f"{uuid_part}-{timestamp}{timestamp_year}{timestamp_month}{timestamp_day}-{random_part}"
        
        # 真实请求中观察到的指纹
        fingerprint = hashlib.md5(f"{timestamp}{random.random()}".encode()).hexdigest()
        
        return {
            "buvid3": buvid3,
            "buvid4": buvid4,
            "buvid_fp": f"{buvid3}",  # 与buvid3保持一致
            "buvid_fp_plain": "undefined",
            "fingerprint": fingerprint
        }
    
    @staticmethod
    def _generate_session_data(timestamp: int) -> Dict[str, str]:
        """生成会话相关Cookie"""
        hash_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        extra_part = base64.b64encode(f"CjCmM5qQQNMR_DWBGg-XLiu_SQMn5NtcQEGTw0IwnXinUPdE8J9GOUkf-wh0QBrpZ2cSVmQzZzMzcWJyWUZ2WmdXYThfX2xCTzVyQWQ0c2VFV19MZk5XX3dNUmtqbXZTRTlnNFYwcndxcnpmLTE5QkczcGlaVktvQTBzM0R0UldzYjJFSlZLMU9B".encode()).decode().replace("=", "")
        expiry = timestamp + 15552000  # 180天
        
        # 生成JWT格式的bili_ticket
        header = {"alg": "HS256", "kid": "s03", "typ": "JWT"}
        payload = {"exp": timestamp + 259200, "iat": timestamp, "plt": -1}  # 3天过期
        
        header_b64 = base64.b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        # 简化的签名
        signature = hashlib.sha256(f"{header_b64}.{payload_b64}_bili_ticket_key".encode()).hexdigest()[:32]
        bili_ticket = f"{header_b64}.{payload_b64}.{signature}"
        
        return {
            "SESSDATA": f"{hash_id}%2C{expiry}%2Cc5307%2A41{extra_part}IIEC",
            "bili_jct": hashlib.md5(f"{timestamp}{random.random()}".encode()).hexdigest(),
            "bili_ticket": bili_ticket,
            "bili_ticket_expires": str(timestamp + 259200)
        }
    
    @staticmethod
    def _generate_user_info(user_id: str, timestamp: int) -> Dict[str, str]:
        """生成用户相关Cookie"""
        return {
            "DedeUserID": user_id,
            "DedeUserID__ckMd5": hashlib.md5(user_id.encode()).hexdigest()[:16],
            "sid": ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8)),
            f"bp_t_offset_{user_id}": str(random.randint(10**18, 10**19-1))
        }
    
    @staticmethod
    def _generate_preferences() -> Dict[str, str]:
        """生成用户偏好相关Cookie"""
        return {
            "header_theme_version": "CLOSE",
            "enable_web_push": "DISABLE",
            "CURRENT_BLACKGAP": "0",
            "browser_resolution": "1528-704",
            "CURRENT_QUALITY": "80",
            "CURRENT_FNVAL": "4048",  # 视频页和评论页使用高级值
            "home_feed_column": "5",
            "enable_feed_channel": "ENABLE",
            "match_float_version": "ENABLE",
            "share_source_origin": "COPY",
            "timeMachine": "0",
            "hit-dyn-v2": "1",
            "bsource": "search_bing",  # 新增字段
            "rpdid": f"0{''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))}|3w1TFQsQ"  # 新增字段
        }
    
    @staticmethod
    def _generate_misc(timestamp: int) -> Dict[str, str]:
        """生成杂项Cookie"""
        return {
            "_uuid": f"{str(uuid.uuid4()).upper()}-{random.choice(['A', 'B', 'C', 'D'])}{timestamp}infoc",
            "b_lsid": f"{hashlib.md5(str(timestamp).encode()).hexdigest()[:8].upper()}_{hex(int(timestamp * 1000))[2:].upper()}",
            "b_nut": str(timestamp),
            "PVID": "2",
            "LIVE_BUVID": f"AUTO{timestamp*1000}"
        }
    
    def generate_cookies(self, 
                         scene: str = "all", 
                         timestamp: Optional[int] = None,
                         user_id: Optional[str] = None,
                         custom_fields: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        生成特定场景下的Cookie
        
        Args:
            scene: 场景类型，可选值: "all", "search", "video", "comment"
            timestamp: 时间戳，如果为None则使用当前时间
            user_id: 用户ID，如果为None则随机生成
            custom_fields: 自定义Cookie字段，将被添加到生成的Cookie中
            
        Returns:
            Dict[str, str]: 生成的Cookie字典
        """
        if timestamp is None:
            timestamp = int(time.time())
            
        if user_id is None:
            user_id = str(random.randint(250000001, 299999999))
        
        # 所有可能的Cookie字段
        all_cookies = {}
        all_cookies.update(self._generate_device_fingerprint(timestamp))
        all_cookies.update(self._generate_session_data(timestamp))
        all_cookies.update(self._generate_user_info(user_id, timestamp))
        all_cookies.update(self._generate_preferences())
        all_cookies.update(self._generate_misc(timestamp))
        
        # 如果是全部场景，返回所有Cookie
        if scene == "all":
            result = all_cookies
        else:
            # 筛选出特定场景需要的Cookie
            needed_keys = set(self.COOKIE_CONFIG["basic"])
            if scene in self.COOKIE_CONFIG:
                needed_keys.update(self.COOKIE_CONFIG[scene])
            
            result = {k: v for k, v in all_cookies.items() if k in needed_keys}
        
        # 添加自定义字段
        if custom_fields:
            result.update(custom_fields)
            
        return result
    
    @staticmethod
    def format_cookies(cookies: Dict[str, str]) -> str:
        """
        将Cookie字典格式化为字符串，按特定顺序
        
        Args:
            cookies: Cookie字典
        
        Returns:
            str: 格式化的Cookie字符串
        """
        # 定义Cookie的显示顺序
        cookie_order = [
            "buvid_fp_plain", "buvid4", "DedeUserID", "DedeUserID__ckMd5",
            "header_theme_version", "enable_web_push", "CURRENT_BLACKGAP", "PVID",
            "buvid3", "b_nut", "_uuid", "match_float_version", "LIVE_BUVID",
            "share_source_origin", "bsource", "rpdid", "CURRENT_QUALITY", 
            "enable_feed_channel", "hit-dyn-v2", "fingerprint", "timeMachine",
            "home_feed_column", "browser_resolution", 
            # 动态字段放在后面
            "bp_t_offset_", "bili_ticket", "bili_ticket_expires", 
            "CURRENT_FNVAL", "SESSDATA", "bili_jct", "sid", "b_lsid", "buvid_fp"
        ]
        
        # 先处理固定顺序的cookie
        cookie_parts = []
        used_keys = set()
        
        for key_prefix in cookie_order:
            for key in cookies.keys():
                if key == key_prefix or (key_prefix.endswith('_') and key.startswith(key_prefix)):
                    cookie_parts.append(f"{key}={cookies[key]}")
                    used_keys.add(key)
                    break
        
        # 添加剩余未排序的cookie
        for key, value in cookies.items():
            if key not in used_keys:
                cookie_parts.append(f"{key}={value}")
        
        return "; ".join(cookie_parts)

def get_random_cookies(scene: str = "all", 
                       timestamp: Optional[int] = None,
                       user_id: Optional[str] = None,
                       custom_fields: Optional[Dict[str, str]] = None,
                       format_as_string: bool = False) -> Union[Dict[str, str], str]:
    """
    获取随机Cookie
    
    Args:
        scene: 场景类型，可选值: "all", "search", "video", "comment"
        timestamp: 时间戳，如果为None则使用当前时间
        user_id: 用户ID，如果为None则随机生成
        custom_fields: 自定义Cookie字段
        format_as_string: 是否将结果格式化为字符串
    
    Returns:
        Dict[str, str] | str: Cookie字典或格式化的字符串
    """
    generator = BiliCookieGenerator()
    cookies = generator.generate_cookies(scene, timestamp, user_id, custom_fields)
    return generator.format_cookies(cookies) if format_as_string else cookies


# 使用示例
if __name__ == "__main__":
    # 获取不同场景的Cookie
    timestamp = int(time.time())
    
    # 搜索页Cookie
    search_cookie = get_random_cookies(scene="search", timestamp=timestamp, format_as_string=True)
    print("Search Cookie:", search_cookie, "\n")
    
    # # 视频页Cookie
    # video_cookie = get_random_cookies(scene="video", timestamp=timestamp, format_as_string=True)
    # print("Video Cookie:", video_cookie, "\n")
    
    # # 评论页Cookie
    # comment_cookie = get_random_cookies(scene="comment", timestamp=timestamp, format_as_string=True)
    # print("Comment Cookie:", comment_cookie, "\n")
    
    # # 所有Cookie
    # all_cookie = get_random_cookies(scene="all", timestamp=timestamp, format_as_string=True)
    # print("All Cookie:", all_cookie)

    # 测试搜索cookie的有效性
    url = 'https://search.bilibili.com/all?vt=97795598&keyword=%E7%BF%81%E6%B3%95%E7%BD%97%E6%96%AF&from_source=webtop_search&spm_id_from=333.1007&search_source=3'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Cookie': search_cookie,
        'Referer': 'https://www.bilibili.com/',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'TE': 'Trailers',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'DNT': '1',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="91", "Google Chrome";v="91"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'X-Requested-With': 'XMLHttpRequest',
    }
    import requests
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print("搜索Cookie有效")
        print("响应内容:", response.text[:1000])  # 打印前1000个字符
    else:
        print("搜索Cookie无效")



