# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from .proxy_manager import ProxyManager, ProxyInfo

router = APIRouter(prefix="/api/v1/proxy", tags=["代理管理"])

# 全局代理管理器实例
proxy_manager = ProxyManager()


class ProxyCreateRequest(BaseModel):
    proxy_type: str = Field(..., description="代理类型: http, https, socks5")
    ip: str = Field(..., description="代理IP地址")
    port: int = Field(..., description="代理端口")
    username: Optional[str] = Field(None, description="代理用户名")
    password: Optional[str] = Field(None, description="代理密码")
    country: Optional[str] = Field(None, description="代理所在国家")
    region: Optional[str] = Field(None, description="代理所在地区")
    city: Optional[str] = Field(None, description="代理所在城市")
    isp: Optional[str] = Field(None, description="网络服务商")
    speed: Optional[int] = Field(None, description="代理速度(ms)")
    anonymity: Optional[str] = Field(None, description="匿名度: transparent, anonymous, elite")
    uptime: Optional[float] = Field(None, description="在线率(%)")
    priority: int = Field(0, description="优先级")
    tags: Optional[str] = Field(None, description="标签，逗号分隔")
    description: Optional[str] = Field(None, description="代理描述")


class ProxyUpdateRequest(BaseModel):
    proxy_type: Optional[str] = Field(None, description="代理类型")
    ip: Optional[str] = Field(None, description="代理IP地址")
    port: Optional[int] = Field(None, description="代理端口")
    username: Optional[str] = Field(None, description="代理用户名")
    password: Optional[str] = Field(None, description="代理密码")
    country: Optional[str] = Field(None, description="代理所在国家")
    region: Optional[str] = Field(None, description="代理所在地区")
    city: Optional[str] = Field(None, description="代理所在城市")
    isp: Optional[str] = Field(None, description="网络服务商")
    speed: Optional[int] = Field(None, description="代理速度(ms)")
    anonymity: Optional[str] = Field(None, description="匿名度")
    uptime: Optional[float] = Field(None, description="在线率(%)")
    priority: Optional[int] = Field(None, description="优先级")
    tags: Optional[str] = Field(None, description="标签")
    description: Optional[str] = Field(None, description="代理描述")
    status: Optional[bool] = Field(None, description="状态")


class ProxyResponse(BaseModel):
    id: int
    proxy_type: str
    ip: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    isp: Optional[str] = None
    speed: Optional[int] = None
    anonymity: Optional[str] = None
    uptime: Optional[float] = None
    last_check_time: Optional[int] = None
    last_check_result: bool = True
    fail_count: int = 0
    success_count: int = 0
    total_requests: int = 0
    total_success: int = 0
    status: bool = True
    priority: int = 0
    tags: Optional[str] = None
    description: Optional[str] = None
    success_rate: float = 0.0
    proxy_url: str = ""


class ProxyStatsResponse(BaseModel):
    total: int
    active: int
    available: int
    avg_speed: float
    avg_uptime: float


class StrategyResponse(BaseModel):
    id: int
    strategy_name: str
    strategy_type: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_default: bool = False
    status: bool = True


@router.get("/stats", response_model=ProxyStatsResponse)
async def get_proxy_stats():
    """获取代理统计信息"""
    try:
        stats = await proxy_manager.get_proxy_stats()
        return ProxyStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/list", response_model=List[ProxyResponse])
async def get_proxy_list(
    page: int = 1,
    page_size: int = 20,
    status: Optional[bool] = None,
    proxy_type: Optional[str] = None,
    country: Optional[str] = None,
    anonymity: Optional[str] = None
):
    """获取代理列表"""
    try:
        # 构建查询条件
        conditions = ["1=1"]
        params = []
        
        if status is not None:
            conditions.append("status = %s")
            params.append(status)
        
        if proxy_type:
            conditions.append("proxy_type = %s")
            params.append(proxy_type)
        
        if country:
            conditions.append("country = %s")
            params.append(country)
        
        if anonymity:
            conditions.append("anonymity = %s")
            params.append(anonymity)
        
        where_clause = " AND ".join(conditions)
        offset = (page - 1) * page_size
        
        # 查询数据
        rows = await proxy_manager.db.query(
            f"SELECT * FROM proxy_pool WHERE {where_clause} "
            f"ORDER BY priority DESC, speed ASC LIMIT %s OFFSET %s",
            *(params + [page_size, offset])
        )
        
        # 转换为响应格式
        proxies = []
        for row in rows:
            proxy_info = ProxyInfo(**row)
            proxy_dict = {
                **row,
                "success_rate": proxy_info.success_rate,
                "proxy_url": proxy_info.proxy_url
            }
            proxies.append(ProxyResponse(**proxy_dict))
        
        return proxies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取代理列表失败: {str(e)}")


