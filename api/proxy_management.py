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
class ProxyAccount(BaseModel):
    """代理账号模型"""
    id: int
    account_id: str
    provider: str
    provider_name: str
    api_key: str
    api_secret: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    signature: Optional[str] = None
    endpoint_url: Optional[str] = None
    is_active: bool = True
    is_default: bool = False
    max_pool_size: int = 10
    validate_ip: bool = True
    description: Optional[str] = None
    config_json: Optional[Dict] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    created_at: datetime
    updated_at: datetime

class ProxyAccountCreate(BaseModel):
    """创建代理账号请求模型"""
    account_id: str = Field(..., description="账号唯一标识")
    provider: str = Field(..., description="代理提供商")
    provider_name: str = Field(..., description="提供商中文名称")
    api_key: str = Field(..., description="API密钥")
    api_secret: Optional[str] = Field(None, description="API密钥（可选）")
    username: Optional[str] = Field(None, description="用户名（可选）")
    password: Optional[str] = Field(None, description="密码（可选）")
    signature: Optional[str] = Field(None, description="签名（可选）")
    endpoint_url: Optional[str] = Field(None, description="API端点URL")
    is_active: bool = Field(True, description="是否启用")
    is_default: bool = Field(False, description="是否默认账号")
    max_pool_size: int = Field(10, description="最大代理池大小")
    validate_ip: bool = Field(True, description="是否验证IP")
    description: Optional[str] = Field(None, description="账号描述")
    config_json: Optional[Dict] = Field(None, description="额外配置JSON")

class ProxyAccountUpdate(BaseModel):
    """更新代理账号请求模型"""
    provider_name: Optional[str] = Field(None, description="提供商中文名称")
    api_key: Optional[str] = Field(None, description="API密钥")
    api_secret: Optional[str] = Field(None, description="API密钥（可选）")
    username: Optional[str] = Field(None, description="用户名（可选）")
    password: Optional[str] = Field(None, description="密码（可选）")
    signature: Optional[str] = Field(None, description="签名（可选）")
    endpoint_url: Optional[str] = Field(None, description="API端点URL")
    is_active: Optional[bool] = Field(None, description="是否启用")
    is_default: Optional[bool] = Field(None, description="是否默认账号")
    max_pool_size: Optional[int] = Field(None, description="最大代理池大小")
    validate_ip: Optional[bool] = Field(None, description="是否验证IP")
    description: Optional[str] = Field(None, description="账号描述")
    config_json: Optional[Dict] = Field(None, description="额外配置JSON")

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
    account_id: Optional[str] = None
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
    account_id: Optional[str] = Field(None, description="关联账号ID")
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
    account_id: Optional[str] = Field(None, description="关联账号ID")
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
                account_id=row.get('account_id'),
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

