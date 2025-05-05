import pandas as pd
import numpy as np
from db_handler import DatabaseHandler
from crawl_utils import extract_comment_data

def save_videos_to_mysql(videos, config):
    """
    将视频数据保存到 MySQL 数据库
    
    Args:
        videos: 视频数据列表
        config: 包含db_config配置的字典
    """
    # 确保config包含有效的db_config配置
    if not config.get("db_config"):
        print("错误: 缺少数据库配置，请在config中设置db_config")
        return False
        
    # 使用整个config对象初始化数据库处理器
    db_handler = DatabaseHandler(config)
    if not db_handler.connect() or not db_handler.init_database():
        print("数据库初始化失败，无法保存视频数据")
        return False

    try:
        db_handler.insert_videos(videos)
        print(f"成功保存 {len(videos)} 条视频数据到数据库")
    except Exception as e:
        print(f"保存视频数据到数据库失败: {str(e)}")
    finally:
        db_handler.close()
    return True

def save_comments_to_mysql(comment_files, config):
    """
    将评论数据保存到 MySQL 数据库
    
    Args:
        comment_files: 评论文件列表，每项为 (bvid, aid, csv_path) 的元组
        config: 包含db_config配置的字典
    """
    # 确保config包含有效的db_config配置
    if not config.get("db_config"):
        print("错误: 缺少数据库配置，请在config中设置db_config") 
        return False
        
    # 使用整个config对象初始化数据库处理器
    db_handler = DatabaseHandler(config)
    if not db_handler.connect():
        print("数据库连接失败，无法保存评论数据")
        return False

    try:
        for bvid, aid, csv_path in comment_files:
            comments_data = extract_comment_data(csv_path)
            if comments_data:
                db_handler.insert_comments(comments_data, bvid, aid)
        print(f"成功保存 {len(comment_files)} 个评论文件到数据库")
    except Exception as e:
        print(f"保存评论数据到数据库失败: {str(e)}")
    finally:
        db_handler.close()
    return True


# 测试
if __name__ == "__main__":
    import pandas as pd
    from config import config
    
    try:
        # 检查配置是否正确
        if not config.get("use_database"):
            print("警告：配置文件中 use_database 设置为 False，正在将其临时设置为 True 以进行测试")
            config["use_database"] = True
            
        # 确保数据库配置存在
        if not config.get("db_config"):
            raise ValueError("缺少数据库配置信息，请在 config.py 中设置 db_config")
            
        # 初始化数据库处理器
        db_handler = DatabaseHandler(config)

        # 读取测试数据
        try:
            videos_df = pd.read_csv("bilibili_search.csv")

            # 简单预处理：删除duration 为非纯数字的行
            videos_df = videos_df[videos_df["duration"].apply(lambda x: str(x).isdigit())]
            videos_df["duration"] = videos_df["duration"].astype(int)
            
            
            # 将DataFrame转换为适合数据库导入的格式
            videos = []
            for _, row in videos_df.iterrows():
                # 安全地获取字段值，避免 NaN 或 float 类型错误
                def safe_get(field, default="", max_length=None):
                    value = row.get(field, default)
                    # 检查是否为 NaN 值
                    if isinstance(value, float) and np.isnan(value):
                        return default
                    # 如果需要限制长度且值是字符串类型
                    if max_length and isinstance(value, str) and len(value) > max_length:
                        return value[:max_length]
                    return value
                
                # 处理可能的数值类型字段
                def safe_int(field, default=0):
                    value = row.get(field, default)
                    if pd.isna(value):
                        return default
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return default
                
                # 构建视频数据字典
                video_data = {
                    "video": {
                        "bvid": safe_get("bvid"),
                        "aid": safe_int("aid"),
                        "title": safe_get("title", "", 255),
                        "cover_url": safe_get("cover_url", "", 255),
                        "tid": safe_int("tid"),
                        "tname": safe_get("tname", "", 50),
                        "description": safe_get("description", ""),
                        "pubdate": safe_get("pubdate", ""),
                        "ctime": safe_get("ctime", ""),
                        "duration": safe_int("duration"),
                        "view_count": safe_int("view_count"),
                        "danmaku_count": safe_int("danmaku_count"),
                        "reply_count": safe_int("reply_count"),
                        "favorite_count": safe_int("favorite_count"),
                        "coin_count": safe_int("coin_count"),
                        "share_count": safe_int("share_count"),
                        "like_count": safe_int("like_count"),
                        "owner_mid": safe_int("owner_mid")
                    },
                    "owner": {
                        "mid": safe_int("owner_mid"),
                        "name": safe_get("owner_name", "", 100),
                        "face_url": safe_get("owner_face", "", 255)
                    }
                }
                videos.append(video_data)
            
            # 保存到数据库
            save_videos_to_mysql(videos, config)
            
        except FileNotFoundError:
            print("找不到 bilibili_search.csv 文件，无法进行测试")
        except Exception as e:
            print(f"测试过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"初始化测试环境失败: {str(e)}")