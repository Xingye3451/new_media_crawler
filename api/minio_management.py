"""
MinIO管理API路由
"""

from fastapi import APIRouter, HTTPException, Query, File, UploadFile
from typing import Dict, Any, List
import logging
from pydantic import BaseModel

from services.minio_service import MinIOService

logger = logging.getLogger(__name__)

router = APIRouter()
minio_service = MinIOService()

class ObjectUploadRequest(BaseModel):
    object_name: str
    metadata: Dict[str, Any] = {}

class ObjectDeleteRequest(BaseModel):
    object_names: List[str]

@router.get("/minio/status", response_model=Dict[str, Any])
async def get_minio_status():
    """获取MinIO服务状态"""
    try:
        stats = minio_service.get_bucket_statistics()
        return {
            "code": 200,
            "message": "获取成功",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取MinIO状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取MinIO状态失败")

@router.get("/minio/objects", response_model=Dict[str, Any])
async def list_minio_objects(
    prefix: str = Query("", description="对象前缀"),
    max_keys: int = Query(100, ge=1, le=1000, description="最大对象数量")
):
    """列出MinIO对象"""
    try:
        if not minio_service.is_available():
            raise HTTPException(status_code=503, detail="MinIO服务不可用")
        
        objects = minio_service.list_objects(prefix=prefix, max_keys=max_keys)
        return {
            "code": 200,
            "message": "获取成功",
            "data": {
                "objects": objects,
                "total": len(objects),
                "prefix": prefix
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出对象失败: {str(e)}")
        raise HTTPException(status_code=500, detail="列出对象失败")

@router.get("/minio/objects/{object_name:path}", response_model=Dict[str, Any])
async def get_object_info(object_name: str):
    """获取对象信息"""
    try:
        if not minio_service.is_available():
            raise HTTPException(status_code=503, detail="MinIO服务不可用")
        
        info = minio_service.get_object_info(object_name)
        if not info:
            raise HTTPException(status_code=404, detail="对象未找到")
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对象信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取对象信息失败")

@router.get("/minio/objects/{object_name:path}/url", response_model=Dict[str, Any])
async def get_object_url(
    object_name: str,
    expires_hours: int = Query(1, ge=1, le=168, description="URL过期时间（小时）")
):
    """获取对象访问URL"""
    try:
        if not minio_service.is_available():
            raise HTTPException(status_code=503, detail="MinIO服务不可用")
        
        from datetime import timedelta
        url = minio_service.get_presigned_url(
            object_name=object_name,
            expires=timedelta(hours=expires_hours)
        )
        
        if not url:
            raise HTTPException(status_code=404, detail="对象未找到或生成URL失败")
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": {
                "object_name": object_name,
                "url": url,
                "expires_hours": expires_hours
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对象URL失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取对象URL失败")

@router.post("/minio/upload", response_model=Dict[str, Any])
async def upload_file(
    file: UploadFile = File(...),
    object_name: str = Query(None, description="对象名称（可选）"),
    metadata: str = Query("{}", description="元数据（JSON格式）")
):
    """上传文件到MinIO"""
    try:
        if not minio_service.is_available():
            raise HTTPException(status_code=503, detail="MinIO服务不可用")
        
        # 解析元数据
        import json
        try:
            metadata_dict = json.loads(metadata)
        except:
            metadata_dict = {}
        
        # 添加文件信息到元数据
        metadata_dict.update({
            'original_filename': file.filename,
            'content_type': file.content_type,
            'file_size': str(file.size) if file.size else '0'
        })
        
        # 保存临时文件
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # 上传到MinIO
            result = await minio_service.upload_file(
                file_path=tmp_file_path,
                object_name=object_name,
                metadata=metadata_dict
            )
            
            return {
                "code": 200,
                "message": "上传成功",
                "data": result
            }
        finally:
            # 清理临时文件
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="上传文件失败")

@router.delete("/minio/objects/{object_name:path}", response_model=Dict[str, Any])
async def delete_object(object_name: str):
    """删除对象"""
    try:
        if not minio_service.is_available():
            raise HTTPException(status_code=503, detail="MinIO服务不可用")
        
        success = minio_service.delete_object(object_name)
        if not success:
            raise HTTPException(status_code=404, detail="对象未找到或删除失败")
        
        return {
            "code": 200,
            "message": "删除成功",
            "data": {"object_name": object_name}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除对象失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除对象失败")

@router.post("/minio/objects/batch-delete", response_model=Dict[str, Any])
async def batch_delete_objects(request: ObjectDeleteRequest):
    """批量删除对象"""
    try:
        if not minio_service.is_available():
            raise HTTPException(status_code=503, detail="MinIO服务不可用")
        
        success_count = 0
        failed_count = 0
        failed_objects = []
        
        for object_name in request.object_names:
            try:
                if minio_service.delete_object(object_name):
                    success_count += 1
                else:
                    failed_count += 1
                    failed_objects.append(object_name)
            except Exception as e:
                failed_count += 1
                failed_objects.append(object_name)
                logger.error(f"删除对象失败 {object_name}: {str(e)}")
        
        return {
            "code": 200,
            "message": "批量删除完成",
            "data": {
                "success_count": success_count,
                "failed_count": failed_count,
                "failed_objects": failed_objects,
                "total_count": len(request.object_names)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量删除对象失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量删除对象失败")

@router.post("/minio/cleanup", response_model=Dict[str, Any])
async def cleanup_expired_objects(
    days: int = Query(30, ge=1, le=365, description="清理天数")
):
    """清理过期对象"""
    try:
        if not minio_service.is_available():
            raise HTTPException(status_code=503, detail="MinIO服务不可用")
        
        deleted_count = minio_service.cleanup_expired_objects(days)
        return {
            "code": 200,
            "message": "清理完成",
            "data": {
                "deleted_count": deleted_count,
                "cleanup_days": days
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理过期对象失败: {str(e)}")
        raise HTTPException(status_code=500, detail="清理过期对象失败")

@router.get("/minio/statistics", response_model=Dict[str, Any])
async def get_minio_statistics():
    """获取MinIO存储统计"""
    try:
        stats = minio_service.get_bucket_statistics()
        return {
            "code": 200,
            "message": "获取成功",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取MinIO统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取MinIO统计失败") 