# 释放代理功能已移除 - 动态型代理不支持释放IP
# 请使用启用/禁用功能来管理代理状态
# @proxy_router.delete("/proxies/{proxy_id}")
# async def release_proxy(proxy_id: str):
#     """释放代理"""
#     try:
#         db = await get_db()
#         
#         # 检查代理是否存在并获取代理信息
#         check_query = "SELECT * FROM proxy_pool WHERE proxy_id = %s"
#         proxy = await db.get_first(check_query, proxy_id)
#         
#         if not proxy:
#             raise HTTPException(status_code=404, detail="代理不存在")
#         
#         # 如果是青果代理，尝试调用青果API删除
#         api_delete_success = False
#         if proxy.get('provider') == 'qingguo':
#             from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
#             
#             proxy_manager = await get_qingguo_proxy_manager()
#             
#             # 调用青果API删除代理
#             api_delete_success = await proxy_manager.delete_proxy_from_api(proxy['ip'])
#             
#             if not api_delete_success:
#                 utils.logger.warning(f"青果API删除失败（可能没有权限），但仍会从数据库删除代理: {proxy_id}")
#         
#         # 从数据库删除代理
#         delete_query = "DELETE FROM proxy_pool WHERE proxy_id = %s"
#         await db.execute(delete_query, proxy_id)
#         
#         # 根据API删除结果返回不同的消息
#         if proxy.get('provider') == 'qingguo' and not api_delete_success:
#             return {
#                 "success": True,
#                 "message": "代理已从数据库释放（青果API删除失败，请手动处理）"
#             }
#         else:
#             return {
#                 "success": True,
#                 "message": "代理释放成功"
#             }
#         
#     except HTTPException:
#         raise
#     except Exception as e:
#         utils.logger.error(f"释放代理失败: {e}")
#         raise HTTPException(status_code=500, detail=f"释放代理失败: {str(e)}")

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
        
        # 打印代理信息
        utils.logger.info(f"[代理测试] 开始测试代理: {proxy_id}")
        utils.logger.info(f"[代理测试] 代理信息: IP={row['ip']}, Port={row['port']}, Type={row['proxy_type']}")
        utils.logger.info(f"[代理测试] 用户名: {row.get('username', '无')}, 密码: {'***' if row.get('password') else '无'}")
        
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
        
        utils.logger.info(f"[代理测试] 构建的代理URL: {proxy_url}")
        utils.logger.info(f"[代理测试] 代理配置: {proxies}")
        
        start_time = time.time()
        
        # 只保留能成功连接的测试网站（优先使用ip-api.com，返回更丰富的信息）
        test_urls = [
            "http://ip-api.com/json"  # 返回详细的IP地理位置信息
        ]
        
        utils.logger.info(f"[代理测试] 测试网站列表: {test_urls}")
        
        response = None
        used_url = ""
        
        for test_url in test_urls:
            utils.logger.info(f"[代理测试] 尝试测试URL: {test_url}")
            
            try:
                utils.logger.info(f"[代理测试] 开始发送请求...")
                async with httpx.AsyncClient(proxies=proxies, timeout=10.0) as client:
                    response = await client.get(test_url)
                    used_url = test_url
                    break  # 如果成功，跳出循环
                    
            except Exception as e:
                utils.logger.warning(f"[代理测试] URL {test_url} 测试失败: {e}")
                continue
        
        if not response:
            raise Exception("所有测试网站都无法访问")
        
        utils.logger.info(f"[代理测试] 成功使用URL: {used_url}")
        utils.logger.info(f"[代理测试] 收到响应: HTTP {response.status_code}")
        utils.logger.info(f"[代理测试] 响应头: {dict(response.headers)}")
        
        # 尝试获取响应内容
        try:
            response_text = response.text
            utils.logger.info(f"[代理测试] 响应内容: {response_text}")
            
            if response.status_code == 200:
                # 尝试解析JSON，如果失败则使用原始文本
                try:
                    response_json = response.json()
                    utils.logger.info(f"[代理测试] 响应JSON: {response_json}")
                    response_data = response_json
                except Exception as json_error:
                    utils.logger.info(f"[代理测试] 响应不是JSON格式，使用原始文本: {response_text}")
                    # 对于纯文本IP地址，构造标准格式
                    if response_text.strip().replace('.', '').isdigit() or ':' in response_text:
                        # 看起来像IP地址
                        response_data = {"origin": response_text.strip()}
                    else:
                        response_data = {"text": response_text.strip()}
                
                speed = int((time.time() - start_time) * 1000)
                utils.logger.info(f"[代理测试] 测试成功! 响应时间: {speed}ms")
                
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
                    "response": response_data,
                    "test_url": used_url,
                    "proxy_info": {
                        "ip": row['ip'],
                        "port": row['port'],
                        "proxy_type": row['proxy_type'],
                        "username": row.get('username'),
                        "has_password": bool(row.get('password'))
                    }
                }
            else:
                utils.logger.error(f"[代理测试] HTTP错误: {response.status_code}")
                utils.logger.error(f"[代理测试] 错误响应: {response_text}")
                
                # 更新失败信息
                update_query = """
                    UPDATE proxy_pool SET 
                        fail_count = fail_count + 1, last_check = %s, updated_at = %s
                    WHERE proxy_id = %s
                """
                await db.execute(update_query, datetime.now(), datetime.now(), proxy_id)
                
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response_text": response_text,
                    "test_url": used_url,
                    "proxy_info": {
                        "ip": row['ip'],
                        "port": row['port'],
                        "proxy_type": row['proxy_type']
                    }
                }
                
        except Exception as parse_error:
            utils.logger.error(f"[代理测试] 解析响应内容失败: {parse_error}")
            utils.logger.error(f"[代理测试] 原始响应: {response_text}")
            
            return {
                "success": False,
                "error": f"响应解析失败: {str(parse_error)}",
                "response_text": response_text,
                "test_url": used_url,
                "proxy_info": {
                    "ip": row['ip'],
                    "port": row['port'],
                    "proxy_type": row['proxy_type']
                }
            }
                    
        except httpx.ConnectTimeout:
            error_msg = "连接超时"
            utils.logger.error(f"[代理测试] {error_msg}")
            
            # 更新失败信息
            update_query = """
                UPDATE proxy_pool SET 
                    fail_count = fail_count + 1, last_check = %s, updated_at = %s
                WHERE proxy_id = %s
            """
            await db.execute(update_query, datetime.now(), datetime.now(), proxy_id)
            
            return {
                "success": False,
                "error": error_msg,
                "proxy_info": {
                    "ip": row['ip'],
                    "port": row['port'],
                    "proxy_type": row['proxy_type']
                }
            }
            
        except httpx.ProxyError as e:
            error_msg = f"代理错误: {str(e)}"
            utils.logger.error(f"[代理测试] {error_msg}")
            
            # 更新失败信息
            update_query = """
                UPDATE proxy_pool SET 
                    fail_count = fail_count + 1, last_check = %s, updated_at = %s
                WHERE proxy_id = %s
            """
            await db.execute(update_query, datetime.now(), datetime.now(), proxy_id)
            
            return {
                "success": False,
                "error": error_msg,
                "proxy_info": {
                    "ip": row['ip'],
                    "port": row['port'],
                    "proxy_type": row['proxy_type']
                }
            }
            
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            utils.logger.error(f"[代理测试] {error_msg}")
            utils.logger.error(f"[代理测试] 异常类型: {type(e).__name__}")
            
            # 更新失败信息
            update_query = """
                UPDATE proxy_pool SET 
                    fail_count = fail_count + 1, last_check = %s, updated_at = %s
                WHERE proxy_id = %s
            """
            await db.execute(update_query, datetime.now(), datetime.now(), proxy_id)
            
            return {
                "success": False,
                "error": error_msg,
                "proxy_info": {
                    "ip": row['ip'],
                    "port": row['port'],
                    "proxy_type": row['proxy_type']
                }
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
    account_id: str = Query(..., description="代理账号ID"),
    region: Optional[str] = Query(None, description="区域名称，为空时自动选择"),
    isp: Optional[str] = Query(None, description="运营商名称，为空时自动选择"),
    description: Optional[str] = Query(None, description="描述信息")
):
    """提取青果长效代理"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 验证代理账号
        db = await get_db()
        account_query = "SELECT * FROM proxy_accounts WHERE account_id = %s AND provider = 'qingguo'"
        account = await db.get_first(account_query, account_id)
        
        if not account:
            raise HTTPException(status_code=404, detail="代理账号不存在或不是青果代理")
        
        # 如果区域或运营商为空，自动选择
        if not region or not isp:
            auto_region, auto_isp = await proxy_manager.get_random_available_region()
            region = region or auto_region
            isp = isp or auto_isp
            utils.logger.info(f"[提取代理] 自动选择区域: {region}, 运营商: {isp}")
        
        # 提取代理
        proxy_info = await proxy_manager.extract_proxy(region, isp, description, account_id)
        
        if not proxy_info:
            raise HTTPException(status_code=500, detail="提取代理失败")
        
        return {
            "success": True,
            "proxy": {
                "proxy_id": proxy_info.id,
                "ip": proxy_info.ip,
                "port": proxy_info.port,
                "username": proxy_info.username,
                "password": proxy_info.password,
                "expire_ts": proxy_info.expire_ts,
                "area": proxy_info.area,
                "description": proxy_info.description,
                "proxy_type": proxy_info.proxy_type,
                "usage_count": proxy_info.usage_count,
                "success_count": proxy_info.success_count,
                "fail_count": proxy_info.fail_count,
                "status": proxy_info.status.value,
                "enabled": proxy_info.enabled,
                "created_at": proxy_info.created_at.isoformat() if proxy_info.created_at else None,
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
                    "status": proxy.status.value,
                    "username": proxy.username,
                    "password": proxy.password,
                    "proxy_type": proxy.proxy_type,
                    "usage_count": proxy.usage_count,
                    "success_count": proxy.success_count,
                    "fail_count": proxy.fail_count,
                    "last_used_at": proxy.last_used_at.isoformat() if proxy.last_used_at else None,
                    "created_at": proxy.created_at.isoformat() if proxy.created_at else None,
                    "task_id": proxy.task_id,
                    "proxy_ip": proxy.proxy_ip,
                    "account_id": proxy.account_id
                }
                for proxy in proxies
            ],
            "total": len(proxies)
        }
        
    except Exception as e:
        utils.logger.error(f"查询青果在用代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询青果在用代理失败: {str(e)}")

# 青果代理释放功能已移除 - 动态型代理不支持释放IP
# 请使用启用/禁用功能来管理代理状态
# @proxy_router.delete("/qingguo/release/{proxy_id}")
# async def release_qingguo_proxy(proxy_id: str):
#     """释放青果代理"""
#     try:
#         from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
#         
#         proxy_manager = await get_qingguo_proxy_manager()
#         
#         # 释放代理
#         success = await proxy_manager.release_proxy(proxy_id)
#         
#         if not success:
#             raise HTTPException(status_code=500, detail="释放代理失败")
#         
#         return {
#             "success": True,
#             "message": "代理释放成功"
#         }
#         
#     except Exception as e:
#         utils.logger.error(f"释放青果代理失败: {e}")
#         raise HTTPException(status_code=500, detail=f"释放青果代理失败: {str(e)}")

@proxy_router.post("/proxies/{proxy_id}/sync")
async def sync_proxy(proxy_id: str):
    """同步单个代理信息"""
    try:
        db = await get_db()
        
        # 检查代理是否存在并获取代理信息
        check_query = "SELECT * FROM proxy_pool WHERE proxy_id = %s"
        proxy = await db.get_first(check_query, proxy_id)
        
        if not proxy:
            raise HTTPException(status_code=404, detail="代理不存在")
        
        # 如果是青果代理，进行同步
        if proxy.get('provider') == 'qingguo':
            from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
            
            proxy_manager = await get_qingguo_proxy_manager()
            
            # 获取代理的账号信息
            account_id = proxy.get('account_id', 'qingguo_default')
            
            # 同步该账号下的所有代理
            synced_proxies = await proxy_manager.sync_proxies_from_query(account_id)
            
            # 查找同步后的代理信息
            updated_query = "SELECT * FROM proxy_pool WHERE proxy_id = %s"
            updated_proxy = await db.get_first(updated_query, proxy_id)
            
            if updated_proxy:
                return {
                    "success": True,
                    "message": f"代理同步成功，共同步 {len(synced_proxies)} 个代理",
                    "proxy": {
                        "proxy_id": updated_proxy['proxy_id'],
                        "ip": updated_proxy['ip'],
                        "port": updated_proxy['port'],
                        "area": updated_proxy.get('area'),
                        "expire_ts": updated_proxy.get('expire_ts'),
                        "status": updated_proxy.get('status'),
                        "enabled": updated_proxy.get('enabled'),
                        "task_id": updated_proxy.get('task_id'),
                        "proxy_ip": updated_proxy.get('proxy_ip')
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"代理同步成功，但当前代理可能已被更新，共同步 {len(synced_proxies)} 个代理"
                }
        else:
            return {
                "success": False,
                "message": "只支持青果代理的同步功能"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"同步代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"同步代理失败: {str(e)}")

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
                    "description": proxy.description,
                    "username": proxy.username,
                    "password": proxy.password,
                    "proxy_type": proxy.proxy_type,
                    "usage_count": proxy.usage_count,
                    "success_count": proxy.success_count,
                    "fail_count": proxy.fail_count,
                    "status": proxy.status.value,
                    "enabled": proxy.enabled,
                    "created_at": proxy.created_at.isoformat() if proxy.created_at else None,
                    "account_id": proxy.account_id
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
    account_id: str = Query(..., description="代理账号ID"),
    region: Optional[str] = Query(None, description="区域名称，为空时自动选择"),
    isp: Optional[str] = Query(None, description="运营商名称，为空时自动选择"),
    count: int = Query(5, ge=1, le=10, description="批量提取数量")
):
    """批量提取青果长效代理"""
    try:
        from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager
        
        proxy_manager = await get_qingguo_proxy_manager()
        
        # 验证代理账号
        db = await get_db()
        account_query = "SELECT * FROM proxy_accounts WHERE account_id = %s AND provider = 'qingguo'"
        account = await db.get_first(account_query, account_id)
        
        if not account:
            raise HTTPException(status_code=404, detail="代理账号不存在或不是青果代理")
        
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
        
        # 如果区域或运营商为空，自动选择
        if not region or not isp:
            auto_region, auto_isp = await proxy_manager.get_random_available_region()
            region = region or auto_region
            isp = isp or auto_isp
            utils.logger.info(f"[批量提取] 自动选择区域: {region}, 运营商: {isp}")
        
        # 批量提取代理
        results = []
        success_count = 0
        fail_count = 0
        
        for i in range(actual_count):
            try:
                proxy_info = await proxy_manager.extract_proxy(
                    region=region,
                    isp=isp,
                    description=f"批量提取-{i+1}",
                    account_id=account_id
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
                            "description": proxy_info.description,
                            "username": proxy_info.username,
                            "password": proxy_info.password,
                            "proxy_type": proxy_info.proxy_type,
                            "usage_count": proxy_info.usage_count,
                            "success_count": proxy_info.success_count,
                            "fail_count": proxy_info.fail_count,
                            "status": proxy_info.status.value,
                            "enabled": proxy_info.enabled,
                            "created_at": proxy_info.created_at.isoformat() if proxy_info.created_at else None,
                            "account_id": proxy_info.account_id
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
                    "error": test_result.get("error"),
                    "area": proxy.get('area'),
                    "description": proxy.get('description'),
                    "username": proxy.get('username'),
                    "password": proxy.get('password'),
                    "proxy_type": proxy.get('proxy_type', 'http'),
                    "usage_count": proxy.get('usage_count', 0),
                    "success_count": proxy.get('success_count', 0),
                    "fail_count": proxy.get('fail_count', 0),
                    "status": proxy.get('status', 'active'),
                    "enabled": proxy.get('enabled', True)
                })
                
            except Exception as e:
                results.append({
                    "proxy_id": proxy['proxy_id'],
                    "ip": proxy['ip'],
                    "port": proxy['port'],
                    "success": False,
                    "error": str(e),
                    "area": proxy.get('area'),
                    "description": proxy.get('description'),
                    "username": proxy.get('username'),
                    "password": proxy.get('password'),
                    "proxy_type": proxy.get('proxy_type', 'http'),
                    "usage_count": proxy.get('usage_count', 0),
                    "success_count": proxy.get('success_count', 0),
                    "fail_count": proxy.get('fail_count', 0),
                    "status": proxy.get('status', 'active'),
                    "enabled": proxy.get('enabled', True)
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

# ==================== 代理账号管理API ====================

@proxy_router.get("/proxy-accounts/", response_model=List[ProxyAccount])
async def get_proxy_accounts(
    provider: Optional[str] = Query(None, description="提供商筛选"),
    is_active: Optional[bool] = Query(None, description="启用状态筛选"),
    is_default: Optional[bool] = Query(None, description="默认账号筛选")
):
    """获取代理账号列表"""
    try:
        db = await get_db()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if provider:
            conditions.append("provider = %s")
            params.append(provider)
        
        if is_active is not None:
            conditions.append("is_active = %s")
            params.append(1 if is_active else 0)
        
        if is_default is not None:
            conditions.append("is_default = %s")
            params.append(1 if is_default else 0)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 查询代理账号列表
        query = f"""
            SELECT * FROM proxy_accounts{where_clause}
            ORDER BY is_default DESC, created_at DESC
        """
        
        results = await db.query(query, *params)
        
        # 转换结果
        accounts = []
        for row in results:
            account = ProxyAccount(
                id=row['id'],
                account_id=row['account_id'],
                provider=row['provider'],
                provider_name=row['provider_name'],
                api_key=row['api_key'],
                api_secret=row.get('api_secret'),
                username=row.get('username'),
                password=row.get('password'),
                signature=row.get('signature'),
                endpoint_url=row.get('endpoint_url'),
                is_active=bool(row['is_active']),
                is_default=bool(row['is_default']),
                max_pool_size=row['max_pool_size'],
                validate_ip=bool(row['validate_ip']),
                description=row.get('description'),
                config_json=json.loads(row['config_json']) if row.get('config_json') else None,
                last_used_at=row.get('last_used_at'),
                usage_count=row.get('usage_count', 0),
                success_count=row.get('success_count', 0),
                fail_count=row.get('fail_count', 0),
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            accounts.append(account)
        
        return accounts
        
    except Exception as e:
        utils.logger.error(f"获取代理账号列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取代理账号列表失败: {str(e)}")

@proxy_router.get("/proxy-accounts/{account_id}", response_model=ProxyAccount)
async def get_proxy_account(account_id: str):
    """获取单个代理账号详情"""
    try:
        db = await get_db()
        
        query = "SELECT * FROM proxy_accounts WHERE account_id = %s"
        row = await db.get_first(query, account_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="代理账号不存在")
        
        account = ProxyAccount(
            id=row['id'],
            account_id=row['account_id'],
            provider=row['provider'],
            provider_name=row['provider_name'],
            api_key=row['api_key'],
            api_secret=row.get('api_secret'),
            username=row.get('username'),
            password=row.get('password'),
            signature=row.get('signature'),
            endpoint_url=row.get('endpoint_url'),
            is_active=bool(row['is_active']),
            is_default=bool(row['is_default']),
            max_pool_size=row['max_pool_size'],
            validate_ip=bool(row['validate_ip']),
            description=row.get('description'),
            config_json=json.loads(row['config_json']) if row.get('config_json') else None,
            last_used_at=row.get('last_used_at'),
            usage_count=row.get('usage_count', 0),
            success_count=row.get('success_count', 0),
            fail_count=row.get('fail_count', 0),
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
        
        return account
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"获取代理账号详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取代理账号详情失败: {str(e)}")

@proxy_router.post("/proxy-accounts/", response_model=ProxyAccount)
async def create_proxy_account(account: ProxyAccountCreate):
    """创建新代理账号"""
    try:
        db = await get_db()
        
        # 检查账号是否已存在
        check_query = "SELECT COUNT(*) FROM proxy_accounts WHERE account_id = %s"
        result = await db.get_first(check_query, account.account_id)
        
        if result and list(result.values())[0] > 0:
            raise HTTPException(status_code=400, detail="代理账号ID已存在")
        
        # 如果设置为默认账号，先取消其他默认账号
        if account.is_default:
            await db.execute("UPDATE proxy_accounts SET is_default = 0 WHERE provider = %s", account.provider)
        
        # 插入新代理账号
        insert_query = """
            INSERT INTO proxy_accounts (
                account_id, provider, provider_name, api_key, api_secret,
                username, password, signature, endpoint_url, is_active,
                is_default, max_pool_size, validate_ip, description, config_json,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        await db.execute(insert_query,
            account.account_id, account.provider, account.provider_name,
            account.api_key, account.api_secret, account.username, account.password,
            account.signature, account.endpoint_url, 1 if account.is_active else 0,
            1 if account.is_default else 0, account.max_pool_size,
            1 if account.validate_ip else 0, account.description,
            json.dumps(account.config_json) if account.config_json else None,
            datetime.now(), datetime.now()
        )
        
        # 获取新创建的代理账号
        return await get_proxy_account(account.account_id)
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"创建代理账号失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建代理账号失败: {str(e)}")

