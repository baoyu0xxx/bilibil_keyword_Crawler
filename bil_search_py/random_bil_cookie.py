import uuid
import hashlib
import time
import random
from typing import Dict, Tuple

class BiliCookieGenerator:
    @staticmethod
    def _generate_device_fingerprint() -> Tuple[str, str]:
        """生成设备指纹(buvid3和buvid4)"""
        buvid3 = f"{str(uuid.uuid4()).upper()}-{int(time.time())}infoc"
        uuid_part = str(uuid.uuid4()).upper()
        timestamp = int(time.time())
        hash_part = hashlib.md5(str(timestamp).encode()).hexdigest()[:6]
        buvid4 = f"{uuid_part}-{timestamp}-{hash_part}"
        return buvid3, buvid4

    @staticmethod
    def _generate_base_values() -> Dict[str, str]:
        """生成基础cookie值"""
        timestamp = int(time.time())
        return {
            "_uuid": f"{str(uuid.uuid4()).upper()}{timestamp}infoc",
            "b_lsid": f"{hashlib.md5(str(time.time()).encode()).hexdigest()[:8].upper()}_{hex(int(time.time() * 1000))[2:].upper()}",
            "fingerprint": hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest(),
            "SESSDATA": f"{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}%2C{timestamp + 15552000}%2C{hashlib.md5(str(random.random()).encode()).hexdigest()[:5]}%2A41",
            "bili_jct": hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()
        }

    @staticmethod
    def _generate_user_specific(user_id: str) -> Dict[str, str]:
        """生成用户特定的cookie值"""
        return {
            "DedeUserID": user_id,
            "DedeUserID__ckMd5": hashlib.md5(user_id.encode()).hexdigest()[:16],
            "sid": ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=8))
        }

    @staticmethod
    def _generate_common_values() -> Dict[str, str]:
        """生成通用固定值"""
        return {
            "FEED_LIVE_VERSION": "V8",
            "header_theme_version": "CLOSE",
            "enable_web_push": "DISABLE",
            "CURRENT_BLACKGAP": "0",
            "PVID": "2",
            "browser_resolution": "1528-704",
            "CURRENT_QUALITY": "80",
            "CURRENT_FNVAL": "16"
        }

    def generate_cookies(self, user_id: str = None) -> Dict[str, str]:
        """
        生成完整的cookie字典
        Args:
            user_id: 用户ID，如果为None则随机生成
        Returns:
            Dict[str, str]: 包含所有cookie键值对的字典
        """
        if user_id is None:
            user_id = str(random.randint(250000000, 299999999))

        cookies = {}
        
        # 添加设备指纹
        buvid3, buvid4 = self._generate_device_fingerprint()
        cookies.update({"buvid3": buvid3, "buvid4": buvid4})
        
        # 添加基础值
        cookies.update(self._generate_base_values())
        
        # 添加用户特定值
        cookies.update(self._generate_user_specific(user_id))
        
        # 添加通用值
        cookies.update(self._generate_common_values())
        
        # 添加时间相关值
        timestamp = int(time.time())
        cookies.update({
            "b_nut": str(timestamp),
            "LIVE_BUVID": f"AUTO{timestamp*1000}",
            f"bp_t_offset_{user_id}": str(random.randint(1000000000000000000, 9999999999999999999))
        })

        return cookies

    @staticmethod
    def format_cookies(cookies: Dict[str, str]) -> str:
        """
        将cookie字典格式化为字符串
        Args:
            cookies: cookie字典
        Returns:
            str: 格式化后的cookie字符串
        """
        return "; ".join([f"{key}={value}" for key, value in cookies.items()])

def get_random_cookies(format_as_string: bool = False) -> Dict[str, str] | str:
    """
    获取随机用户ID的cookie
    Args:
        format_as_string: 是否将结果格式化为字符串
    Returns:
        Dict[str, str] | str: cookie字典或格式化的字符串
    """
    generator = BiliCookieGenerator()
    cookies = generator.generate_cookies()
    return generator.format_cookies(cookies) if format_as_string else cookies

# 使用示例
if __name__ == "__main__":
    # 获取cookie字典
    cookie_dict = get_random_cookies()
    print("Cookie Dictionary:", cookie_dict)
    
    # 获取格式化的cookie字符串
    cookie_string = get_random_cookies(format_as_string=True)
    print("\nCookie String:", cookie_string)