import mysql.connector
from mysql.connector import Error
import pandas as pd
from tqdm import tqdm
import time
import re


class DatabaseHandler:
    """处理数据库相关操作的工具类"""
    
    def __init__(self, config):
        """
        初始化数据库处理器
        
        Args:
            config: 数据库配置信息，包含连接信息和表名
        """
        self.db_config = config["db_config"]
        self.db_tables = config["db_tables"]
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = mysql.connector.connect(
                host=self.db_config["host"],
                port=self.db_config["port"],
                user=self.db_config["user"],
                password=self.db_config["password"],
                database=self.db_config["database"]
            )
            
            if self.connection.is_connected():
                self.cursor = self.connection.cursor()
                print(f"已成功连接到MySQL数据库: {self.db_config['database']}")
                return True
        except Error as e:
            print(f"连接MySQL数据库时发生错误: {e}")
            return False
            
    def close(self):
        """关闭数据库连接"""
        if self.connection and self.connection.is_connected():
            if self.cursor:
                self.cursor.close()
            self.connection.close()
            print("MySQL数据库连接已关闭")
    
    def init_database(self):
        """初始化数据库表结构"""
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                return False
        
        try:
            # 创建视频信息表
            video_table = f"""
            CREATE TABLE IF NOT EXISTS {self.db_tables['videos']} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bvid VARCHAR(20) UNIQUE NOT NULL,
                aid BIGINT,
                title VARCHAR(255),
                cover_url VARCHAR(255),
                tid INT,
                tname VARCHAR(50),
                description TEXT,
                pubdate DATETIME,
                ctime DATETIME,
                duration INT,
                view_count INT,
                danmaku_count INT,
                reply_count INT,
                favorite_count INT,
                coin_count INT,
                share_count INT,
                like_count INT,
                owner_mid BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_bvid (bvid),
                INDEX idx_aid (aid),
                INDEX idx_owner_mid (owner_mid),
                INDEX idx_pubdate (pubdate)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            
            # 创建UP主信息表
            owner_table = f"""
            CREATE TABLE IF NOT EXISTS {self.db_tables['owners']} (
                mid BIGINT PRIMARY KEY,
                name VARCHAR(100),
                face_url VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_name (name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            
            # 创建评论信息表
            comment_table = f"""
            CREATE TABLE IF NOT EXISTS {self.db_tables['comments']} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                rpid BIGINT,
                parent_id BIGINT,
                oid BIGINT,
                bvid VARCHAR(20),
                mid BIGINT,
                username VARCHAR(100),
                level INT,
                gender VARCHAR(10),
                content TEXT,
                comment_time DATETIME,
                reply_count INT,
                like_count INT,
                ip_location VARCHAR(50),
                is_vip VARCHAR(5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_rpid (rpid),
                INDEX idx_bvid (bvid),
                INDEX idx_mid (mid)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            
            # 执行创建表操作
            self.cursor.execute(video_table)
            self.cursor.execute(owner_table)
            self.cursor.execute(comment_table)
            self.connection.commit()
            
            print(f"已成功创建/确认表结构: {list(self.db_tables.values())}")
            return True
            
        except Error as e:
            print(f"初始化数据库结构时发生错误: {e}")
            return False
    
    def insert_videos(self, videos_data):
        """
        插入视频数据到数据库
        
        Args:
            videos_data: 包含视频信息的字典列表
        """
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                return
        
        videos_table = self.db_tables['videos']
        owners_table = self.db_tables['owners']
        
        # 准备批量插入的数据
        videos_to_insert = []
        owners_to_insert = []
        owners_seen = set()  # 用于去重UP主
        
        for video in tqdm(videos_data, desc="处理视频数据"):
            video_info = video["video"]
            owner_info = video["owner"]
            
            # 处理视频信息
            videos_to_insert.append((
                video_info.get("bvid", ""),
                video_info.get("aid", 0),
                video_info.get("title", "")[:255],  # 限制标题长度
                video_info.get("cover_url", "")[:255],
                video_info.get("tid", 0),
                video_info.get("tname", "")[:50],
                video_info.get("description", ""),
                self._parse_datetime(video_info.get("pubdate", "")),
                self._parse_datetime(video_info.get("ctime", "")),
                video_info.get("duration", 0),
                video_info.get("view_count", 0),
                video_info.get("danmaku_count", 0),
                video_info.get("reply_count", 0),
                video_info.get("favorite_count", 0),
                video_info.get("coin_count", 0),
                video_info.get("share_count", 0),
                video_info.get("like_count", 0),
                video_info.get("owner_mid", 0)
            ))
            
            # 处理UP主信息（确保不重复）
            owner_mid = owner_info.get("mid", 0)
            if owner_mid > 0 and owner_mid not in owners_seen:
                owners_to_insert.append((
                    owner_mid,
                    owner_info.get("name", "")[:100],
                    owner_info.get("face_url", "")[:255]
                ))
                owners_seen.add(owner_mid)
        
        try:
            # 插入视频信息
            if videos_to_insert:
                video_insert_query = f"""
                INSERT INTO {videos_table} 
                (bvid, aid, title, cover_url, tid, tname, description, pubdate, 
                 ctime, duration, view_count, danmaku_count, reply_count, 
                 favorite_count, coin_count, share_count, like_count, owner_mid)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    aid = VALUES(aid),
                    title = VALUES(title),
                    cover_url = VALUES(cover_url),
                    tid = VALUES(tid),
                    tname = VALUES(tname),
                    description = VALUES(description),
                    pubdate = VALUES(pubdate),
                    ctime = VALUES(ctime),
                    duration = VALUES(duration),
                    view_count = VALUES(view_count),
                    danmaku_count = VALUES(danmaku_count),
                    reply_count = VALUES(reply_count),
                    favorite_count = VALUES(favorite_count),
                    coin_count = VALUES(coin_count),
                    share_count = VALUES(share_count),
                    like_count = VALUES(like_count),
                    owner_mid = VALUES(owner_mid),
                    updated_at = CURRENT_TIMESTAMP
                """
                self.cursor.executemany(video_insert_query, videos_to_insert)
            
            # 插入UP主信息
            if owners_to_insert:
                owner_insert_query = f"""
                INSERT INTO {owners_table} 
                (mid, name, face_url)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    name = VALUES(name),
                    face_url = VALUES(face_url),
                    updated_at = CURRENT_TIMESTAMP
                """
                self.cursor.executemany(owner_insert_query, owners_to_insert)
            
            self.connection.commit()
            print(f"成功导入 {len(videos_to_insert)} 条视频数据和 {len(owners_to_insert)} 条UP主数据")
            
        except Error as e:
            print(f"插入数据时发生错误: {e}")
            self.connection.rollback()
    
    def insert_comments(self, comments_data, bvid, aid):
        """
        插入评论数据到数据库
        
        Args:
            comments_data: 评论数据列表
            bvid: 视频BV号
            aid: 视频AV号（OID）
        """
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                return
        
        comments_table = self.db_tables['comments']
        
        # 准备批量插入的数据
        comments_to_insert = []
        
        for comment in comments_data:
            # 处理评论信息（根据CSV文件格式）
            # 假设comment是一个包含15个元素的列表，对应CSV的15列
            if len(comment) >= 15:
                try:
                    # 格式: [序号, 上级评论ID, 评论ID, 用户ID, 用户名, 用户等级, 性别, 评论内容, 评论时间, 回复数, 点赞数, 个性签名, IP属地, 是否是大会员, 头像]
                    rpid = comment[2]  # 评论ID
                    parent_id = comment[1] if comment[1] else 0  # 上级评论ID
                    mid = comment[3]  # 用户ID
                    username = comment[4][:100] if comment[4] else ""  # 用户名
                    level = int(comment[5]) if comment[5] and comment[5].isdigit() else 0  # 用户等级
                    gender = comment[6][:10] if comment[6] else ""  # 性别
                    content = comment[7]  # 评论内容
                    comment_time = self._parse_datetime(comment[8])  # 评论时间
                    reply_count = int(comment[9]) if comment[9] and str(comment[9]).isdigit() else 0  # 回复数
                    like_count = int(comment[10]) if comment[10] and str(comment[10]).isdigit() else 0  # 点赞数
                    ip_location = comment[12][:50] if comment[12] else ""  # IP属地
                    is_vip = comment[13][:5] if comment[13] else "否"  # 是否是大会员
                    
                    comments_to_insert.append((
                        rpid, parent_id, aid, bvid, mid, username, level, gender,
                        content, comment_time, reply_count, like_count, ip_location, is_vip
                    ))
                except (ValueError, TypeError) as e:
                    print(f"处理评论数据时出错: {e}, 数据: {comment}")
                    continue
        
        try:
            if comments_to_insert:
                comment_insert_query = f"""
                INSERT INTO {comments_table} 
                (rpid, parent_id, oid, bvid, mid, username, level, gender,
                 content, comment_time, reply_count, like_count, ip_location, is_vip)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    parent_id = VALUES(parent_id),
                    username = VALUES(username),
                    level = VALUES(level),
                    gender = VALUES(gender),
                    content = VALUES(content),
                    comment_time = VALUES(comment_time),
                    reply_count = VALUES(reply_count),
                    like_count = VALUES(like_count),
                    ip_location = VALUES(ip_location),
                    is_vip = VALUES(is_vip),
                    created_at = CURRENT_TIMESTAMP
                """
                
                # 分批执行，每批500条
                batch_size = 500
                for i in range(0, len(comments_to_insert), batch_size):
                    batch = comments_to_insert[i:i+batch_size]
                    self.cursor.executemany(comment_insert_query, batch)
                    self.connection.commit()
                    
                print(f"成功导入 {len(comments_to_insert)} 条评论数据，视频BV号: {bvid}")
                
        except Error as e:
            print(f"插入评论数据时发生错误: {e}")
            self.connection.rollback()
    
    def _parse_datetime(self, date_str):
        """将日期字符串解析为数据库兼容的日期时间格式"""
        if not date_str:
            return None
            
        # 如果已经是datetime格式则转换为字符串
        if hasattr(date_str, 'strftime'):
            return date_str.strftime('%Y-%m-%d %H:%M:%S')
            
        # 尝试解析不同格式的日期字符串
        formats = [
            '%Y-%m-%d %H:%M:%S',  # 标准格式
            '%Y-%m-%d',          # 仅日期
            '%Y/%m/%d %H:%M:%S',  # 斜杠分隔
            '%Y/%m/%d',          # 仅日期，斜杠分隔
        ]
        
        for fmt in formats:
            try:
                return time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(str(date_str), fmt))
            except ValueError:
                continue
        
        # 处理特殊格式，如"3天前"、"1小时前"等
        if isinstance(date_str, str):
            now = time.localtime()
            
            # 匹配"X天前"
            days_match = re.search(r'(\d+)\s*天前', date_str)
            if days_match:
                days = int(days_match.group(1))
                past = time.localtime(time.time() - days * 86400)
                return time.strftime('%Y-%m-%d 00:00:00', past)
            
            # 匹配"X小时前"
            hours_match = re.search(r'(\d+)\s*小时前', date_str)
            if hours_match:
                hours = int(hours_match.group(1))
                past = time.localtime(time.time() - hours * 3600)
                return time.strftime('%Y-%m-%d %H:00:00', past)
            
            # 匹配"X分钟前"
            minutes_match = re.search(r'(\d+)\s*分钟前', date_str)
            if minutes_match:
                minutes = int(minutes_match.group(1))
                past = time.localtime(time.time() - minutes * 60)
                return time.strftime('%Y-%m-%d %H:%M:00', past)
        
        # 无法解析，返回NULL
        return None