@proxy_router.put("/proxy-accounts/{account_id}", response_model=ProxyAccount)
async def update_proxy_account(account_id: str, account: ProxyAccountUpdate):
    """更新代理账号信息"""
    try:
        db = await get_db()
        
        # 检查代理账号是否存在
        check_query = "SELECT COUNT(*) FROM proxy_accounts WHERE account_id = %s"
        result = await db.get_first(check_query, account_id)
        
        if not result or list(result.values())[0] == 0:
            raise HTTPException(status_code=404, detail="代理账号不存在")
        
        # 如果设置为默认账号，先取消其他默认账号
        if account.is_default:
            current_account = await get_proxy_account(account_id)
            await db.execute("UPDATE proxy_accounts SET is_default = 0 WHERE provider = %s", current_account.provider)
        
        # 构建更新语句
        updates = []
        params = []
        
        for field, value in account.dict(exclude_unset=True).items():
            if value is not None:
                if field in ['is_active', 'is_default', 'validate_ip']:
                    updates.append(f"{field} = %s")
                    params.append(1 if value else 0)
                elif field == 'config_json':
                    updates.append(f"{field} = %s")
                    params.append(json.dumps(value) if value else None)
                else:
                    updates.append(f"{field} = %s")
                    params.append(value)
        
        if not updates:
            raise HTTPException(status_code=400, detail="没有提供要更新的字段")
        
        # 执行更新
        update_query = f"UPDATE proxy_accounts SET {', '.join(updates)}, updated_at = %s WHERE account_id = %s"
        params.extend([datetime.now(), account_id])
        
        await db.execute(update_query, *params)
        
        # 清除该账号关联的所有代理IP
        utils.logger.info(f"[账号更新] 开始清除账号 {account_id} 关联的代理IP")
        
        # 查询该账号关联的代理数量
        count_query = "SELECT COUNT(*) as count FROM proxy_pool WHERE account_id = %s"
        count_result = await db.get_first(count_query, account_id)
        proxy_count = count_result['count'] if count_result else 0
        
        if proxy_count > 0:
            # 删除关联的代理IP
            delete_query = "DELETE FROM proxy_pool WHERE account_id = %s"
            await db.execute(delete_query, account_id)
            
            utils.logger.info(f"[账号更新] 已清除账号 {account_id} 关联的 {proxy_count} 个代理IP")
            
            # 记录清理日志
            log_query = """
                INSERT INTO proxy_account_logs (
                    account_id, provider, operation, success, response_time, error_message, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            await db.execute(log_query, account_id, "qingguo", "cleanup_proxies", 1, None, 
                           f"清除关联的 {proxy_count} 个代理IP", datetime.now())
        else:
            utils.logger.info(f"[账号更新] 账号 {account_id} 没有关联的代理IP需要清除")
        
        # 返回更新后的代理账号
        return await get_proxy_account(account_id)
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"更新代理账号失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新代理账号失败: {str(e)}")

@proxy_router.delete("/proxy-accounts/{account_id}")
async def delete_proxy_account(account_id: str):
    """删除代理账号"""
    try:
        db = await get_db()
        
        # 检查代理账号是否存在
        check_query = "SELECT COUNT(*) FROM proxy_accounts WHERE account_id = %s"
        result = await db.get_first(check_query, account_id)
        
        if not result or list(result.values())[0] == 0:
            raise HTTPException(status_code=404, detail="代理账号不存在")
        
        # 检查是否为默认账号
        account = await get_proxy_account(account_id)
        if account.is_default:
            raise HTTPException(status_code=400, detail="不能删除默认代理账号")
        
        # 清除该账号关联的所有代理IP
        utils.logger.info(f"[账号删除] 开始清除账号 {account_id} 关联的代理IP")
        
        # 查询该账号关联的代理数量
        count_query = "SELECT COUNT(*) as count FROM proxy_pool WHERE account_id = %s"
        count_result = await db.get_first(count_query, account_id)
        proxy_count = count_result['count'] if count_result else 0
        
        if proxy_count > 0:
            # 删除关联的代理IP
            delete_proxy_query = "DELETE FROM proxy_pool WHERE account_id = %s"
            await db.execute(delete_proxy_query, account_id)
            
            utils.logger.info(f"[账号删除] 已清除账号 {account_id} 关联的 {proxy_count} 个代理IP")
            
            # 记录清理日志
            log_query = """
                INSERT INTO proxy_account_logs (
                    account_id, provider, operation, success, response_time, error_message, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            await db.execute(log_query, account_id, "qingguo", "cleanup_proxies", 1, None, 
                           f"删除账号时清除关联的 {proxy_count} 个代理IP", datetime.now())
        else:
            utils.logger.info(f"[账号删除] 账号 {account_id} 没有关联的代理IP需要清除")
        
        # 删除代理账号
        delete_query = "DELETE FROM proxy_accounts WHERE account_id = %s"
        await db.execute(delete_query, account_id)
        
        return {
            "success": True,
            "message": f"代理账号删除成功，已清除 {proxy_count} 个关联代理IP"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"删除代理账号失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除代理账号失败: {str(e)}")

@proxy_router.post("/proxy-accounts/{account_id}/test")
async def test_proxy_account(account_id: str):
    """测试代理账号连接"""
    try:
        db = await get_db()
        
        # 获取代理账号信息
        query = "SELECT * FROM proxy_accounts WHERE account_id = %s"
        row = await db.get_first(query, account_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="代理账号不存在")
        
        # 打印账号信息
        utils.logger.info(f"[账号测试] 开始测试代理账号: {account_id}")
        utils.logger.info(f"[账号测试] 账号信息: Provider={row['provider']}, Name={row['provider_name']}")
        utils.logger.info(f"[账号测试] API Key: {row['api_key']}, API Secret: {'***' if row['api_secret'] else '无'}")
        
        # 根据提供商测试连接
        provider = row['provider']
        success = False
        error_message = None
        response_time = None
        
        try:
            if provider == 'qingguo':
                # 测试青果代理连接
                import httpx
                import time
                
                test_url = "https://longterm.proxy.qg.net/query"
                test_params = {
                    "key": row['api_key'],
                    "pwd": row['api_secret']
                }
                
                utils.logger.info(f"[账号测试] 测试URL: {test_url}")
                utils.logger.info(f"[账号测试] 请求参数: {test_params}")
                
                start_time = time.time()
                utils.logger.info(f"[账号测试] 开始发送请求...")
                
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(test_url, params=test_params)
                    
                    utils.logger.info(f"[账号测试] 收到响应: HTTP {response.status_code}")
                    utils.logger.info(f"[账号测试] 响应头: {dict(response.headers)}")
                    
                    # 尝试获取响应内容
                    try:
                        response_text = response.text
                        utils.logger.info(f"[账号测试] 响应内容: {response_text}")
                        
                        if response.status_code == 200:
                            data = response.json()
                            utils.logger.info(f"[账号测试] 响应JSON: {data}")
                            
                            if data.get("code") == "SUCCESS":
                                success = True
                                response_time = int((time.time() - start_time) * 1000)
                                utils.logger.info(f"[账号测试] 测试成功! 响应时间: {response_time}ms")
                            else:
                                error_message = f"API返回错误: {data.get('message', '未知错误')}"
                                utils.logger.error(f"[账号测试] {error_message}")
                        else:
                            error_message = f"HTTP错误: {response.status_code}"
                            utils.logger.error(f"[账号测试] {error_message}")
                            utils.logger.error(f"[账号测试] 错误响应: {response_text}")
                            
                    except Exception as parse_error:
                        utils.logger.error(f"[账号测试] 解析响应内容失败: {parse_error}")
                        utils.logger.error(f"[账号测试] 原始响应: {response_text}")
                        error_message = f"响应解析失败: {str(parse_error)}"
                        
            else:
                error_message = f"暂不支持测试 {provider} 提供商"
                utils.logger.warning(f"[账号测试] {error_message}")
                
        except httpx.ConnectTimeout:
            error_message = "连接超时"
            utils.logger.error(f"[账号测试] {error_message}")
            
        except httpx.RequestError as e:
            error_message = f"请求错误: {str(e)}"
            utils.logger.error(f"[账号测试] {error_message}")
            
        except Exception as e:
            error_message = f"未知错误: {str(e)}"
            utils.logger.error(f"[账号测试] {error_message}")
            utils.logger.error(f"[账号测试] 异常类型: {type(e).__name__}")
        
        # 记录测试结果
        log_query = """
            INSERT INTO proxy_account_logs (
                account_id, provider, operation, success, response_time, error_message, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        await db.execute(log_query, account_id, provider, "test", 1 if success else 0, 
                        response_time, error_message, datetime.now())
        
        # 更新账号统计
        if success:
            update_query = """
                UPDATE proxy_accounts SET 
                    success_count = success_count + 1, last_used_at = %s, updated_at = %s
                WHERE account_id = %s
            """
            await db.execute(update_query, datetime.now(), datetime.now(), account_id)
            utils.logger.info(f"[账号测试] 已更新账号成功统计")
        else:
            update_query = """
                UPDATE proxy_accounts SET 
                    fail_count = fail_count + 1, last_used_at = %s, updated_at = %s
                WHERE account_id = %s
            """
            await db.execute(update_query, datetime.now(), datetime.now(), account_id)
            utils.logger.info(f"[账号测试] 已更新账号失败统计")
        
        return {
            "success": success,
            "response_time": response_time,
            "error_message": error_message,
            "account_info": {
                "account_id": account_id,
                "provider": provider,
                "provider_name": row['provider_name']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"测试代理账号失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试代理账号失败: {str(e)}")

@proxy_router.get("/proxy-accounts/{account_id}/logs")
async def get_proxy_account_logs(
    account_id: str,
    operation: Optional[str] = Query(None, description="操作类型筛选"),
    success: Optional[bool] = Query(None, description="成功状态筛选"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取代理账号使用日志"""
    try:
        db = await get_db()
        
        # 构建查询条件
        conditions = ["account_id = %s"]
        params = [account_id]
        
        if operation:
            conditions.append("operation = %s")
            params.append(operation)
        
        if success is not None:
            conditions.append("success = %s")
            params.append(1 if success else 0)
        
        if start_date:
            conditions.append("created_at >= %s")
            params.append(start_date)
        
        if end_date:
            conditions.append("created_at <= %s")
            params.append(end_date)
        
        where_clause = " WHERE " + " AND ".join(conditions)
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 查询使用日志
        query = f"""
            SELECT * FROM proxy_account_logs{where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        
        results = await db.query(query, *(params + [page_size, offset]))
        
        return {
            "logs": results,
            "page": page,
            "page_size": page_size,
            "total": len(results)
        }
        
    except Exception as e:
        utils.logger.error(f"获取代理账号使用日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取代理账号使用日志失败: {str(e)}")

@proxy_router.post("/proxy-accounts/{account_id}/cleanup-proxies")
async def cleanup_account_proxies(account_id: str):
    """清理指定账号关联的所有代理IP"""
    try:
        db = await get_db()
        
        # 检查代理账号是否存在
        check_query = "SELECT COUNT(*) FROM proxy_accounts WHERE account_id = %s"
        result = await db.get_first(check_query, account_id)
        
        if not result or list(result.values())[0] == 0:
            raise HTTPException(status_code=404, detail="代理账号不存在")
        
        utils.logger.info(f"[手动清理] 开始清理账号 {account_id} 关联的代理IP")
        
        # 查询该账号关联的代理信息
        proxy_query = """
            SELECT proxy_id, ip, port, status, created_at 
            FROM proxy_pool 
            WHERE account_id = %s
        """
        proxies = await db.query(proxy_query, account_id)
        proxy_count = len(proxies)
        
        if proxy_count > 0:
            # 删除关联的代理IP
            delete_query = "DELETE FROM proxy_pool WHERE account_id = %s"
            await db.execute(delete_query, account_id)
            
            utils.logger.info(f"[手动清理] 已清除账号 {account_id} 关联的 {proxy_count} 个代理IP")
            
            # 记录清理日志
            log_query = """
                INSERT INTO proxy_account_logs (
                    account_id, provider, operation, success, response_time, error_message, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            await db.execute(log_query, account_id, "qingguo", "manual_cleanup", 1, None, 
                           f"手动清理关联的 {proxy_count} 个代理IP", datetime.now())
            
            return {
                "success": True,
                "message": f"成功清理 {proxy_count} 个关联代理IP",
                "cleaned_proxies": [
                    {
                        "proxy_id": proxy['proxy_id'],
                        "ip": proxy['ip'],
                        "port": proxy['port'],
                        "status": proxy['status'],
                        "created_at": proxy['created_at'].isoformat() if proxy['created_at'] else None
                    }
                    for proxy in proxies
                ],
                "count": proxy_count
            }
        else:
            utils.logger.info(f"[手动清理] 账号 {account_id} 没有关联的代理IP需要清理")
            
            return {
                "success": True,
                "message": "没有关联的代理IP需要清理",
                "cleaned_proxies": [],
                "count": 0
            }
        
    except HTTPException:
        raise
    except Exception as e:
        utils.logger.error(f"清理账号代理失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理账号代理失败: {str(e)}")

@proxy_router.get("/proxy-accounts/stats/overview")
async def get_proxy_account_stats():
    """获取代理账号统计概览"""
    try:
        db = await get_db()
        
        # 基础统计
        total_query = "SELECT COUNT(*) as total FROM proxy_accounts"
        total_result = await db.get_first(total_query)
        total_accounts = total_result['total'] if total_result else 0
        
        # 活跃账号统计
        active_query = "SELECT COUNT(*) as active FROM proxy_accounts WHERE is_active = 1"
        active_result = await db.get_first(active_query)
        active_accounts = active_result['active'] if active_result else 0
        
        # 提供商统计
        provider_query = """
            SELECT provider, COUNT(*) as count 
            FROM proxy_accounts 
            GROUP BY provider
        """
        provider_results = await db.query(provider_query)
        by_provider = {row['provider']: row['count'] for row in provider_results}
        
        # 成功率统计
        success_rate_query = """
            SELECT 
                SUM(success_count) as total_success,
                SUM(usage_count) as total_usage
            FROM proxy_accounts 
            WHERE usage_count > 0
        """
        success_rate_result = await db.get_first(success_rate_query)
        
        total_success = success_rate_result['total_success'] if success_rate_result and success_rate_result['total_success'] else 0
        total_usage = success_rate_result['total_usage'] if success_rate_result and success_rate_result['total_usage'] else 0
        
        avg_success_rate = round((total_success / total_usage * 100) if total_usage > 0 else 0, 2)
        
        return {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "by_provider": by_provider,
            "avg_success_rate": avg_success_rate,
            "total_usage": total_usage,
            "total_success": total_success
        }
        
    except Exception as e:
        utils.logger.error(f"获取代理账号统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取代理账号统计失败: {str(e)}")