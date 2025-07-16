"""
视频文件管理API
提供视频文件下载、存储转换、批量管理等功能
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, File, UploadFile
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Union
import asyncio
import os
import json
from datetime import datetime, timedelta
import minio
from minio import Minio
from tools import utils
from db_video_files import VideoFileManager

router = APIRouter(prefix="/api/video-files", tags=["视频文件管理"])

# Pydantic 模型
class VideoFileInfo(BaseModel):
    platform: str
    content_id: str
    task_id: Optional[str] = None
    original_url: Optional[str] = None
    title: Optional[str] = None
    author_name: Optional[str] = None
    duration: Optional[int] = None
    file_size: Optional[int] = None
    video_format: Optional[str] = "mp4"
    resolution: Optional[str] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    bitrate: Optional[int] = None
    fps: Optional[float] = None
    storage_type: Optional[str] = "url_only"
    metadata: Optional[Dict] = {}
    thumbnail_url: Optional[str] = None

class DownloadTaskConfig(BaseModel):
    target_storage: str  # 'local' or 'minio'
    target_path: Optional[str] = None
    quality_preset: Optional[str] = "auto"
    max_file_size: Optional[int] = None
    batch_id: Optional[str] = None

class StorageTransferConfig(BaseModel):
    file_ids: List[int]
    target_storage: str  # 'local', 'minio', 'download'
    target_path: Optional[str] = None
    quality_preset: Optional[str] = "auto"
    auto_cleanup: Optional[bool] = False

# 全局变量
file_manager = None
minio_client = None

def init_video_files_api(minio_config=None):
    """初始化视频文件API"""
    global file_manager, minio_client
    
    file_manager = VideoFileManager()
    
    if minio_config:
        minio_client = Minio(
            minio_config['endpoint'],
            access_key=minio_config['access_key'],
            secret_key=minio_config['secret_key'],
            secure=minio_config.get('secure', False)
        )

@router.post("/save-metadata")
async def save_video_metadata(video_info: VideoFileInfo):
    """保存视频元数据"""
    try:
        if not file_manager:
            raise HTTPException(status_code=500, detail="文件管理器未初始化")
        
        file_id = await file_manager.save_video_metadata(video_info.dict())
        
        if file_id:
            return {
                "success": True,
                "file_id": file_id,
                "message": "视频元数据保存成功"
            }
        else:
            raise HTTPException(status_code=500, detail="保存视频元数据失败")
            
    except Exception as e:
        utils.logger.error(f"[API] 保存视频元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_video_files(
    platform: Optional[str] = Query(None, description="平台筛选"),
    task_id: Optional[str] = Query(None, description="任务ID筛选"),
    storage_type: Optional[str] = Query(None, description="存储类型筛选"),
    limit: int = Query(50, description="返回数量限制"),
    offset: int = Query(0, description="偏移量")
):
    """获取视频文件列表"""
    try:
        if not file_manager:
            raise HTTPException(status_code=500, detail="文件管理器未初始化")
        
        # 构建查询条件
        where_conditions = []
        params = []
        
        if platform:
            where_conditions.append("platform = %s")
            params.append(platform)
        
        if task_id:
            where_conditions.append("task_id = %s")
            params.append(task_id)
        
        if storage_type:
            where_conditions.append("storage_type = %s")
            params.append(storage_type)
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # 查询文件列表
        sql = f"""
        SELECT 
            id, file_hash, platform, content_id, task_id, title, author_name,
            duration, file_size, video_format, resolution, storage_type,
            download_status, download_progress, download_count, thumbnail_url,
            created_at, updated_at
        FROM video_files 
        {where_clause}
        ORDER BY created_at DESC 
        LIMIT %s OFFSET %s
        """
        
        params.extend([limit, offset])
        results = await file_manager.db.query(sql, *params)
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as total FROM video_files {where_clause}"
        count_params = params[:-2]  # 除去limit和offset
        total_result = await file_manager.db.query(count_sql, *count_params)
        total = total_result[0]['total'] if total_result else 0
        
        return {
            "success": True,
            "data": [dict(row) for row in results],
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        utils.logger.error(f"[API] 获取视频文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-download-task")
async def create_download_task(file_id: int, config: DownloadTaskConfig, background_tasks: BackgroundTasks):
    """创建下载任务"""
    try:
        if not file_manager:
            raise HTTPException(status_code=500, detail="文件管理器未初始化")
        
        # 检查文件是否存在
        file_info = await file_manager.db.query(
            "SELECT * FROM video_files WHERE id = %s", file_id
        )
        
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        file_info = dict(file_info[0])
        
        # 创建下载任务
        task_id = await file_manager.create_download_task(
            file_id, config.target_storage, config.dict()
        )
        
        if not task_id:
            raise HTTPException(status_code=500, detail="创建下载任务失败")
        
        # 启动后台下载任务
        background_tasks.add_task(
            execute_download_task, task_id, file_info, config.dict()
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "下载任务创建成功，正在后台执行"
        }
        
    except Exception as e:
        utils.logger.error(f"[API] 创建下载任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transfer-storage")
async def transfer_storage(config: StorageTransferConfig, background_tasks: BackgroundTasks):
    """批量转换存储方式"""
    try:
        if not file_manager:
            raise HTTPException(status_code=500, detail="文件管理器未初始化")
        
        # 生成批次ID
        batch_id = f"transfer_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        task_ids = []
        for file_id in config.file_ids:
            # 检查文件是否存在
            file_info = await file_manager.db.query(
                "SELECT * FROM video_files WHERE id = %s", file_id
            )
            
            if not file_info:
                continue
            
            # 创建转换任务
            task_config = {
                'target_storage': config.target_storage,
                'target_path': config.target_path,
                'quality_preset': config.quality_preset,
                'batch_id': batch_id
            }
            
            task_id = await file_manager.create_download_task(
                file_id, config.target_storage, task_config
            )
            
            if task_id:
                task_ids.append(task_id)
                
                # 启动后台任务
                background_tasks.add_task(
                    execute_download_task, task_id, dict(file_info[0]), task_config
                )
        
        return {
            "success": True,
            "batch_id": batch_id,
            "task_count": len(task_ids),
            "task_ids": task_ids,
            "message": f"批量转换任务创建成功，共 {len(task_ids)} 个任务"
        }
        
    except Exception as e:
        utils.logger.error(f"[API] 批量转换存储失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{file_id}")
async def download_file(file_id: int):
    """下载文件"""
    try:
        if not file_manager:
            raise HTTPException(status_code=500, detail="文件管理器未初始化")
        
        # 获取文件信息
        file_info = await file_manager.db.query(
            "SELECT * FROM video_files WHERE id = %s", file_id
        )
        
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        file_info = dict(file_info[0])
        
        # 更新下载计数
        await file_manager.db.execute(
            "UPDATE video_files SET download_count = download_count + 1, last_accessed_at = NOW() WHERE id = %s",
            file_id
        )
        
        # 根据存储类型返回文件
        if file_info['storage_type'] == 'local' and file_info['local_path']:
            if os.path.exists(file_info['local_path']):
                filename = f"{file_info['platform']}_{file_info['content_id']}.{file_info['video_format']}"
                return FileResponse(
                    file_info['local_path'],
                    filename=filename,
                    media_type='application/octet-stream'
                )
            else:
                raise HTTPException(status_code=404, detail="本地文件不存在")
        
        elif file_info['storage_type'] == 'minio' and minio_client:
            try:
                # 生成MinIO预签名下载URL
                download_url = minio_client.presigned_get_object(
                    file_info['minio_bucket'],
                    file_info['minio_object_key'],
                    expires=timedelta(hours=1)
                )
                
                return {
                    "success": True,
                    "download_url": download_url,
                    "expires_in": 3600,
                    "message": "MinIO下载链接生成成功"
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"生成MinIO下载链接失败: {e}")
        
        elif file_info['storage_type'] == 'url_only' and file_info['original_url']:
            return {
                "success": True,
                "download_url": file_info['original_url'],
                "message": "返回原始视频链接"
            }
        
        else:
            raise HTTPException(status_code=404, detail="文件不可下载")
            
    except Exception as e:
        utils.logger.error(f"[API] 下载文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_storage_stats(platform: Optional[str] = Query(None)):
    """获取存储统计"""
    try:
        if not file_manager:
            raise HTTPException(status_code=500, detail="文件管理器未初始化")
        
        stats = await file_manager.get_storage_stats(platform)
        
        # 计算总体统计
        total_files = sum(stat['file_count'] for stat in stats.values())
        total_size = sum(stat['total_size'] for stat in stats.values())
        total_downloads = sum(stat['total_downloads'] for stat in stats.values())
        
        return {
            "success": True,
            "stats_by_storage": stats,
            "total_summary": {
                "total_files": total_files,
                "total_size": total_size,
                "total_downloads": total_downloads,
                "storage_types": list(stats.keys())
            }
        }
        
    except Exception as e:
        utils.logger.error(f"[API] 获取存储统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks")
async def get_download_tasks(
    status: Optional[str] = Query(None, description="任务状态筛选"),
    batch_id: Optional[str] = Query(None, description="批次ID筛选"),
    limit: int = Query(50, description="返回数量限制")
):
    """获取下载任务列表"""
    try:
        if not file_manager:
            raise HTTPException(status_code=500, detail="文件管理器未初始化")
        
        # 构建查询条件
        where_conditions = []
        params = []
        
        if status:
            where_conditions.append("dt.status = %s")
            params.append(status)
        
        if batch_id:
            where_conditions.append("dt.batch_id = %s")
            params.append(batch_id)
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # 查询任务列表，关联文件信息
        sql = f"""
        SELECT 
            dt.id, dt.batch_id, dt.file_id, dt.target_storage, dt.target_path,
            dt.quality_preset, dt.max_file_size, dt.status, dt.progress,
            dt.error_message, dt.attempts, dt.final_path, dt.final_size,
            dt.created_at, dt.started_at, dt.completed_at,
            vf.platform, vf.content_id, vf.title, vf.author_name, vf.file_size
        FROM video_download_tasks dt
        LEFT JOIN video_files vf ON dt.file_id = vf.id
        {where_clause}
        ORDER BY dt.created_at DESC 
        LIMIT %s
        """
        
        params.append(limit)
        results = await file_manager.db.query(sql, *params)
        
        return {
            "success": True,
            "data": [dict(row) for row in results]
        }
        
    except Exception as e:
        utils.logger.error(f"[API] 获取下载任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cleanup-expired")
async def cleanup_expired_files():
    """清理过期文件"""
    try:
        if not file_manager:
            raise HTTPException(status_code=500, detail="文件管理器未初始化")
        
        cleaned_count = await file_manager.cleanup_expired_files()
        
        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "message": f"清理完成，共清理 {cleaned_count} 个过期文件"
        }
        
    except Exception as e:
        utils.logger.error(f"[API] 清理过期文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 后台任务函数
async def execute_download_task(task_id: int, file_info: Dict, config: Dict):
    """执行下载任务"""
    try:
        utils.logger.info(f"[DOWNLOAD_TASK] 开始执行下载任务: {task_id}")
        
        # 更新任务状态为进行中
        await file_manager.db.execute(
            "UPDATE video_download_tasks SET status = 'downloading', started_at = NOW() WHERE id = %s",
            task_id
        )
        
        # 更新文件下载状态
        await file_manager.update_download_status(file_info['id'], 'downloading', 0)
        
        # 根据目标存储类型执行不同的下载逻辑
        if config['target_storage'] == 'local':
            success = await download_to_local(task_id, file_info, config)
        elif config['target_storage'] == 'minio':
            success = await download_to_minio(task_id, file_info, config)
        else:
            raise Exception(f"不支持的存储类型: {config['target_storage']}")
        
        if success:
            # 更新任务状态为完成
            await file_manager.db.execute(
                "UPDATE video_download_tasks SET status = 'completed', completed_at = NOW() WHERE id = %s",
                task_id
            )
            await file_manager.update_download_status(file_info['id'], 'completed', 100)
            utils.logger.info(f"[DOWNLOAD_TASK] 下载任务完成: {task_id}")
        else:
            raise Exception("下载失败")
            
    except Exception as e:
        utils.logger.error(f"[DOWNLOAD_TASK] 下载任务失败 {task_id}: {e}")
        
        # 更新任务状态为失败
        await file_manager.db.execute(
            "UPDATE video_download_tasks SET status = 'failed', error_message = %s WHERE id = %s",
            str(e), task_id
        )
        await file_manager.update_download_status(file_info['id'], 'failed', error=str(e))

async def download_to_local(task_id: int, file_info: Dict, config: Dict) -> bool:
    """下载到本地存储"""
    try:
        # 这里需要实现实际的下载逻辑
        # 1. 从原始URL下载视频
        # 2. 保存到指定本地路径
        # 3. 更新数据库记录
        
        # 示例代码，需要根据实际需求实现
        target_dir = config.get('target_path', './downloads')
        os.makedirs(target_dir, exist_ok=True)
        
        filename = f"{file_info['platform']}_{file_info['content_id']}.{file_info['video_format']}"
        file_path = os.path.join(target_dir, filename)
        
        # TODO: 实际下载逻辑
        # await download_video_from_url(file_info['original_url'], file_path)
        
        # 更新文件记录
        await file_manager.db.execute(
            "UPDATE video_files SET storage_type = 'local', local_path = %s WHERE id = %s",
            file_path, file_info['id']
        )
        
        # 更新任务记录
        await file_manager.db.execute(
            "UPDATE video_download_tasks SET final_path = %s WHERE id = %s",
            file_path, task_id
        )
        
        return True
        
    except Exception as e:
        utils.logger.error(f"[DOWNLOAD_LOCAL] 本地下载失败: {e}")
        return False

async def download_to_minio(task_id: int, file_info: Dict, config: Dict) -> bool:
    """下载到MinIO存储"""
    try:
        if not minio_client:
            raise Exception("MinIO客户端未初始化")
        
        # 这里需要实现MinIO上传逻辑
        # 1. 下载视频到临时文件
        # 2. 上传到MinIO
        # 3. 删除临时文件
        # 4. 更新数据库记录
        
        bucket_name = config.get('minio_bucket', 'videos')
        object_key = f"{file_info['platform']}/{file_info['content_id']}.{file_info['video_format']}"
        
        # TODO: 实际MinIO上传逻辑
        # temp_file = await download_to_temp(file_info['original_url'])
        # minio_client.fput_object(bucket_name, object_key, temp_file)
        
        # 更新文件记录
        await file_manager.db.execute(
            "UPDATE video_files SET storage_type = 'minio', minio_bucket = %s, minio_object_key = %s WHERE id = %s",
            bucket_name, object_key, file_info['id']
        )
        
        return True
        
    except Exception as e:
        utils.logger.error(f"[DOWNLOAD_MINIO] MinIO上传失败: {e}")
        return False 