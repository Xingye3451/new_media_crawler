"""
视频文件元数据管理系统
用于管理从各平台爬取的视频文件信息，支持多种存储方式
"""

import asyncio
import aiomysql
from typing import Optional, Dict, List
from datetime import datetime
import json
import os
import hashlib
from tools import utils
from var import media_crawler_db_var

class VideoFileManager:
    """视频文件元数据管理器"""
    
    def __init__(self):
        pass
    
    @property
    def db(self):
        """获取数据库连接"""
        return media_crawler_db_var.get()
    
    async def execute_ddl(self, sql: str):
        """执行DDL语句（如CREATE TABLE），不传递参数以避免格式化错误"""
        from var import db_conn_pool_var
        
        pool = db_conn_pool_var.get()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql)
    
    async def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            result = await self.db.query("SHOW TABLES LIKE %s", table_name)
            return len(result) > 0
        except Exception:
            return False
    
    async def init_video_files_tables(self):
        """初始化视频文件相关表"""
        
        # 视频文件元数据表
        video_files_table = """
        CREATE TABLE IF NOT EXISTS video_files (
            id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '文件ID',
            file_hash VARCHAR(64) UNIQUE NOT NULL COMMENT '文件哈希值(MD5)',
            
            -- 关联信息
            platform VARCHAR(20) NOT NULL COMMENT '来源平台',
            content_id VARCHAR(100) NOT NULL COMMENT '内容ID',
            task_id VARCHAR(100) COMMENT '关联任务ID',
            
            -- 基础信息
            original_url TEXT COMMENT '原始视频URL',
            title VARCHAR(500) COMMENT '视频标题',
            author_name VARCHAR(100) COMMENT '作者名称',
            duration INT COMMENT '视频时长(秒)',
            file_size BIGINT COMMENT '文件大小(字节)',
            
            -- 技术参数
            video_format VARCHAR(20) COMMENT '视频格式(mp4/webm等)',
            resolution VARCHAR(20) COMMENT '分辨率(1920x1080)',
            video_codec VARCHAR(50) COMMENT '视频编码(H.264/VP9等)',
            audio_codec VARCHAR(50) COMMENT '音频编码(AAC/Opus等)',
            bitrate INT COMMENT '码率(kbps)',
            fps DECIMAL(5,2) COMMENT '帧率',
            
            -- 存储信息
            storage_type ENUM('local', 'minio', 'url_only', 'temp') DEFAULT 'url_only' COMMENT '存储类型',
            local_path TEXT COMMENT '本地存储路径',
            minio_bucket VARCHAR(100) COMMENT 'MinIO桶名',
            minio_object_key VARCHAR(500) COMMENT 'MinIO对象键',
            cdn_url TEXT COMMENT 'CDN访问地址',
            
            -- 状态信息
            download_status ENUM('pending', 'downloading', 'completed', 'failed', 'expired') DEFAULT 'pending' COMMENT '下载状态',
            download_progress DECIMAL(5,2) DEFAULT 0 COMMENT '下载进度(%)',
            download_error TEXT COMMENT '下载错误信息',
            download_attempts INT DEFAULT 0 COMMENT '下载尝试次数',
            
            -- 访问信息
            download_count INT DEFAULT 0 COMMENT '下载次数',
            last_accessed_at TIMESTAMP NULL COMMENT '最后访问时间',
            expiry_date TIMESTAMP NULL COMMENT '过期时间',
            
            -- 元数据
            metadata JSON COMMENT '扩展元数据',
            thumbnail_url TEXT COMMENT '缩略图URL',
            thumbnail_path TEXT COMMENT '缩略图本地路径',
            
            -- 时间戳
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            INDEX idx_platform_content (platform, content_id),
            INDEX idx_task_id (task_id),
            INDEX idx_storage_type (storage_type),
            INDEX idx_download_status (download_status),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='视频文件元数据表';
        """
        
        # 文件下载任务表
        download_tasks_table = """
        CREATE TABLE IF NOT EXISTS video_download_tasks (
            id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '任务ID',
            batch_id VARCHAR(100) COMMENT '批次ID',
            file_id BIGINT NOT NULL COMMENT '文件ID',
            
            -- 下载配置
            target_storage ENUM('local', 'minio') NOT NULL COMMENT '目标存储',
            target_path TEXT COMMENT '目标路径',
            quality_preset VARCHAR(20) COMMENT '质量预设',
            max_file_size BIGINT COMMENT '最大文件大小',
            
            -- 任务状态
            status ENUM('pending', 'downloading', 'completed', 'failed', 'cancelled') DEFAULT 'pending' COMMENT '任务状态',
            progress DECIMAL(5,2) DEFAULT 0 COMMENT '进度(%)',
            error_message TEXT COMMENT '错误信息',
            attempts INT DEFAULT 0 COMMENT '尝试次数',
            
            -- 结果信息
            final_path TEXT COMMENT '最终存储路径',
            final_size BIGINT COMMENT '最终文件大小',
            download_duration INT COMMENT '下载耗时(秒)',
            
            -- 时间戳
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            started_at TIMESTAMP NULL COMMENT '开始时间',
            completed_at TIMESTAMP NULL COMMENT '完成时间',
            
            FOREIGN KEY (file_id) REFERENCES video_files(id) ON DELETE CASCADE,
            INDEX idx_batch_id (batch_id),
            INDEX idx_status (status),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='视频下载任务表';
        """
        
        # 存储统计表
        storage_stats_table = """
        CREATE TABLE IF NOT EXISTS video_storage_stats (
            id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'ID',
            date DATE NOT NULL COMMENT '日期',
            platform VARCHAR(20) NOT NULL COMMENT '平台',
            storage_type VARCHAR(20) NOT NULL COMMENT '存储类型',
            
            -- 统计数据
            file_count INT DEFAULT 0 COMMENT '文件数量',
            total_size BIGINT DEFAULT 0 COMMENT '总大小(字节)',
            download_count INT DEFAULT 0 COMMENT '下载次数',
            success_count INT DEFAULT 0 COMMENT '成功次数',
            failed_count INT DEFAULT 0 COMMENT '失败次数',
            
            -- 时间戳
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            UNIQUE KEY uk_date_platform_storage (date, platform, storage_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='存储统计表';
        """
        
        try:
            # 定义表名和对应的SQL
            tables_to_create = [
                ("video_files", video_files_table),
                ("video_download_tasks", download_tasks_table), 
                ("video_storage_stats", storage_stats_table)
            ]
            
            created_tables = []
            existing_tables = []
            
            # 检查表是否存在，只创建不存在的表
            for table_name, table_sql in tables_to_create:
                if await self.table_exists(table_name):
                    existing_tables.append(table_name)
                    utils.logger.debug(f"[VIDEO_FILES] 表 {table_name} 已存在，跳过创建")
                else:
                    # 移除 IF NOT EXISTS 语句以避免警告
                    clean_sql = table_sql.replace("CREATE TABLE IF NOT EXISTS", "CREATE TABLE")
                    await self.execute_ddl(clean_sql)
                    created_tables.append(table_name)
                    utils.logger.info(f"[VIDEO_FILES] 成功创建表: {table_name}")
            
            if created_tables:
                utils.logger.info(f"[VIDEO_FILES] 创建了 {len(created_tables)} 个新表: {', '.join(created_tables)}")
            
            if existing_tables:
                utils.logger.info(f"[VIDEO_FILES] 跳过了 {len(existing_tables)} 个已存在的表: {', '.join(existing_tables)}")
            
            utils.logger.info("[VIDEO_FILES] 视频文件相关表初始化完成")
            return True
            
        except Exception as e:
            utils.logger.error(f"[VIDEO_FILES] 初始化表失败: {e}")
            return False
    
    async def save_video_metadata(self, video_info: Dict) -> Optional[int]:
        """保存视频元数据"""
        try:
            # 生成文件哈希
            content_str = f"{video_info['platform']}_{video_info['content_id']}_{video_info.get('original_url', '')}"
            file_hash = hashlib.md5(content_str.encode()).hexdigest()
            
            # 检查是否已存在
            existing = await self.db.query(
                "SELECT id FROM video_files WHERE file_hash = %s",
                file_hash
            )
            
            if existing:
                utils.logger.info(f"[VIDEO_FILES] 文件已存在: {file_hash}")
                return existing[0]['id']
            
            # 使用item_to_table方法插入并获取ID
            video_data = {
                'file_hash': file_hash,
                'platform': video_info['platform'],
                'content_id': video_info['content_id'],
                'task_id': video_info.get('task_id'),
                'original_url': video_info.get('original_url'),
                'title': video_info.get('title', ''),
                'author_name': video_info.get('author_name', ''),
                'duration': video_info.get('duration'),
                'file_size': video_info.get('file_size'),
                'video_format': video_info.get('video_format', 'mp4'),
                'resolution': video_info.get('resolution'),
                'video_codec': video_info.get('video_codec'),
                'audio_codec': video_info.get('audio_codec'),
                'bitrate': video_info.get('bitrate'),
                'fps': video_info.get('fps'),
                'storage_type': video_info.get('storage_type', 'url_only'),
                'metadata': json.dumps(video_info.get('metadata', {})),
                'thumbnail_url': video_info.get('thumbnail_url')
            }
            
            file_id = await self.db.item_to_table('video_files', video_data)
            
            utils.logger.info(f"[VIDEO_FILES] 保存视频元数据成功: {file_id}")
            return file_id
            
        except Exception as e:
            utils.logger.error(f"[VIDEO_FILES] 保存视频元数据失败: {e}")
            return None
    
    async def create_download_task(self, file_id: int, target_storage: str, config: Dict) -> Optional[int]:
        """创建下载任务"""
        try:
            # 使用item_to_table方法插入并获取ID
            task_data = {
                'file_id': file_id,
                'batch_id': config.get('batch_id'),
                'target_storage': target_storage,
                'target_path': config.get('target_path'),
                'quality_preset': config.get('quality_preset', 'auto'),
                'max_file_size': config.get('max_file_size')
            }
            
            task_id = await self.db.item_to_table('video_download_tasks', task_data)
            utils.logger.info(f"[VIDEO_FILES] 创建下载任务成功: {task_id}")
            return task_id
            
        except Exception as e:
            utils.logger.error(f"[VIDEO_FILES] 创建下载任务失败: {e}")
            return None
    
    async def get_files_by_task(self, task_id: str) -> List[Dict]:
        """根据任务ID获取文件列表"""
        try:
            sql = """
            SELECT * FROM video_files 
            WHERE task_id = %s 
            ORDER BY created_at DESC
            """
            
            results = await self.db.query(sql, task_id)
            return [dict(row) for row in results]
            
        except Exception as e:
            utils.logger.error(f"[VIDEO_FILES] 获取任务文件列表失败: {e}")
            return []
    
    async def get_files_by_platform(self, platform: str, limit: int = 100) -> List[Dict]:
        """根据平台获取文件列表"""
        try:
            sql = """
            SELECT * FROM video_files 
            WHERE platform = %s 
            ORDER BY created_at DESC 
            LIMIT %s
            """
            
            results = await self.db.query(sql, platform, limit)
            return [dict(row) for row in results]
            
        except Exception as e:
            utils.logger.error(f"[VIDEO_FILES] 获取平台文件列表失败: {e}")
            return []
    
    async def update_download_status(self, file_id: int, status: str, progress: float = None, error: str = None):
        """更新下载状态"""
        try:
            update_fields = ["download_status = %s"]
            values = [status]
            
            if progress is not None:
                update_fields.append("download_progress = %s")
                values.append(progress)
            
            if error:
                update_fields.append("download_error = %s")
                values.append(error)
            
            update_fields.append("download_attempts = download_attempts + 1")
            values.append(file_id)
            
            sql = f"UPDATE video_files SET {', '.join(update_fields)} WHERE id = %s"
            await self.db.execute(sql, *values)
            
        except Exception as e:
            utils.logger.error(f"[VIDEO_FILES] 更新下载状态失败: {e}")
    
    async def get_storage_stats(self, platform: str = None) -> Dict:
        """获取存储统计"""
        try:
            where_clause = "WHERE platform = %s" if platform else ""
            values = [platform] if platform else []
            
            sql = f"""
            SELECT 
                storage_type,
                COUNT(*) as file_count,
                SUM(file_size) as total_size,
                SUM(download_count) as total_downloads
            FROM video_files 
            {where_clause}
            GROUP BY storage_type
            """
            
            results = await self.db.query(sql, *values)
            
            stats = {}
            for row in results:
                stats[row['storage_type']] = {
                    'file_count': row['file_count'],
                    'total_size': row['total_size'] or 0,
                    'total_downloads': row['total_downloads'] or 0
                }
            
            return stats
            
        except Exception as e:
            utils.logger.error(f"[VIDEO_FILES] 获取存储统计失败: {e}")
            return {}
    
    async def cleanup_expired_files(self):
        """清理过期文件"""
        try:
            # 查找过期文件
            sql = """
            SELECT id, local_path, minio_bucket, minio_object_key 
            FROM video_files 
            WHERE expiry_date IS NOT NULL AND expiry_date < NOW()
            """
            
            expired_files = await self.db.query(sql)
            
            cleaned_count = 0
            for file_info in expired_files:
                try:
                    # 删除本地文件
                    if file_info['local_path'] and os.path.exists(file_info['local_path']):
                        os.remove(file_info['local_path'])
                    
                    # 删除MinIO文件 (需要MinIO客户端)
                    # if file_info['minio_bucket'] and file_info['minio_object_key']:
                    #     await minio_client.remove_object(file_info['minio_bucket'], file_info['minio_object_key'])
                    
                    # 更新数据库记录
                    await self.db.execute(
                        "UPDATE video_files SET storage_type = 'url_only', local_path = NULL, minio_bucket = NULL, minio_object_key = NULL WHERE id = %s",
                        file_info['id']
                    )
                    
                    cleaned_count += 1
                    
                except Exception as e:
                    utils.logger.error(f"[VIDEO_FILES] 清理文件失败 {file_info['id']}: {e}")
            
            utils.logger.info(f"[VIDEO_FILES] 清理过期文件完成: {cleaned_count} 个文件")
            return cleaned_count
            
        except Exception as e:
            utils.logger.error(f"[VIDEO_FILES] 清理过期文件失败: {e}")
            return 0


# 使用示例函数
async def example_usage():
    """使用示例"""
    
    # 这里需要替换为实际的数据库连接
    # db = await get_database_connection()
    # file_manager = VideoFileManager(db)
    
    # 初始化表
    # await file_manager.init_video_files_tables()
    
    # 保存视频元数据
    video_info = {
        'platform': 'xhs',
        'content_id': '12345',
        'task_id': 'task_001',
        'original_url': 'https://example.com/video.mp4',
        'title': '测试视频',
        'author_name': '测试作者',
        'duration': 120,
        'file_size': 1024000,
        'video_format': 'mp4',
        'resolution': '1920x1080',
        'storage_type': 'url_only'
    }
    
    # file_id = await file_manager.save_video_metadata(video_info)
    
    # 创建下载任务
    download_config = {
        'batch_id': 'batch_001',
        'target_path': '/downloads/',
        'quality_preset': 'high',
        'max_file_size': 100 * 1024 * 1024  # 100MB
    }
    
    # task_id = await file_manager.create_download_task(file_id, 'local', download_config)
    
    print("视频文件管理系统示例完成")

if __name__ == "__main__":
    asyncio.run(example_usage()) 