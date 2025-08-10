"""
代理管理API模块
提供代理池管理、代理使用统计、代理状态监控等功能
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

from tools import utils
from var import media_crawler_db_var

proxy_router = APIRouter(tags=["代理管理"])

# 数据模型
class ProxyInfo(BaseModel):
    """代理信息模型"""
    id: int
    proxy_id: str
    ip: str
    port: int
    proxy_type: str
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    speed: Optional[int] = None
    anonymity: Optional[str] = None
    success_rate: Optional[float] = None
    expire_ts: Optional[int] = None
    provider: str = "qingguo"
    usage_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    status: str = "active"
    enabled: bool = True
    area: Optional[str] = None
    description: Optional[str] = None
    last_check: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class ProxyCreate(BaseModel):
    """创建代理请求模型"""
    proxy_id: str = Field(..., description="代理唯一标识")
    ip: str = Field(..., description="代理IP地址")
    port: int = Field(..., description="代理端口")
    proxy_type: str = Field(default="http", description="代理类型")
    username: Optional[str] = Field(None, description="代理用户名")
    password: Optional[str] = Field(None, description="代理密码")
    country: Optional[str] = Field(None, description="代理所在国家")
    speed: Optional[int] = Field(None, description="代理速度(ms)")
    anonymity: Optional[str] = Field(None, description="匿名级别")
    success_rate: Optional[float] = Field(None, description="成功率")
    expire_ts: Optional[int] = Field(None, description="过期时间戳")
    platform: Optional[str] = Field(None, description="关联平台")
    account_id: Optional[int] = Field(None, description="关联账号ID")
    provider: str = Field(default="qingguo", description="代理提供商")

class ProxyUpdate(BaseModel):
    """更新代理请求模型"""
    ip: Optional[str] = Field(None, description="代理IP地址")
    port: Optional[int] = Field(None, description="代理端口")
    proxy_type: Optional[str] = Field(None, description="代理类型")
    username: Optional[str] = Field(None, description="代理用户名")
    password: Optional[str] = Field(None, description="代理密码")
    country: Optional[str] = Field(None, description="代理所在国家")
    speed: Optional[int] = Field(None, description="代理速度(ms)")
    anonymity: Optional[str] = Field(None, description="匿名级别")
    success_rate: Optional[float] = Field(None, description="成功率")
    expire_ts: Optional[int] = Field(None, description="过期时间戳")
    platform: Optional[str] = Field(None, description="关联平台")
    account_id: Optional[int] = Field(None, description="关联账号ID")
    provider: Optional[str] = Field(None, description="代理提供商")
    status: Optional[str] = Field(None, description="代理状态")

class ProxyStats(BaseModel):
    """代理统计信息模型"""
    total_proxies: int
    active_proxies: int
    expired_proxies: int
    failed_proxies: int
    by_provider: Dict[str, int]
    by_platform: Dict[str, int]
    by_status: Dict[str, int]
    avg_success_rate: float
    total_usage_count: int

async def get_db():
    """获取数据库连接"""
    try:
        return media_crawler_db_var.get()
    except LookupError:
        from db import init_mediacrawler_db
        await init_mediacrawler_db()
        return media_crawler_db_var.get()

@proxy_router.get("/proxies/", response_model=List[ProxyInfo])
async def get_proxies(
    provider: Optional[str] = Query(None, description="提供商筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    enabled: Optional[str] = Query(None, description="启用状态筛选"),
    area: Optional[str] = Query(None, description="区域筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取代理列表"""
    try:
        db = await get_db()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if provider:
            conditions.append("provider = %s")
            params.append(provider)
        
        if status:
            conditions.append("status = %s")
            params.append(status)
        
        if enabled:
            conditions.append("enabled = %s")
            params.append(enabled)
        
        if area:
            conditions.append("area LIKE %s")
            params.append(f"%{area}%")
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 查询代理列表
        query = f"""
            SELECT * FROM proxy_pool{where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        
        results = await db.query(query, *(params + [page_size, offset]))
        
        # 转换结果
        proxies = []
        for row in results:
            proxy = ProxyInfo(
                id=row['id'],
                proxy_id=row['proxy_id'],
                ip=row['ip'],
                port=row['port'],
                proxy_type=row['proxy_type'],
                username=row.get('username'),
                password=row.get('password'),
                country=row.get('country'),
                speed=row.get('speed'),
                anonymity=row.get('anonymity'),
                success_rate=row.get('success_rate'),
                expire_ts=row.get('expire_ts'),
                provider=row.get('provider', 'qingguo'),
                usage_count=row.get('usage_count', 0),
                success_count=row.get('success_count', 0),
                fail_count=row.get('fail_count', 0),
                status=row.get('status', 'active') if 'status' in row else ('active' if row.get('is_active', 1) else 'inactive'),
                enabled=row.get('enabled', True),
                area=row.get('area'),
                description=row.get('description'),
                last_check=row.get('last_check'),
                last_used_at=row.get('last_used_at'),
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            proxies.append(proxy)
        
        return proxies
        
    except Exception as e:
        utils.logger.error(f"获取代理列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取代理列表失败: {str(e)}")

@proxy_router.get("/proxies/{proxy_id}", response_model=ProxyInfo)
async def get_proxy(proxy_id: str):
    """获取单个代理详情"""
    try:
        db = await get_db()
        
        query = "SELECT * FROM proxy_pool WHERE proxy_id = %s"
        row = await db.get_first(query, proxy_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="代理不存在")
        
        proxy = ProxyInfo(
            id=row['id'],
            proxy_id=row['proxy_id'],
            ip=row['ip'],
            port=row['port'],
            proxy_type=row['proxy_type'],
            username=row.get('username'),
            password=row.get('password'),
            country=row.get('country'),
            speed=row.get('speed'),
            anonymity=row.get('anonymity'),
            success_rate=row.get('success_rate'),
            expire_ts=row.get('expire_ts'),
            provider=row.get('provider', 'qingguo'),
            usage_count=row.get('usage_count', 0),
            success_count=row.get('success_count', 0),
            fail_count=row.get('fail_count', 0),
            status=row.get('status', 'active') if 'status' in row else ('active' if row.get('is_active', 1) else 'inactive'),
            enabled=row.get('enabled', True),
            area=row.get('area'),
            description=row.get('description'),
            last_check=row.get('last_check'),
            last_used_at=row.get('last_used_at'),
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
        
        return proxy
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"获取代理详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取代理详情失败: {str(e)}")

@proxy_router.post("/proxies/", response_model=ProxyInfo)
async def create_proxy(proxy: ProxyCreate):
    """创建新代理"""
    try:
        db = await get_db()
        
        # 检查代理是否已存在
        check_query = "SELECT COUNT(*) FROM proxy_pool WHERE proxy_id = %s"
        result = await db.get_first(check_query, proxy.proxy_id)
        
        if result and list(result.values())[0] > 0:
            raise HTTPException(status_code=400, detail="代理ID已存在")
        
        # 插入新代理
        insert_query = """
            INSERT INTO proxy_pool (
                proxy_id, ip, port, proxy_type, username, password,
                country, speed, anonymity, success_rate, expire_ts,
                platform, account_id, provider, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        await db.execute(insert_query,
            proxy.proxy_id, proxy.ip, proxy.port, proxy.proxy_type,
            proxy.username, proxy.password, proxy.country, proxy.speed,
            proxy.anonymity, proxy.success_rate, proxy.expire_ts,
            proxy.platform, proxy.account_id, proxy.provider,
            datetime.now(), datetime.now()
        )
        
        # 获取新创建的代理
        return await get_proxy(proxy.proxy_id)
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"创建代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建代理失败: {str(e)}")

