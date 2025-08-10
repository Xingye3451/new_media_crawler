"""
青果长效代理（动态IP）实现
专门针对MediaCrawler项目的长效代理管理
"""

import os
import json
import time
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import httpx
from pydantic import BaseModel, Field

from tools import utils
from var import media_crawler_db_var


class ProxyStatus(str, Enum):
    """代理状态枚举"""
    ACTIVE = "active"           # 活跃
    EXPIRED = "expired"         # 已过期
    FAILED = "failed"           # 失败
    ROTATING = "rotating"       # 轮换中
    DISABLED = "disabled"       # 已禁用


@dataclass
class QingguoLongTermProxyConfig:
    """青果长效代理配置"""
    key: str
    pwd: str = ""
    bandwidth: str = "10Mbps"
    tunnel_forwarding: bool = True
    channel_count: int = 1
    duration: str = "1个月"  # 6小时, 1天, 1周, 1个月, 3个月, 半年, 1年
    region: str = "国内"
    auth_method: str = "whitelist"


class ProxyInfo(BaseModel):
    """代理信息模型"""
    id: Optional[str] = None
    ip: str
    port: int
    username: str
    password: str = ""
    proxy_type: str = "http"
    expire_ts: int
    created_at: datetime
    status: ProxyStatus = ProxyStatus.ACTIVE
    enabled: bool = True  # 是否启用
    usage_count: int = 0
    last_used_at: Optional[datetime] = None
    success_count: int = 0
    fail_count: int = 0
    area: Optional[str] = None  # 区域编码
    distinct: Optional[bool] = False  # 是否独享
    speed: Optional[int] = None  # 速度(ms)
    description: Optional[str] = None  # 描述信息


