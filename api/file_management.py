"""
文件管理API路由
"""

from fastapi import APIRouter, HTTPException, Query, Form
from typing import Dict, Any, List
import logging
from pydantic import BaseModel

from services.file_management_service import FileManagementService

logger = logging.getLogger(__name__)

router = APIRouter()
file_service = FileManagementService()

class BatchDeleteRequest(BaseModel):
    file_ids: List[int]

class MoveFileRequest(BaseModel):
    target_dir: str

class CleanupRequest(BaseModel):
    file_paths: List[str] = []
    file_ids: List[int] = []

@router.get("/files", response_model=Dict[str, Any])
async def get_file_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    storage_type: str = Query(None, description="存储类型筛选")
):
    """获取文件列表"""
    try:
        results = await file_service.get_file_list(page=page, page_size=page_size, storage_type=storage_type)
        return {
            "code": 200,
            "message": "获取成功",
            "data": results
        }
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文件列表失败")

@router.get("/files/{file_id}", response_model=Dict[str, Any])
async def get_file_detail(file_id: int):
    """获取文件详情"""
    try:
        result = await file_service.get_file_detail(file_id)
        if not result:
            raise HTTPException(status_code=404, detail="文件未找到")
        
        return {
            "code": 200,
            "message": "获取成功",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件详情失败 {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文件详情失败")

@router.delete("/files/{file_id}", response_model=Dict[str, Any])
async def delete_file(file_id: int):
    """删除文件"""
    try:
        success = await file_service.delete_file(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="文件未找到")
        
        return {
            "code": 200,
            "message": "删除成功",
            "data": {"file_id": file_id}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败 {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="删除文件失败")

@router.post("/files/batch-delete", response_model=Dict[str, Any])
async def batch_delete_files(request: BatchDeleteRequest):
    """批量删除文件"""
    try:
        results = await file_service.batch_delete_files(request.file_ids)
        return {
            "code": 200,
            "message": "批量删除完成",
            "data": results
        }
    except Exception as e:
        logger.error(f"批量删除文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量删除文件失败")

@router.put("/files/{file_id}/move", response_model=Dict[str, Any])
async def move_file(file_id: int, request: MoveFileRequest):
    """移动文件"""
    try:
        success = await file_service.move_file(file_id, request.target_dir)
        if not success:
            raise HTTPException(status_code=404, detail="文件未找到或移动失败")
        
        return {
            "code": 200,
            "message": "移动成功",
            "data": {"file_id": file_id, "target_dir": request.target_dir}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移动文件失败 {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="移动文件失败")

@router.get("/files/statistics", response_model=Dict[str, Any])
async def get_storage_statistics():
    """获取存储统计信息"""
    try:
        results = await file_service.get_storage_statistics()
        return {
            "code": 200,
            "message": "获取成功",
            "data": results
        }
    except Exception as e:
        logger.error(f"获取存储统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取存储统计失败")

@router.get("/files/cleanup/scan", response_model=Dict[str, Any])
async def scan_orphaned_files():
    """扫描孤立文件"""
    try:
        results = await file_service.cleanup_orphaned_files()
        return {
            "code": 200,
            "message": "扫描完成",
            "data": results
        }
    except Exception as e:
        logger.error(f"扫描孤立文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="扫描孤立文件失败")

@router.post("/files/cleanup/remove-orphaned", response_model=Dict[str, Any])
async def remove_orphaned_files(request: CleanupRequest):
    """删除孤立文件"""
    try:
        results = await file_service.remove_orphaned_files(request.file_paths)
        return {
            "code": 200,
            "message": "删除完成",
            "data": results
        }
    except Exception as e:
        logger.error(f"删除孤立文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除孤立文件失败")

@router.post("/files/cleanup/remove-missing", response_model=Dict[str, Any])
async def remove_missing_records(request: CleanupRequest):
    """删除缺失文件记录"""
    try:
        results = await file_service.remove_missing_records(request.file_ids)
        return {
            "code": 200,
            "message": "删除完成",
            "data": results
        }
    except Exception as e:
        logger.error(f"删除缺失文件记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除缺失文件记录失败") 