@router.post("/add", response_model=Dict[str, Any])
async def add_proxy(request: ProxyCreateRequest):
    """添加代理"""
    try:
        proxy_data = request.dict()
        proxy_id = await proxy_manager.add_proxy(proxy_data)
        
        return {
            "message": "代理添加成功",
            "proxy_id": proxy_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加代理失败: {str(e)}")


@router.put("/update/{proxy_id}", response_model=Dict[str, Any])
async def update_proxy(proxy_id: int, request: ProxyUpdateRequest):
    """更新代理"""
    try:
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供更新数据")
        
        success = await proxy_manager.update_proxy(proxy_id, update_data)
        
        if success:
            return {"message": "代理更新成功"}
        else:
            raise HTTPException(status_code=404, detail="代理不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新代理失败: {str(e)}")


@router.delete("/delete/{proxy_id}", response_model=Dict[str, Any])
async def delete_proxy(proxy_id: int):
    """删除代理"""
    try:
        success = await proxy_manager.delete_proxy(proxy_id)
        
        if success:
            return {"message": "代理删除成功"}
        else:
            raise HTTPException(status_code=404, detail="代理不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除代理失败: {str(e)}")


@router.post("/check/{proxy_id}", response_model=Dict[str, Any])
async def check_proxy(proxy_id: int):
    """检测代理可用性"""
    try:
        # 获取代理信息
        row = await proxy_manager.db.get_first(
            "SELECT * FROM proxy_pool WHERE id = %s", proxy_id
        )
        
        if not row:
            raise HTTPException(status_code=404, detail="代理不存在")
        
        proxy_info = ProxyInfo(**row)
        
        # 检测代理
        is_available = await proxy_manager.check_proxy(proxy_info)
        
        # 更新检测结果
        await proxy_manager.db.execute(
            "UPDATE proxy_pool SET last_check_time = %s, last_check_result = %s, "
            "last_modify_ts = %s WHERE id = %s",
            int(datetime.now().timestamp() * 1000), is_available, 
            int(datetime.now().timestamp() * 1000), proxy_id
        )
        
        return {
            "message": "代理检测完成",
            "proxy_id": proxy_id,
            "is_available": is_available
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测代理失败: {str(e)}")


@router.post("/check/batch", response_model=Dict[str, Any])
async def check_proxies_batch(background_tasks: BackgroundTasks, proxy_ids: List[int] = None):
    """批量检测代理"""
    try:
        if not proxy_ids:
            # 如果没有指定ID，检测所有启用的代理
            rows = await proxy_manager.db.query(
                "SELECT id FROM proxy_pool WHERE status = 1"
            )
            proxy_ids = [row["id"] for row in rows]
        
        # 在后台执行批量检测
        background_tasks.add_task(batch_check_proxies, proxy_ids)
        
        return {
            "message": f"批量检测任务已启动，共 {len(proxy_ids)} 个代理",
            "task_count": len(proxy_ids)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动批量检测失败: {str(e)}")


async def batch_check_proxies(proxy_ids: List[int]):
    """后台批量检测代理"""
    for proxy_id in proxy_ids:
        try:
            # 获取代理信息
            row = await proxy_manager.db.get_first(
                "SELECT * FROM proxy_pool WHERE id = %s", proxy_id
            )
            
            if row:
                proxy_info = ProxyInfo(**row)
                is_available = await proxy_manager.check_proxy(proxy_info)
                
                # 更新检测结果
                await proxy_manager.db.execute(
                    "UPDATE proxy_pool SET last_check_time = %s, last_check_result = %s, "
                    "last_modify_ts = %s WHERE id = %s",
                    int(datetime.now().timestamp() * 1000), is_available, 
                    int(datetime.now().timestamp() * 1000), proxy_id
                )
            
            # 避免检测过于频繁
            await asyncio.sleep(1)
        except Exception as e:
            print(f"检测代理 {proxy_id} 失败: {e}")


@router.get("/get", response_model=Dict[str, Any])
async def get_proxy(
    strategy_type: str = "round_robin",
    platform: str = None,
    check_availability: bool = True
):
    """获取代理"""
    try:
        proxy_info = await proxy_manager.get_proxy(strategy_type, platform)
        
        if not proxy_info:
            raise HTTPException(status_code=404, detail="没有可用的代理")
        
        # 如果需要检测可用性
        if check_availability:
            is_available = await proxy_manager.check_proxy(proxy_info)
            if not is_available:
                # 如果检测失败，尝试获取其他代理
                proxy_info = await proxy_manager.get_proxy(strategy_type, platform)
                if not proxy_info:
                    raise HTTPException(status_code=404, detail="没有可用的代理")
        
        return {
            "proxy_id": proxy_info.id,
            "proxy_type": proxy_info.proxy_type,
            "ip": proxy_info.ip,
            "port": proxy_info.port,
            "username": proxy_info.username,
            "password": proxy_info.password,
            "proxy_url": proxy_info.proxy_url,
            "country": proxy_info.country,
            "speed": proxy_info.speed,
            "anonymity": proxy_info.anonymity,
            "success_rate": proxy_info.success_rate
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取代理失败: {str(e)}")


@router.get("/strategies", response_model=List[StrategyResponse])
async def get_strategies():
    """获取所有策略"""
    try:
        strategies = await proxy_manager.get_strategies()
        return [StrategyResponse(**strategy) for strategy in strategies]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取策略列表失败: {str(e)}")


@router.post("/import", response_model=Dict[str, Any])
async def import_proxies(proxies: List[ProxyCreateRequest]):
    """批量导入代理"""
    try:
        success_count = 0
        fail_count = 0
        
        for proxy_request in proxies:
            try:
                proxy_data = proxy_request.dict()
                await proxy_manager.add_proxy(proxy_data)
                success_count += 1
            except Exception as e:
                fail_count += 1
                print(f"导入代理失败: {e}")
        
        return {
            "message": "批量导入完成",
            "success_count": success_count,
            "fail_count": fail_count,
            "total_count": len(proxies)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量导入失败: {str(e)}")


@router.get("/usage/logs", response_model=List[Dict[str, Any]])
async def get_usage_logs(
    proxy_id: Optional[int] = None,
    platform: Optional[str] = None,
    success: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20
):
    """获取代理使用日志"""
    try:
        conditions = ["1=1"]
        params = []
        
        if proxy_id:
            conditions.append("proxy_id = %s")
            params.append(proxy_id)
        
        if platform:
            conditions.append("platform = %s")
            params.append(platform)
        
        if success is not None:
            conditions.append("success = %s")
            params.append(success)
        
        where_clause = " AND ".join(conditions)
        offset = (page - 1) * page_size
        
        rows = await proxy_manager.db.query(
            f"SELECT * FROM proxy_usage_log WHERE {where_clause} "
            f"ORDER BY add_ts DESC LIMIT %s OFFSET %s",
            *(params + [page_size, offset])
        )
        
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取使用日志失败: {str(e)}")


@router.get("/check/logs", response_model=List[Dict[str, Any]])
async def get_check_logs(
    proxy_id: Optional[int] = None,
    check_type: Optional[str] = None,
    success: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20
):
    """获取代理检测日志"""
    try:
        conditions = ["1=1"]
        params = []
        
        if proxy_id:
            conditions.append("proxy_id = %s")
            params.append(proxy_id)
        
        if check_type:
            conditions.append("check_type = %s")
            params.append(check_type)
        
        if success is not None:
            conditions.append("success = %s")
            params.append(success)
        
        where_clause = " AND ".join(conditions)
        offset = (page - 1) * page_size
        
        rows = await proxy_manager.db.query(
            f"SELECT * FROM proxy_check_log WHERE {where_clause} "
            f"ORDER BY add_ts DESC LIMIT %s OFFSET %s",
            *(params + [page_size, offset])
        )
        
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取检测日志失败: {str(e)}") 