@proxy_router.put("/proxies/{proxy_id}", response_model=ProxyInfo)
async def update_proxy(proxy_id: str, proxy: ProxyUpdate):
    """更新代理信息"""
    try:
        db = await get_db()
        
        # 检查代理是否存在
        check_query = "SELECT COUNT(*) FROM proxy_pool WHERE proxy_id = %s"
        result = await db.get_first(check_query, proxy_id)
        
        if not result or list(result.values())[0] == 0:
            raise HTTPException(status_code=404, detail="代理不存在")
        
        # 构建更新语句
        updates = []
        params = []
        
        for field, value in proxy.dict(exclude_unset=True).items():
            if value is not None:
                updates.append(f"{field} = %s")
                params.append(value)
        
        if not updates:
            raise HTTPException(status_code=400, detail="没有提供要更新的字段")
        
        # 执行更新
        update_query = f"UPDATE proxy_pool SET {', '.join(updates)}, updated_at = %s WHERE proxy_id = %s"
        params.extend([datetime.now(), proxy_id])
        
        await db.execute(update_query, *params)
        
        # 返回更新后的代理
        return await get_proxy(proxy_id)
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"更新代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新代理失败: {str(e)}")

@proxy_router.delete("/proxies/{proxy_id}")
async def release_proxy(proxy_id: str):
    """释放代理"""
    try:
        db = await get_db()
        
        # 检查代理是否存在并获取代理信息
        check_query = "SELECT * FROM proxy_pool WHERE proxy_id = %s"
        proxy = await db.get_first(check_query, proxy_id)
        
        if not proxy:
            raise HTTPException(status_code=404, detail="代理不存在")
        
        # 如果是青果代理，尝试调用青果API删除
        api_delete_success = False
        if proxy.get('provider') == 'qingguo':
            from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
            
            proxy_manager = await get_qingguo_proxy_manager()
            
            # 调用青果API删除代理
            api_delete_success = await proxy_manager.delete_proxy_from_api(proxy['ip'])
            
            if not api_delete_success:
                utils.logger.warning(f"青果API删除失败（可能没有权限），但仍会从数据库删除代理: {proxy_id}")
        
        # 从数据库删除代理
        delete_query = "DELETE FROM proxy_pool WHERE proxy_id = %s"
        await db.execute(delete_query, proxy_id)
        
        # 根据API删除结果返回不同的消息
        if proxy.get('provider') == 'qingguo' and not api_delete_success:
            return {
                "success": True,
                "message": "代理已从数据库释放（青果API删除失败，请手动处理）"
            }
        else:
            return {
                "success": True,
                "message": "代理释放成功"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"释放代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"释放代理失败: {str(e)}")

@proxy_router.get("/proxies/stats/overview", response_model=ProxyStats)
async def get_proxy_stats():
    """获取代理统计概览"""
    try:
        db = await get_db()
        
        # 基础统计
        total_query = "SELECT COUNT(*) as total FROM proxy_pool"
        total_result = await db.get_first(total_query)
        total_proxies = total_result['total'] if total_result else 0
        
        # 状态统计 - 兼容旧版本数据库
        try:
            status_query = """
                SELECT status, COUNT(*) as count 
                FROM proxy_pool 
                GROUP BY status
            """
            status_results = await db.query(status_query)
            by_status = {row['status']: row['count'] for row in status_results}
        except Exception as e:
            # 如果status字段不存在，使用is_active字段
            utils.logger.warning(f"status字段不存在，使用is_active字段: {e}")
            status_query = """
                SELECT 
                    CASE WHEN is_active = 1 THEN 'active' ELSE 'inactive' END as status,
                    COUNT(*) as count 
                FROM proxy_pool 
                GROUP BY is_active
            """
            status_results = await db.query(status_query)
            by_status = {row['status']: row['count'] for row in status_results}
        
        # 提供商统计
        provider_query = """
            SELECT provider, COUNT(*) as count 
            FROM proxy_pool 
            GROUP BY provider
        """
        provider_results = await db.query(provider_query)
        by_provider = {row['provider']: row['count'] for row in provider_results}
        
        # 平台统计
        platform_query = """
            SELECT platform, COUNT(*) as count 
            FROM proxy_pool 
            WHERE platform IS NOT NULL
            GROUP BY platform
        """
        platform_results = await db.query(platform_query)
        by_platform = {row['platform']: row['count'] for row in platform_results}
        
        # 平均成功率
        success_rate_query = "SELECT AVG(success_rate) as avg_rate FROM proxy_pool WHERE success_rate > 0"
        success_rate_result = await db.get_first(success_rate_query)
        avg_success_rate = success_rate_result['avg_rate'] if success_rate_result and success_rate_result['avg_rate'] else 0.0
        
        # 总使用次数
        usage_query = "SELECT SUM(usage_count) as total_usage FROM proxy_pool"
        usage_result = await db.get_first(usage_query)
        total_usage_count = usage_result['total_usage'] if usage_result and usage_result['total_usage'] else 0
        
        stats = ProxyStats(
            total_proxies=total_proxies,
            active_proxies=by_status.get('active', 0),
            expired_proxies=by_status.get('expired', 0),
            failed_proxies=by_status.get('failed', 0),
            by_provider=by_provider,
            by_platform=by_platform,
            by_status=by_status,
            avg_success_rate=round(avg_success_rate, 2),
            total_usage_count=total_usage_count
        )
        
        return stats
        
    except Exception as e:
        utils.logger.error(f"获取代理统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取代理统计失败: {str(e)}")

@proxy_router.get("/proxies/usage/logs")
async def get_proxy_usage_logs(
    proxy_id: Optional[str] = Query(None, description="代理ID筛选"),
    success: Optional[bool] = Query(None, description="成功状态筛选"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取代理使用日志"""
    try:
        db = await get_db()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if proxy_id:
            conditions.append("proxy_id = %s")
            params.append(proxy_id)
        
        if success is not None:
            conditions.append("success = %s")
            params.append(1 if success else 0)
        
        if start_date:
            conditions.append("add_ts >= %s")
            params.append(int(start_date.timestamp() * 1000))
        
        if end_date:
            conditions.append("add_ts <= %s")
            params.append(int(end_date.timestamp() * 1000))
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 查询使用日志
        query = f"""
            SELECT * FROM proxy_usage_log{where_clause}
            ORDER BY add_ts DESC
            LIMIT %s OFFSET %s
        """
        
        results = await db.query(query, *(params + [page_size, offset]))
        
        # 转换时间戳
        for row in results:
            if row.get('add_ts'):
                row['add_ts'] = datetime.fromtimestamp(row['add_ts'] / 1000)
        
        return {
            "logs": results,
            "page": page,
            "page_size": page_size,
            "total": len(results)
        }
        
    except Exception as e:
        utils.logger.error(f"获取代理使用日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取代理使用日志失败: {str(e)}")

@proxy_router.post("/proxies/{proxy_id}/test")
async def test_proxy(proxy_id: str):
    """测试代理连接"""
    try:
        db = await get_db()
        
        # 获取代理信息
        query = "SELECT * FROM proxy_pool WHERE proxy_id = %s"
        row = await db.get_first(query, proxy_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="代理不存在")
        
        # 测试代理连接
        import httpx
        import time
        
        proxy_url = f"{row['proxy_type']}://"
        if row.get('username'):
            proxy_url += f"{row['username']}"
            if row.get('password'):
                proxy_url += f":{row['password']}"
            proxy_url += "@"
        
        proxy_url += f"{row['ip']}:{row['port']}"
        
        proxies = {
            "http://": proxy_url,
            "https://": proxy_url
        }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(proxies=proxies, timeout=10.0) as client:
                response = await client.get("http://httpbin.org/ip")
                
                if response.status_code == 200:
                    speed = int((time.time() - start_time) * 1000)
                    
                    # 更新代理信息
                    update_query = """
                        UPDATE proxy_pool SET 
                            speed = %s, success_rate = 100, last_check = %s,
                            success_count = success_count + 1, updated_at = %s
                        WHERE proxy_id = %s
                    """
                    await db.execute(update_query, speed, datetime.now(), datetime.now(), proxy_id)
                    
                    return {
                        "success": True,
                        "speed": speed,
                        "response": response.json()
                    }
                else:
                    # 更新失败信息
                    update_query = """
                        UPDATE proxy_pool SET 
                            fail_count = fail_count + 1, last_check = %s, updated_at = %s
                        WHERE proxy_id = %s
                    """
                    await db.execute(update_query, datetime.now(), datetime.now(), proxy_id)
                    
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    }
                    
        except Exception as e:
            # 更新失败信息
            update_query = """
                UPDATE proxy_pool SET 
                    fail_count = fail_count + 1, last_check = %s, updated_at = %s
                WHERE proxy_id = %s
            """
            await db.execute(update_query, datetime.now(), datetime.now(), proxy_id)
            
            return {
                "success": False,
                "error": str(e)
            }
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"测试代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试代理失败: {str(e)}")

@proxy_router.post("/proxies/{proxy_id}/enable")
async def enable_proxy(proxy_id: str):
    """启用代理"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 启用代理
        success = await proxy_manager.enable_proxy(proxy_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="启用代理失败")
        
        return {
            "success": True,
            "message": "代理启用成功"
        }
        
    except Exception as e:
        utils.logger.error(f"启用代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"启用代理失败: {str(e)}")

@proxy_router.post("/proxies/{proxy_id}/disable")
async def disable_proxy(proxy_id: str):
    """禁用代理"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 禁用代理
        success = await proxy_manager.disable_proxy(proxy_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="禁用代理失败")
        
        return {
            "success": True,
            "message": "代理禁用成功"
        }
        
    except Exception as e:
        utils.logger.error(f"禁用代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"禁用代理失败: {str(e)}")

@proxy_router.post("/proxies/cleanup/expired")
async def cleanup_expired_proxies():
    """清理过期代理"""
    try:
        db = await get_db()
        
        # 清理过期代理
        import time
        current_ts = int(time.time())
        
        update_query = """
            UPDATE proxy_pool SET 
                status = 'expired', updated_at = %s
            WHERE expire_ts <= %s AND status = 'active'
        """
        
        result = await db.execute(update_query, datetime.now(), current_ts)
        
        return {
            "message": "过期代理清理完成",
            "affected_rows": result
        }
        
    except Exception as e:
        utils.logger.error(f"清理过期代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理过期代理失败: {str(e)}")

# ==================== 青果长效代理专用API ====================

@proxy_router.post("/qingguo/extract")
async def extract_qingguo_proxy(
    region: str = Query("北京", description="区域名称"),
    isp: str = Query("电信", description="运营商名称"),
    description: Optional[str] = Query(None, description="描述信息")
):
    """提取青果长效代理"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 提取代理
        proxy_info = await proxy_manager.extract_proxy(region, isp, description)
        
        if not proxy_info:
            raise HTTPException(status_code=500, detail="提取代理失败")
        
        return {
            "success": True,
            "proxy": {
                "proxy_id": proxy_info.proxy_id,
                "ip": proxy_info.ip,
                "port": proxy_info.port,
                "username": proxy_info.username,
                "password": proxy_info.password,
                "expire_ts": proxy_info.expire_ts,
                "platform": proxy_info.platform,
                "account_id": proxy_info.account_id
            }
        }
        
    except Exception as e:
        utils.logger.error(f"提取青果代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"提取青果代理失败: {str(e)}")

@proxy_router.get("/qingguo/in-use")
async def get_qingguo_in_use_proxies():
    """查询青果代理在用IP"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 查询在用代理
        proxies = await proxy_manager.get_in_use_proxies()
        
        return {
            "success": True,
            "proxies": [
                {
                    "proxy_id": proxy.id,
                    "ip": proxy.ip,
                    "port": proxy.port,
                    "area": proxy.area,
                    "description": proxy.description,
                    "expire_ts": proxy.expire_ts,
                    "status": proxy.status.value
                }
                for proxy in proxies
            ],
            "total": len(proxies)
        }
        
    except Exception as e:
        utils.logger.error(f"查询青果在用代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询青果在用代理失败: {str(e)}")

@proxy_router.delete("/qingguo/release/{proxy_id}")
async def release_qingguo_proxy(proxy_id: str):
    """释放青果代理"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 释放代理
        success = await proxy_manager.release_proxy(proxy_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="释放代理失败")
        
        return {
            "success": True,
            "message": "代理释放成功"
        }
        
    except Exception as e:
        utils.logger.error(f"释放青果代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"释放青果代理失败: {str(e)}")

@proxy_router.get("/qingguo/channels")
async def get_qingguo_channels():
    """查询青果代理通道数"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 查询通道数
        channels = await proxy_manager.get_channels()
        
        return {
            "success": True,
            "channels": channels
        }
        
    except Exception as e:
        utils.logger.error(f"查询青果通道数失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询青果通道数失败: {str(e)}")

@proxy_router.get("/qingguo/resources")
async def get_qingguo_resources():
    """查询青果代理资源地区"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 查询资源地区
        resources = await proxy_manager.get_resources()
        
        return {
            "success": True,
            "resources": resources
        }
        
    except Exception as e:
        utils.logger.error(f"查询青果资源地区失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询青果资源地区失败: {str(e)}")

@proxy_router.get("/qingguo/available-count")
async def get_qingguo_available_count():
    """查询青果代理可用数量"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 查询在用代理
        proxies = await proxy_manager.get_in_use_proxies()
        
        return {
            "success": True,
            "count": len(proxies)
        }
        
    except Exception as e:
        utils.logger.error(f"查询青果可用代理数量失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询青果可用代理数量失败: {str(e)}")

@proxy_router.post("/qingguo/sync-from-query")
async def sync_qingguo_proxies_from_query():
    """从query API同步代理信息到数据库"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 同步代理信息
        synced_proxies = await proxy_manager.sync_proxies_from_query()
        
        return {
            "success": True,
            "message": f"成功同步 {len(synced_proxies)} 个代理",
            "proxies": [
                {
                    "proxy_id": proxy.id,
                    "ip": proxy.ip,
                    "port": proxy.port,
                    "area": proxy.area,
                    "description": proxy.description
                }
                for proxy in synced_proxies
            ],
            "count": len(synced_proxies)
        }
        
    except Exception as e:
        utils.logger.error(f"同步青果代理信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"同步青果代理信息失败: {str(e)}")

@proxy_router.get("/qingguo/whitelist")
async def get_qingguo_whitelist():
    """查询青果代理IP白名单"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 查询白名单
        whitelist = await proxy_manager.get_whitelist()
        
        return {
            "success": True,
            "whitelist": whitelist
        }
        
    except Exception as e:
        utils.logger.error(f"查询青果白名单失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询青果白名单失败: {str(e)}")

@proxy_router.post("/qingguo/whitelist/add")
async def add_qingguo_whitelist(ip: str = Query(..., description="要添加的IP地址")):
    """添加青果代理IP白名单"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 添加白名单
        success = await proxy_manager.add_whitelist(ip)
        
        if not success:
            raise HTTPException(status_code=500, detail="添加白名单失败")
        
        return {
            "success": True,
            "message": f"IP {ip} 已添加到白名单"
        }
        
    except Exception as e:
        utils.logger.error(f"添加青果白名单失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加青果白名单失败: {str(e)}")

@proxy_router.delete("/qingguo/whitelist/remove")
async def remove_qingguo_whitelist(ip: str = Query(..., description="要删除的IP地址")):
    """删除青果代理IP白名单"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 删除白名单
        success = await proxy_manager.remove_whitelist(ip)
        
        if not success:
            raise HTTPException(status_code=500, detail="删除白名单失败")
        
        return {
            "success": True,
            "message": f"IP {ip} 已从白名单删除"
        }
        
    except Exception as e:
        utils.logger.error(f"删除青果白名单失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除青果白名单失败: {str(e)}")

@proxy_router.get("/qingguo/balance")
async def get_qingguo_balance():
    """查询青果代理账户余额"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 查询余额
        balance = await proxy_manager.get_balance()
        
        return {
            "success": True,
            "balance": balance
        }
        
    except Exception as e:
        utils.logger.error(f"查询青果余额失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询青果余额失败: {str(e)}")

@proxy_router.post("/qingguo/batch-extract")
async def batch_extract_qingguo_proxies(
    region: str = Query("北京", description="区域名称"),
    isp: str = Query("电信", description="运营商名称"),
    count: int = Query(5, ge=1, le=10, description="批量提取数量")
):
    """批量提取青果长效代理"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 首先检查通道空闲数
        channels = await proxy_manager.get_channels()
        idle_count = channels.get("idle", 0)
        
        utils.logger.info(f"[批量提取] 当前通道空闲数: {idle_count}, 请求提取数: {count}")
        
        # 如果请求数量大于空闲数，调整提取数量
        if count > idle_count:
            if idle_count == 0:
                # 如果空闲数为0，先尝试清理旧代理
                utils.logger.warning(f"[批量提取] 空闲数为0，先清理旧代理")
                await proxy_manager._cleanup_old_proxies_for_extraction(max_delete_count=count)
                
                # 重新检查空闲数
                channels = await proxy_manager.get_channels()
                idle_count = channels.get("idle", 0)
                utils.logger.info(f"[批量提取] 清理后通道空闲数: {idle_count}")
                
                if idle_count == 0:
                    raise HTTPException(status_code=400, detail="通道已满，无法提取代理")
            
            # 限制提取数量不超过空闲数
            actual_count = min(count, idle_count)
            utils.logger.warning(f"[批量提取] 请求数量({count})超过空闲数({idle_count})，调整为{actual_count}")
        else:
            actual_count = count
        
        # 批量提取代理
        results = []
        success_count = 0
        fail_count = 0
        
        for i in range(actual_count):
            try:
                proxy_info = await proxy_manager.extract_proxy(
                    region=region,
                    isp=isp,
                    description=f"批量提取-{i+1}"
                )
                if proxy_info:
                    results.append({
                        "index": i + 1,
                        "success": True,
                        "proxy": {
                            "proxy_id": proxy_info.id,
                            "ip": proxy_info.ip,
                            "port": proxy_info.port,
                            "area": proxy_info.area,
                            "description": proxy_info.description
                        }
                    })
                    success_count += 1
                else:
                    results.append({
                        "index": i + 1,
                        "success": False,
                        "error": "提取失败"
                    })
                    fail_count += 1
            except Exception as e:
                results.append({
                    "index": i + 1,
                    "success": False,
                    "error": str(e)
                })
                fail_count += 1
        

        
        return {
            "success": True,
            "total": count,
            "success_count": success_count,
            "fail_count": count - success_count,
            "results": results
        }
        
    except Exception as e:
        utils.logger.error(f"批量提取青果代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量提取青果代理失败: {str(e)}")

@proxy_router.post("/qingguo/health-check")
async def health_check_qingguo_proxies():
    """青果代理健康检查"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 获取所有活跃代理
        db = await get_db()
        query = "SELECT * FROM proxy_pool WHERE provider = 'qingguo' AND status = 'active'"
        proxies = await db.query(query)
        
        results = []
        for proxy in proxies:
            try:
                # 测试代理连接
                test_result = await test_proxy(proxy['proxy_id'])
                
                results.append({
                    "proxy_id": proxy['proxy_id'],
                    "ip": proxy['ip'],
                    "port": proxy['port'],
                    "success": test_result.get("success", False),
                    "speed": test_result.get("speed"),
                    "error": test_result.get("error")
                })
                
            except Exception as e:
                results.append({
                    "proxy_id": proxy['proxy_id'],
                    "ip": proxy['ip'],
                    "port": proxy['port'],
                    "success": False,
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r["success"])
        total_count = len(results)
        
        return {
            "success": True,
            "total": total_count,
            "success_count": success_count,
            "fail_count": total_count - success_count,
            "success_rate": round(success_count / total_count * 100, 2) if total_count > 0 else 0,
            "results": results
        }
        
    except Exception as e:
        utils.logger.error(f"青果代理健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"青果代理健康检查失败: {str(e)}")