class QingguoLongTermProxy:
    """青果长效代理管理器"""
    
    def __init__(self, config: QingguoLongTermProxyConfig):
        self.config = config
        # 基础API和业务API使用不同的域名
        self.basic_api_base = "https://proxy.qg.net"  # 基础API（查询余额、通道等）
        self.business_api_base = "https://longterm.proxy.qg.net"  # 长效代理API
        self.db = None
        
    async def get_db(self):
        """获取数据库连接"""
        if not self.db:
            try:
                self.db = media_crawler_db_var.get()
            except LookupError:
                from db import init_mediacrawler_db
                await init_mediacrawler_db()
                self.db = media_crawler_db_var.get()
        return self.db
    
    async def extract_proxy(self, region: str = "北京", isp: str = "电信", description: str = None) -> Optional[ProxyInfo]:
        """提取长效代理IP"""
        try:
            # 首先检查通道空闲数
            channels = await self.get_channels()
            idle_count = channels.get("idle", 0)
            
            utils.logger.info(f"[QingguoLongTermProxy] 当前通道空闲数: {idle_count}")
            
            # 如果空闲数为0，需要先删除一些现有代理
            if idle_count == 0:
                utils.logger.warning(f"[QingguoLongTermProxy] 通道空闲数为0，需要先删除现有代理")
                await self._cleanup_old_proxies_for_extraction()
                
                # 重新检查空闲数
                channels = await self.get_channels()
                idle_count = channels.get("idle", 0)
                utils.logger.info(f"[QingguoLongTermProxy] 清理后通道空闲数: {idle_count}")
                
                if idle_count == 0:
                    utils.logger.error(f"[QingguoLongTermProxy] 清理后仍无空闲通道，无法提取代理")
                    return None
            
            # 检查区域可用性
            is_available = await self.is_region_available(region, isp)
            if not is_available:
                utils.logger.warning(f"[QingguoLongTermProxy] 区域 {region} 运营商 {isp} 不可用，尝试获取随机可用区域")
                region, isp = await self.get_random_available_region()
                utils.logger.info(f"[QingguoLongTermProxy] 使用随机区域: {region}, 运营商: {isp}")
            
            # 获取可用区域信息以获取正确的区域编码
            available_regions = await self.get_available_regions()
            area_code = None
            isp_code = None
            
            if region in available_regions:
                for isp_info in available_regions[region]:
                    if isp_info["isp"] == isp:
                        area_code = str(isp_info["area_code"])
                        isp_code = isp_info["isp_code"]
                        break
            
            # 如果找不到对应的编码，使用默认映射
            if not area_code or not isp_code:
                from proxy.qingguo_region_mapping import get_region_code, get_isp_code
                area_code = get_region_code(region)
                isp_code = get_isp_code(isp)
                utils.logger.warning(f"[QingguoLongTermProxy] 使用默认区域映射: {region} -> {area_code}, {isp} -> {isp_code}")
            
            # 构建API参数 - 长效代理需要key、pwd、区域、运营商等参数
            params = {
                "key": self.config.key,
                "pwd": self.config.pwd,
                "num": 1,  # 提取数量
                "area": area_code,  # 区域编码
                "isp": isp_code,  # 运营商编码
                "del_server": "*",  # 释放服务器参数
                "format": "json"
            }
            
            if self.config.pwd:
                params["Pwd"] = self.config.pwd
            
            # 调用青果代理API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.business_api_base}/get", params=params)
                
                if response.status_code != 200:
                    utils.logger.error(f"[QingguoLongTermProxy] API调用失败: {response.status_code}, {response.text}")
                    return None
                
                # 解析响应
                proxy_text = response.text.strip()
                if not proxy_text or proxy_text.startswith("error"):
                    utils.logger.error(f"[QingguoLongTermProxy] API返回错误: {proxy_text}")
                    return None
                
                # 解析长效代理响应格式
                try:
                    import json
                    response_data = json.loads(proxy_text)
                    
                    if response_data.get("code") != "SUCCESS":
                        utils.logger.error(f"[QingguoLongTermProxy] API返回错误: {response_data}")
                        return None
                    
                    proxy_list = response_data.get("data", [])
                    if not proxy_list:
                        utils.logger.error(f"[QingguoLongTermProxy] 没有可用的代理")
                        return None
                    
                    # 获取第一个代理
                    proxy_info_data = proxy_list[0]
                    server = proxy_info_data.get("server", "")
                    area = proxy_info_data.get("area", "")
                    distinct = proxy_info_data.get("distinct", False)
                    
                    if not server:
                        utils.logger.error(f"[QingguoLongTermProxy] 代理服务器信息为空")
                        return None
                    
                    # 解析服务器地址 (格式: host:port)
                    if ":" not in server:
                        utils.logger.error(f"[QingguoLongTermProxy] 代理服务器格式错误: {server}")
                        return None
                    
                    host, port = server.split(":", 1)
                    ip = host
                    port = int(port)
                    
                    # 长效代理的过期时间（默认24小时）
                    expire_ts = int(time.time()) + 24 * 3600
                    
                    # 记录提取的代理信息
                    utils.logger.info(f"[QingguoLongTermProxy] 提取代理成功: {ip}:{port}, 区域: {area}, 独享: {distinct}")
                    
                except (json.JSONDecodeError, ValueError) as e:
                    utils.logger.error(f"[QingguoLongTermProxy] 解析代理信息失败: {e}")
                    return None
                
                # 创建代理信息对象
                proxy_info = ProxyInfo(
                    ip=ip,
                    port=int(port),
                    username=self.config.key,
                    password=self.config.pwd,
                    expire_ts=int(expire_ts),
                    created_at=datetime.now(),
                    area=area,
                    distinct=distinct,
                    description=description or f"青果代理 - {region} {isp}"
                )
                
                # 保存到数据库
                await self.save_proxy_to_db(proxy_info)
                
                utils.logger.info(f"[QingguoLongTermProxy] 成功提取代理: {ip}:{port}")
                return proxy_info
                
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 提取代理失败: {e}")
            return None
    
    async def save_proxy_to_db(self, proxy_info: ProxyInfo):
        """保存代理信息到数据库"""
        try:
            db = await self.get_db()
            
            # 生成代理ID
            proxy_id = f"qingguo_{proxy_info.ip}_{proxy_info.port}_{int(time.time())}"
            
            # 检查是否已存在相同的代理
            check_query = """
                SELECT id FROM proxy_pool 
                WHERE ip = %s AND port = %s
            """
            existing = await db.get_first(check_query, proxy_info.ip, proxy_info.port)
            
            if existing:
                # 更新现有记录
                update_query = """
                    UPDATE proxy_pool SET 
                        expire_ts = %s, status = %s, updated_at = %s,
                        username = %s, password = %s, provider = %s
                    WHERE id = %s
                """
                await db.execute(update_query, 
                    proxy_info.expire_ts, proxy_info.status.value, 
                    datetime.now(), proxy_info.username, proxy_info.password,
                    'qingguo', existing['id']
                )
                proxy_info.id = existing['id']
            else:
                # 插入新记录
                insert_query = """
                    INSERT INTO proxy_pool (
                        proxy_id, ip, port, username, password, proxy_type, expire_ts,
                        provider, status, enabled, area, description, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                await db.execute(insert_query,
                    proxy_id, proxy_info.ip, proxy_info.port, proxy_info.username,
                    proxy_info.password, proxy_info.proxy_type, proxy_info.expire_ts,
                    'qingguo', proxy_info.status.value, proxy_info.enabled,
                    proxy_info.area, proxy_info.description,
                    proxy_info.created_at, datetime.now()
                )
                
                # 获取插入的ID
                result = await db.get_first("SELECT LAST_INSERT_ID() as id")
                proxy_info.id = str(result['id']) if result else None
            
            utils.logger.info(f"[QingguoLongTermProxy] 代理信息已保存到数据库: {proxy_info.ip}:{proxy_info.port}")
            
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 保存代理信息失败: {e}")
    
    async def get_available_proxy(self) -> Optional[ProxyInfo]:
        """获取可用的代理"""
        try:
            db = await self.get_db()
            
            # 首先尝试获取现有的有效代理
            query = """
                SELECT * FROM proxy_pool 
                WHERE status = %s AND enabled = 1 AND expire_ts > %s
                ORDER BY last_used_at ASC, created_at ASC
                LIMIT 1
            """
            
            current_ts = int(time.time())
            result = await db.get_first(query, ProxyStatus.ACTIVE.value, current_ts)
            
            if result:
                # 使用现有代理
                proxy_info = ProxyInfo(
                    id=str(result['id']),
                    ip=result['ip'],
                    port=result['port'],
                    username=result['username'],
                    password=result['password'] or "",
                    proxy_type=result['proxy_type'],
                    expire_ts=result['expire_ts'],
                    created_at=result['created_at'],
                    status=ProxyStatus(result['status']),
                    enabled=result.get('enabled', True),
                    usage_count=result.get('usage_count', 0),
                    last_used_at=result.get('last_used_at'),
                    success_count=result.get('success_count', 0),
                    fail_count=result.get('fail_count', 0),
                    area=result.get('area'),
                    speed=result.get('speed'),
                    description=result.get('description')
                )
                
                # 更新使用时间
                await self.update_proxy_usage(proxy_info.id)
                
                utils.logger.info(f"[QingguoLongTermProxy] 使用现有代理: {proxy_info.ip}:{proxy_info.port}")
                return proxy_info
            
            # 如果没有现有代理，提取新的代理
            utils.logger.info(f"[QingguoLongTermProxy] 提取新代理")
            return await self.extract_proxy()
            
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 获取代理失败: {e}")
            return None
    
    async def update_proxy_usage(self, proxy_id: str):
        """更新代理使用情况"""
        try:
            db = await self.get_db()
            
            update_query = """
                UPDATE proxy_pool SET 
                    usage_count = usage_count + 1,
                    last_used_at = %s,
                    updated_at = %s
                WHERE id = %s
            """
            
            await db.execute(update_query, datetime.now(), datetime.now(), proxy_id)
            
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 更新代理使用情况失败: {e}")
    
    async def mark_proxy_success(self, proxy_id: str):
        """标记代理使用成功"""
        try:
            db = await self.get_db()
            
            update_query = """
                UPDATE proxy_pool SET 
                    success_count = success_count + 1,
                    fail_count = 0,
                    updated_at = %s
                WHERE id = %s
            """
            
            await db.execute(update_query, datetime.now(), proxy_id)
            
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 标记代理成功失败: {e}")
    
    async def mark_proxy_failed(self, proxy_id: str, error_message: str = None):
        """标记代理使用失败"""
        try:
            db = await self.get_db()
            
            # 检查失败次数
            check_query = "SELECT fail_count FROM proxy_pool WHERE id = %s"
            result = await db.get_first(check_query, proxy_id)
            
            if result:
                fail_count = result['fail_count'] + 1
                
                # 如果失败次数过多，标记为失败状态
                status = ProxyStatus.FAILED.value if fail_count >= 3 else ProxyStatus.ACTIVE.value
                
                update_query = """
                    UPDATE proxy_pool SET 
                        fail_count = %s,
                        status = %s,
                        updated_at = %s
                    WHERE id = %s
                """
                
                await db.execute(update_query, fail_count, status, datetime.now(), proxy_id)
                
                # 记录失败日志
                log_query = """
                    INSERT INTO proxy_usage_log (proxy_id, success, error_message, add_ts)
                    VALUES (%s, 0, %s, %s)
                """
                await db.execute(log_query, proxy_id, error_message, int(time.time() * 1000))
                
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 标记代理失败: {e}")
    
    async def get_proxy_for_login(self) -> Optional[ProxyInfo]:
        """为登录获取代理"""
        return await self.get_available_proxy()
    
    async def get_proxy_for_crawling(self) -> Optional[ProxyInfo]:
        """为爬取获取代理"""
        return await self.get_available_proxy()
    
    def format_proxy_for_playwright(self, proxy_info: ProxyInfo) -> Dict[str, Any]:
        """格式化代理信息为Playwright格式"""
        if not proxy_info:
            return None
        
        proxy_config = {
            "server": f"{proxy_info.proxy_type}://{proxy_info.ip}:{proxy_info.port}"
        }
        
        if proxy_info.username:
            proxy_config["username"] = proxy_info.username
        
        if proxy_info.password:
            proxy_config["password"] = proxy_info.password
        
        # 打印正在使用的代理信息
        self.log_proxy_usage(proxy_info, "Playwright")
        utils.logger.info(f"[PROXY_USAGE] 📋 Playwright配置: {proxy_config}")
        
        return proxy_config
    
    def format_proxy_for_httpx(self, proxy_info: ProxyInfo) -> Dict[str, str]:
        """格式化代理信息为httpx格式"""
        if not proxy_info:
            return None
        
        proxy_url = f"{proxy_info.proxy_type}://"
        if proxy_info.username:
            proxy_url += f"{proxy_info.username}"
            if proxy_info.password:
                proxy_url += f":{proxy_info.password}"
            proxy_url += "@"
        
        proxy_url += f"{proxy_info.ip}:{proxy_info.port}"
        
        proxy_config = {
            "http://": proxy_url,
            "https://": proxy_url
        }
        
        # 打印正在使用的代理信息
        self.log_proxy_usage(proxy_info, "httpx")
        utils.logger.info(f"[PROXY_USAGE] 📋 httpx配置: {proxy_config}")
        
        return proxy_config
    
    def log_proxy_usage(self, proxy_info: ProxyInfo, usage_type: str = "general"):
        """记录代理使用日志"""
        if not proxy_info:
            return
        
        utils.logger.info(f"[PROXY_USAGE] 🚀 使用{usage_type}代理: {proxy_info.ip}:{proxy_info.port}")
        utils.logger.info(f"[PROXY_USAGE] 📋 代理类型: {proxy_info.proxy_type}")
        utils.logger.info(f"[PROXY_USAGE] 🔑 认证信息: {proxy_info.username}:{proxy_info.password}")
        utils.logger.info(f"[PROXY_USAGE] ⏰ 过期时间: {proxy_info.expire_ts}")
        utils.logger.info(f"[PROXY_USAGE] 📊 使用统计: 成功{proxy_info.success_count}次, 失败{proxy_info.fail_count}次")
        
        # 添加区域和独享信息
        if proxy_info.area:
            utils.logger.info(f"[PROXY_USAGE] 🌍 区域编码: {proxy_info.area}")
        if proxy_info.distinct is not None:
            utils.logger.info(f"[PROXY_USAGE] 🔒 独享代理: {proxy_info.distinct}")
        
        # 打印curl使用示例
        curl_example = f"curl -x http://{proxy_info.username}:{proxy_info.password}@{proxy_info.ip}:{proxy_info.port} https://httpbin.org/ip"
        utils.logger.info(f"[PROXY_USAGE] 💡 curl使用示例: {curl_example}")
    
    async def cleanup_expired_proxies(self):
        """清理过期的代理"""
        try:
            db = await self.get_db()
            
            current_ts = int(time.time())
            update_query = """
                UPDATE proxy_pool SET 
                    status = %s,
                    updated_at = %s
                WHERE expire_ts <= %s AND status = %s
            """
            
            await db.execute(update_query, 
                ProxyStatus.EXPIRED.value, datetime.now(), 
                current_ts, ProxyStatus.ACTIVE.value
            )
            
            utils.logger.info("[QingguoLongTermProxy] 过期代理清理完成")
            
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 清理过期代理失败: {e}")

    async def _cleanup_old_proxies_for_extraction(self, max_delete_count: int = 5):
        """为提取新代理而清理旧代理"""
        try:
            db = await self.get_db()
            
            # 查找最旧的代理（按最后使用时间排序，优先删除未使用的）
            old_proxies_query = """
                SELECT * FROM proxy_pool 
                WHERE status = %s AND enabled = 1 AND provider = 'qingguo'
                ORDER BY 
                    CASE WHEN last_used_at IS NULL THEN 0 ELSE 1 END,  -- 未使用的优先
                    last_used_at ASC,  -- 最后使用时间最早的优先
                    created_at ASC     -- 创建时间最早的优先
                LIMIT %s
            """
            old_proxies = await db.query(old_proxies_query, ProxyStatus.ACTIVE.value, max_delete_count)
            
            if not old_proxies:
                utils.logger.warning(f"[QingguoLongTermProxy] 没有找到可以清理的旧代理")
                return
            
            utils.logger.info(f"[QingguoLongTermProxy] 找到 {len(old_proxies)} 个旧代理，开始清理以释放通道")
            
            deleted_count = 0
            for proxy in old_proxies:
                try:
                    # 标记为已过期（释放通道）
                    await db.execute(
                        "UPDATE proxy_pool SET status = %s WHERE id = %s",
                        ProxyStatus.EXPIRED.value, proxy['id']
                    )
                    deleted_count += 1
                    utils.logger.info(f"[QingguoLongTermProxy] 清理旧代理: {proxy['ip']}:{proxy['port']} (使用{proxy.get('usage_count', 0)}次)")
                except Exception as e:
                    utils.logger.error(f"[QingguoLongTermProxy] 清理旧代理失败: {proxy['ip']}:{proxy['port']} - {e}")
            
            utils.logger.info(f"[QingguoLongTermProxy] 旧代理清理完成，共处理 {deleted_count} 个")
            
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 清理旧代理异常: {e}")

    async def enable_proxy(self, proxy_id: str) -> bool:
        """启用代理"""
        try:
            db = await self.get_db()
            
            update_query = """
                UPDATE proxy_pool SET 
                    enabled = 1,
                    updated_at = %s
                WHERE id = %s
            """
            
            await db.execute(update_query, datetime.now(), proxy_id)
            utils.logger.info(f"[QingguoLongTermProxy] 代理启用成功: {proxy_id}")
            return True
            
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 启用代理失败: {e}")
            return False

    async def disable_proxy(self, proxy_id: str) -> bool:
        """禁用代理"""
        try:
            db = await self.get_db()
            
            update_query = """
                UPDATE proxy_pool SET 
                    enabled = 0,
                    updated_at = %s
                WHERE id = %s
            """
            
            await db.execute(update_query, datetime.now(), proxy_id)
            utils.logger.info(f"[QingguoLongTermProxy] 代理禁用成功: {proxy_id}")
            return True
            
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 禁用代理失败: {e}")
            return False

    async def test_proxy_speed(self, proxy_id: str) -> dict:
        """测试代理速度"""
        try:
            db = await self.get_db()
            
            # 获取代理信息
            query = "SELECT * FROM proxy_pool WHERE id = %s"
            proxy = await db.get_first(query, proxy_id)
            
            if not proxy:
                return {"success": False, "error": "代理不存在"}
            
            # 测试代理连接
            import httpx
            proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}"
            
            start_time = time.time()
            async with httpx.AsyncClient(
                proxies={"http://": proxy_url, "https://": proxy_url},
                timeout=10.0
            ) as client:
                response = await client.get("http://httpbin.org/ip")
                end_time = time.time()
                
                if response.status_code == 200:
                    speed = int((end_time - start_time) * 1000)  # 转换为毫秒
                    
                    # 更新代理速度
                    update_query = """
                        UPDATE proxy_pool SET 
                            speed = %s,
                            updated_at = %s
                        WHERE id = %s
                    """
                    await db.execute(update_query, speed, datetime.now(), proxy_id)
                    
                    return {
                        "success": True,
                        "speed": speed,
                        "ip": proxy['ip'],
                        "port": proxy['port']
                    }
                else:
                    return {"success": False, "error": f"HTTP错误: {response.status_code}"}
                    
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 测试代理速度失败: {e}")
            return {"success": False, "error": str(e)}

    async def get_balance(self) -> dict:
        """查询账户余额（需要登录token，暂时返回默认值）"""
        utils.logger.warning("[QingguoLongTermProxy] 余额查询需要登录token，暂时返回默认值")
        return {
            "balance": 0.0,
            "currency": "CNY",
            "message": "余额查询需要登录token，请使用平台登录后查询"
        }

    async def get_channels(self) -> dict:
        """查询通道数"""
        try:
            params = {
                "key": self.config.key,
                "format": "json"
            }
            
            if self.config.pwd:
                params["pwd"] = self.config.pwd
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.business_api_base}/channels", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == "SUCCESS":
                        # 根据API返回的数据结构
                        channels_data = data.get("data", {})
                        total = channels_data.get("total", 0)
                        idle = channels_data.get("idle", 0)
                        
                        utils.logger.info(f"[QingguoLongTermProxy] 通道查询成功: 总数={total}, 空闲={idle}")
                        return {
                            "total": total,
                            "idle": idle,
                            "in_use": total - idle
                        }
                    else:
                        utils.logger.error(f"[QingguoLongTermProxy] 查询通道数失败: {data}")
                        return {"total": 0, "idle": 0, "in_use": 0}
                else:
                    utils.logger.error(f"[QingguoLongTermProxy] 查询通道数HTTP错误: {response.status_code}")
                    return {"total": 0, "idle": 0, "in_use": 0}
                    
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 查询通道数异常: {e}")
            return {"total": 0, "idle": 0, "in_use": 0}

    async def get_resources(self) -> List[Dict[str, Any]]:
        """查询可用资源地区"""
        try:
            params = {
                "key": self.config.key,
                "format": "json"
            }
            
            if self.config.pwd:
                params["pwd"] = self.config.pwd
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.business_api_base}/resources", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == "SUCCESS":
                        # 根据API返回的数据结构，data字段包含资源信息
                        resources = data.get("data", [])
                        utils.logger.info(f"[QingguoLongTermProxy] 查询到 {len(resources)} 个可用资源")
                        return resources
                    else:
                        utils.logger.error(f"[QingguoLongTermProxy] 查询资源地区失败: {data}")
                        return []
                else:
                    utils.logger.error(f"[QingguoLongTermProxy] 查询资源地区HTTP错误: {response.status_code}")
                    return []
                    
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 查询资源地区异常: {e}")
            return []

    async def get_available_regions(self) -> Dict[str, List[str]]:
        """获取可用的区域和运营商组合"""
        try:
            resources = await self.get_resources()
            available_regions = {}
            
            for resource in resources:
                area = resource.get("area", "")
                isp = resource.get("isp", "")
                area_code = resource.get("area_code", "")
                isp_code = resource.get("isp_code", "")
                available = resource.get("available", False)
                
                if available and area and isp:
                    if area not in available_regions:
                        available_regions[area] = []
                    available_regions[area].append({
                        "isp": isp,
                        "isp_code": isp_code,
                        "area_code": area_code
                    })
            
            utils.logger.info(f"[QingguoLongTermProxy] 可用区域数量: {len(available_regions)}")
            return available_regions
            
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 获取可用区域失败: {e}")
            return {}

    async def is_region_available(self, region: str, isp: str) -> bool:
        """检查指定区域和运营商是否可用"""
        try:
            available_regions = await self.get_available_regions()
            
            if region in available_regions:
                for isp_info in available_regions[region]:
                    if isp_info["isp"] == isp:
                        return True
            
            return False
            
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 检查区域可用性失败: {e}")
            return False

    async def get_random_available_region(self) -> tuple:
        """获取一个随机的可用区域和运营商组合"""
        try:
            available_regions = await self.get_available_regions()
            
            if not available_regions:
                utils.logger.warning("[QingguoLongTermProxy] 没有可用的区域，使用默认值")
                return "北京", "电信"
            
            import random
            region = random.choice(list(available_regions.keys()))
            isp_info = random.choice(available_regions[region])
            
            utils.logger.info(f"[QingguoLongTermProxy] 随机选择区域: {region}, 运营商: {isp_info['isp']}")
            return region, isp_info["isp"]
            
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 获取随机可用区域失败: {e}")
            return "北京", "电信"

    async def get_in_use_proxies(self) -> List[ProxyInfo]:
        """查询在用代理"""
        try:
            db = await self.get_db()
            
            query = """
                SELECT * FROM proxy_pool 
                WHERE provider = 'qingguo' AND status = 'active' AND enabled = 1
                ORDER BY last_used_at DESC
            """
            
            results = await db.query(query)
            
            proxies = []
            for row in results:
                proxy = ProxyInfo(
                    id=str(row.get('id')),  # 确保id是字符串类型
                    ip=row['ip'],
                    port=row['port'],
                    username=row.get('username', ''),
                    password=row.get('password', ''),
                    proxy_type=row['proxy_type'],
                    expire_ts=row.get('expire_ts', 0),
                    created_at=row['created_at'],
                    status=ProxyStatus(row.get('status', 'active')),
                    enabled=row.get('enabled', True),
                    usage_count=row.get('usage_count', 0),
                    success_count=row.get('success_count', 0),
                    fail_count=row.get('fail_count', 0),
                    last_used_at=row.get('last_used_at'),
                    area=row.get('area'),
                    speed=row.get('speed'),
                    description=row.get('description')
                )
                proxies.append(proxy)
            
            return proxies
            
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 查询在用代理失败: {e}")
            return []

    async def release_proxy(self, proxy_id: str) -> bool:
        """释放代理"""
        try:
            db = await self.get_db()
            
            # 获取代理信息
            query = "SELECT * FROM proxy_pool WHERE proxy_id = %s"
            proxy = await db.get_first(query, proxy_id)
            
            if not proxy:
                utils.logger.warning(f"[QingguoLongTermProxy] 代理不存在: {proxy_id}")
                return False
            
            # 调用青果API释放代理
            params = {
                "Key": self.config.key,
                "format": "json",
                "ip": proxy['ip'],
                "port": proxy['port']
            }
            
            if self.config.pwd:
                params["Pwd"] = self.config.pwd
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(f"{self.business_api_base}/delete", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 200:
                        # 更新数据库状态
                        update_query = """
                            UPDATE proxy_pool SET 
                                status = %s, updated_at = %s
                            WHERE proxy_id = %s
                        """
                        await db.execute(update_query, ProxyStatus.EXPIRED.value, datetime.now(), proxy_id)
                        
                        utils.logger.info(f"[QingguoLongTermProxy] 代理释放成功: {proxy_id}")
                        return True
                    else:
                        utils.logger.error(f"[QingguoLongTermProxy] 释放代理失败: {data}")
                        return False
                else:
                    utils.logger.error(f"[QingguoLongTermProxy] 释放代理HTTP错误: {response.status_code}")
                    return False
                    
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 释放代理异常: {e}")
            return False

    async def get_whitelist(self) -> List[str]:
        """查询IP白名单"""
        try:
            params = {
                "Key": self.config.key,
                "format": "json"
            }
            
            if self.config.pwd:
                params["Pwd"] = self.config.pwd
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.basic_api_base}/whitelist/query", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("Code") == 0:
                        # 根据测试结果，Data字段包含白名单信息
                        return data.get("Data", []) if data.get("Data") else []
                    else:
                        utils.logger.error(f"[QingguoLongTermProxy] 查询白名单失败: {data}")
                        return []
                else:
                    utils.logger.error(f"[QingguoLongTermProxy] 查询白名单HTTP错误: {response.status_code}")
                    return []
                    
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 查询白名单异常: {e}")
            return []

    async def add_whitelist(self, ip: str) -> bool:
        """添加IP白名单"""
        try:
            params = {
                "Key": self.config.key,
                "format": "json",
                "ip": ip
            }
            
            if self.config.pwd:
                params["Pwd"] = self.config.pwd
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{self.basic_api_base}/whitelist/add", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("Code") == 0:
                        utils.logger.info(f"[QingguoLongTermProxy] 添加白名单成功: {ip}")
                        return True
                    else:
                        utils.logger.error(f"[QingguoLongTermProxy] 添加白名单失败: {data}")
                        return False
                else:
                    utils.logger.error(f"[QingguoLongTermProxy] 添加白名单HTTP错误: {response.status_code}")
                    return False
                    
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 添加白名单异常: {e}")
            return False

    async def remove_whitelist(self, ip: str) -> bool:
        """删除IP白名单"""
        try:
            params = {
                "Key": self.config.key,
                "format": "json",
                "ip": ip
            }
            
            if self.config.pwd:
                params["Pwd"] = self.config.pwd
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(f"{self.basic_api_base}/whitelist/del", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("Code") == 0:
                        utils.logger.info(f"[QingguoLongTermProxy] 删除白名单成功: {ip}")
                        return True
                    else:
                        utils.logger.error(f"[QingguoLongTermProxy] 删除白名单失败: {data}")
                        return False
                else:
                    utils.logger.error(f"[QingguoLongTermProxy] 删除白名单HTTP错误: {response.status_code}")
                    return False
                    
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 删除白名单异常: {e}")
            return False

    async def sync_proxies_from_query(self):
        """从query API同步代理信息到数据库"""
        try:
            # 调用query API获取当前代理
            params = {
                "key": self.config.key,
                "format": "json"
            }
            
            if self.config.pwd:
                params["pwd"] = self.config.pwd
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.business_api_base}/query", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == "SUCCESS":
                        proxy_list = data.get("data", [])
                        
                        if not proxy_list:
                            utils.logger.info(f"[QingguoLongTermProxy] query API返回空代理列表")
                            return []
                        
                        utils.logger.info(f"[QingguoLongTermProxy] query API返回 {len(proxy_list)} 个代理")
                        
                        # 同步到数据库
                        synced_proxies = []
                        for proxy_data in proxy_list:
                            proxy_info = await self._sync_proxy_to_db(proxy_data)
                            if proxy_info:
                                synced_proxies.append(proxy_info)
                        
                        utils.logger.info(f"[QingguoLongTermProxy] 成功同步 {len(synced_proxies)} 个代理到数据库")
                        return synced_proxies
                    else:
                        utils.logger.error(f"[QingguoLongTermProxy] query API返回错误: {data}")
                        return []
                else:
                    utils.logger.error(f"[QingguoLongTermProxy] query API HTTP错误: {response.status_code}")
                    return []
                    
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 同步代理信息异常: {e}")
            return []

    async def _sync_proxy_to_db(self, proxy_data: dict) -> Optional[ProxyInfo]:
        """将单个代理信息同步到数据库"""
        try:
            server = proxy_data.get("server", "")
            area = proxy_data.get("area", "")
            distinct = proxy_data.get("distinct", False)
            
            if not server or ":" not in server:
                utils.logger.error(f"[QingguoLongTermProxy] 代理服务器格式错误: {server}")
                return None
            
            # 解析服务器地址
            host, port = server.split(":", 1)
            ip = host
            port = int(port)
            
            # 生成代理ID
            proxy_id = f"qingguo_{ip}_{port}_{int(time.time())}"
            
            # 长效代理的过期时间（默认24小时）
            expire_ts = int(time.time()) + 24 * 3600
            
            # 创建代理信息对象
            proxy_info = ProxyInfo(
                ip=ip,
                port=port,
                username=self.config.key,  # 使用key作为用户名
                password=self.config.pwd or "",  # 使用pwd作为密码
                proxy_type="http",
                expire_ts=expire_ts,
                created_at=datetime.now(),
                status=ProxyStatus.ACTIVE,
                enabled=True,
                area=area,
                distinct=distinct,
                description=f"青果长效代理 - {area}"
            )
            
            # 保存到数据库
            await self.save_proxy_to_db(proxy_info)
            
            utils.logger.info(f"[QingguoLongTermProxy] 同步代理成功: {ip}:{port}")
            return proxy_info
            
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 同步单个代理失败: {e}")
            return None

    async def delete_proxy_from_api(self, ip: str) -> bool:
        """通过青果API删除代理"""
        try:
            # 调用青果API删除代理
            params = {
                "key": self.config.key,
                "pwd": self.config.pwd,
                "ip": ip
            }
            
            # 构建URL
            url = f"{self.business_api_base}/delete"
            
            utils.logger.info(f"[QingguoLongTermProxy] 调用青果删除API: {url} 参数: {params}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                
                utils.logger.info(f"[QingguoLongTermProxy] 青果删除API响应: {response.status_code} - {response.text}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get("code") == "SUCCESS":
                            utils.logger.info(f"[QingguoLongTermProxy] 青果API删除代理成功: {ip}")
                            return True
                        else:
                            utils.logger.error(f"[QingguoLongTermProxy] 青果API删除代理失败: {data}")
                            return False
                    except Exception as json_error:
                        utils.logger.error(f"[QingguoLongTermProxy] 解析青果删除API响应失败: {json_error}")
                        # 如果响应不是JSON格式，检查是否包含成功信息
                        if "success" in response.text.lower() or "成功" in response.text:
                            utils.logger.info(f"[QingguoLongTermProxy] 青果API删除代理成功: {ip}")
                            return True
                        return False
                else:
                    utils.logger.error(f"[QingguoLongTermProxy] 青果API删除代理HTTP错误: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            utils.logger.error(f"[QingguoLongTermProxy] 青果API删除代理异常: {e}")
            return False


# 全局代理管理器实例
_qingguo_proxy_manager = None

async def get_qingguo_proxy_manager() -> QingguoLongTermProxy:
    """获取青果代理管理器实例"""
    global _qingguo_proxy_manager
    
    if not _qingguo_proxy_manager:
        # 从配置加载
        from config.config_manager import config_manager
        proxy_config = config_manager.get_proxy_config()
        
        config = QingguoLongTermProxyConfig(
            key=proxy_config.qingguo_key or os.getenv("QG_PROXY_KEY", ""),
            pwd=proxy_config.qingguo_pwd or os.getenv("QG_PROXY_PWD", ""),
            bandwidth="10Mbps",
            tunnel_forwarding=True,
            channel_count=1,
            duration="1个月",
            region="国内",
            auth_method="whitelist"
        )
        
        _qingguo_proxy_manager = QingguoLongTermProxy(config)
    
    return _qingguo_proxy_manager
