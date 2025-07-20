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
import random
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import aiohttp
import aiomysql
from async_db import AsyncMysqlDB
from var import media_crawler_db_var


class ProxyType(Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class AnonymityLevel(Enum):
    TRANSPARENT = "transparent"
    ANONYMOUS = "anonymous"
    ELITE = "elite"


@dataclass
class ProxyInfo:
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

    @property
    def proxy_url(self) -> str:
        """生成代理URL"""
        if self.username and self.password:
            return f"{self.proxy_type}://{self.username}:{self.password}@{self.ip}:{self.port}"
        return f"{self.proxy_type}://{self.ip}:{self.port}"

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_requests == 0:
            return 0.0
        return round(self.total_success / self.total_requests * 100, 2)


class ProxyStrategy(ABC):
    """代理策略抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db: Optional[AsyncMysqlDB] = None
    
    def _ensure_db_connection(self):
        """确保数据库连接可用"""
        if not self.db:
            try:
                self.db = media_crawler_db_var.get()
            except Exception as e:
                raise RuntimeError(f"无法获取数据库连接: {e}")
    
    @abstractmethod
    async def select_proxy(self, platform: str = None, **kwargs) -> Optional[ProxyInfo]:
        """选择代理"""
        pass
    
    async def mark_proxy_success(self, proxy_id: int):
        """标记代理成功"""
        self._ensure_db_connection()
        await self.db.execute(
            "UPDATE proxy_pool SET success_count = success_count + 1, "
            "total_requests = total_requests + 1, total_success = total_success + 1, "
            "fail_count = 0, last_modify_ts = %s WHERE id = %s",
            (int(time.time() * 1000), proxy_id)
        )
    
    async def mark_proxy_failed(self, proxy_id: int, error_message: str = None):
        """标记代理失败"""
        self._ensure_db_connection()
        await self.db.execute(
            "UPDATE proxy_pool SET fail_count = fail_count + 1, "
            "total_requests = total_requests + 1, last_check_result = 0, "
            "last_modify_ts = %s WHERE id = %s",
            (int(time.time() * 1000), proxy_id)
        )
        
        # 记录失败日志
        await self.db.execute(
            "INSERT INTO proxy_usage_log (proxy_id, success, error_message, add_ts) "
            "VALUES (%s, 0, %s, %s)",
            (proxy_id, error_message, int(time.time() * 1000))
        )


class RoundRobinStrategy(ProxyStrategy):
    """轮询策略"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.current_index = 0
        self.proxy_cache: List[ProxyInfo] = []
        self.last_refresh = 0
    
    async def select_proxy(self, platform: str = None, **kwargs) -> Optional[ProxyInfo]:
        """轮询选择代理"""
        # 每5分钟刷新一次代理列表
        if time.time() - self.last_refresh > 300:
            await self._refresh_proxy_list()
        
        if not self.proxy_cache:
            return None
        
        # 轮询选择
        proxy = self.proxy_cache[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxy_cache)
        
        return proxy
    
    async def _refresh_proxy_list(self):
        """刷新代理列表"""
        self._ensure_db_connection()
        rows = await self.db.query(
            "SELECT * FROM proxy_pool WHERE status = 1 AND last_check_result = 1 "
            "ORDER BY priority DESC, speed ASC"
        )
        
        self.proxy_cache = [ProxyInfo(**row) for row in rows]
        self.last_refresh = time.time()


class RandomStrategy(ProxyStrategy):
    """随机策略"""
    
    async def select_proxy(self, platform: str = None, **kwargs) -> Optional[ProxyInfo]:
        """随机选择代理"""
        self._ensure_db_connection()
        rows = await self.db.query(
            "SELECT * FROM proxy_pool WHERE status = 1 AND last_check_result = 1 "
            "ORDER BY RAND() LIMIT 1"
        )
        
        if not rows:
            return None
        
        return ProxyInfo(**rows[0])


class WeightedStrategy(ProxyStrategy):
    """权重策略"""
    
    async def select_proxy(self, platform: str = None, **kwargs) -> Optional[ProxyInfo]:
        """根据权重选择代理"""
        self._ensure_db_connection()
        weight_field = self.config.get("weight_field", "priority")
        
        rows = await self.db.query(
            f"SELECT * FROM proxy_pool WHERE status = 1 AND last_check_result = 1 "
            f"ORDER BY {weight_field} DESC, success_count DESC LIMIT 10"
        )
        
        if not rows:
            return None
        
        # 根据权重随机选择
        proxies = [ProxyInfo(**row) for row in rows]
        weights = [getattr(proxy, weight_field, 0) for proxy in proxies]
        
        return random.choices(proxies, weights=weights, k=1)[0]


class FailoverStrategy(ProxyStrategy):
    """故障转移策略"""
    
    async def select_proxy(self, platform: str = None, **kwargs) -> Optional[ProxyInfo]:
        """故障转移选择代理"""
        self._ensure_db_connection()
        priority_order = self.config.get("priority_order", ["elite", "anonymous", "transparent"])
        
        for anonymity in priority_order:
            rows = await self.db.query(
                "SELECT * FROM proxy_pool WHERE status = 1 AND last_check_result = 1 "
                "AND anonymity = %s ORDER BY speed ASC, success_count DESC LIMIT 1",
                anonymity
            )
            
            if rows:
                return ProxyInfo(**rows[0])
        
        # 如果没有找到，返回任意可用代理
        rows = await self.db.query(
            "SELECT * FROM proxy_pool WHERE status = 1 AND last_check_result = 1 "
            "ORDER BY speed ASC LIMIT 1"
        )
        
        if rows:
            return ProxyInfo(**rows[0])
        
        return None


class GeoBasedStrategy(ProxyStrategy):
    """地理位置策略"""
    
    async def select_proxy(self, platform: str = None, **kwargs) -> Optional[ProxyInfo]:
        """根据地理位置选择代理"""
        self._ensure_db_connection()
        geo_mapping = self.config.get("geo_mapping", {})
        target_countries = geo_mapping.get(platform, ["CN"])
        
        # 构建国家查询条件
        country_conditions = " OR ".join([f"country = '{country}'" for country in target_countries])
        
        rows = await self.db.query(
            f"SELECT * FROM proxy_pool WHERE status = 1 AND last_check_result = 1 "
            f"AND ({country_conditions}) ORDER BY speed ASC, success_count DESC LIMIT 1"
        )
        
        if rows:
            return ProxyInfo(**rows[0])
        
        # 如果没有找到指定国家的代理，返回任意可用代理
        rows = await self.db.query(
            "SELECT * FROM proxy_pool WHERE status = 1 AND last_check_result = 1 "
            "ORDER BY speed ASC LIMIT 1"
        )
        
        if rows:
            return ProxyInfo(**rows[0])
        
        return None


class SmartStrategy(ProxyStrategy):
    """智能策略"""
    
    async def select_proxy(self, platform: str = None, **kwargs) -> Optional[ProxyInfo]:
        """智能选择代理"""
        self._ensure_db_connection()
        factors = self.config.get("factors", ["speed", "uptime", "fail_count"])
        weights = self.config.get("weights", [0.4, 0.4, 0.2])
        
        # 获取候选代理
        rows = await self.db.query(
            "SELECT * FROM proxy_pool WHERE status = 1 AND last_check_result = 1 "
            "ORDER BY speed ASC, success_count DESC LIMIT 20"
        )
        
        if not rows:
            return None
        
        proxies = [ProxyInfo(**row) for row in rows]
        
        # 计算综合评分
        scored_proxies = []
        for proxy in proxies:
            score = 0
            for factor, weight in zip(factors, weights):
                if factor == "speed":
                    # 速度越快分数越高
                    speed_score = max(0, 100 - (proxy.speed or 1000) / 10)
                    score += speed_score * weight
                elif factor == "uptime":
                    # 在线率越高分数越高
                    uptime_score = proxy.uptime or 0
                    score += uptime_score * weight
                elif factor == "fail_count":
                    # 失败次数越少分数越高
                    fail_score = max(0, 100 - (proxy.fail_count * 20))
                    score += fail_score * weight
            
            scored_proxies.append((proxy, score))
        
        # 按评分排序并随机选择前3个中的一个
        scored_proxies.sort(key=lambda x: x[1], reverse=True)
        top_proxies = scored_proxies[:3]
        
        if not top_proxies:
            return None
        
        return random.choice(top_proxies)[0]


class ProxyManager:
    """代理管理器"""
    
    def __init__(self):
        self.db: Optional[AsyncMysqlDB] = None
        self.strategies: Dict[str, ProxyStrategy] = {}
        self._initialized = False
    
    def _ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            try:
                self.db = media_crawler_db_var.get()
                self._load_strategies()
                self._initialized = True
            except Exception as e:
                # 如果无法获取数据库连接，使用默认配置
                self.db = None
                self._load_strategies()
                self._initialized = True
                # 记录警告但不抛出异常
                import logging
                logging.warning(f"代理管理器初始化时无法获取数据库连接: {e}")
                # 记录到tools.utils.logger
                try:
                    from tools import utils
                    utils.logger.warning(f"代理管理器初始化时无法获取数据库连接: {e}")
                except ImportError:
                    pass
    
    def _load_strategies(self):
        """加载策略"""
        strategy_classes = {
            "round_robin": RoundRobinStrategy,
            "random": RandomStrategy,
            "weighted": WeightedStrategy,
            "failover": FailoverStrategy,
            "geo_based": GeoBasedStrategy,
            "smart": SmartStrategy
        }
        
        # 这里可以从数据库加载策略配置
        # 暂时使用默认配置
        default_configs = {
            "round_robin": {"max_fail_count": 3, "retry_interval": 300},
            "random": {"max_fail_count": 3, "retry_interval": 300},
            "weighted": {"weight_field": "priority", "max_fail_count": 3},
            "failover": {"priority_order": ["elite", "anonymous", "transparent"], "max_fail_count": 2},
            "geo_based": {"geo_mapping": {"xhs": ["CN"], "dy": ["CN"], "ks": ["CN"]}},
            "smart": {"factors": ["speed", "uptime", "fail_count"], "weights": [0.4, 0.4, 0.2]}
        }
        
        for strategy_type, strategy_class in strategy_classes.items():
            config = default_configs.get(strategy_type, {})
            self.strategies[strategy_type] = strategy_class(config)
    
    async def get_proxy(self, strategy_type: str = "round_robin", platform: str = None, **kwargs) -> Optional[ProxyInfo]:
        """获取代理"""
        self._ensure_initialized()
        strategy = self.strategies.get(strategy_type)
        if not strategy:
            raise ValueError(f"不支持的策略类型: {strategy_type}")
        
        try:
            return await strategy.select_proxy(platform, **kwargs)
        except Exception as e:
            # 如果获取代理失败，返回None而不是抛出异常
            import logging
            logging.warning(f"获取代理失败: {e}")
            # 记录到tools.utils.logger
            try:
                from tools import utils
                utils.logger.warning(f"获取代理失败: {e}")
            except ImportError:
                pass
            return None
    
    async def add_proxy(self, proxy_info: Dict[str, Any]) -> int:
        """添加代理"""
        self._ensure_initialized()
        
        if not self.db:
            raise RuntimeError("数据库连接不可用")
        
        proxy_info["add_ts"] = int(time.time() * 1000)
        proxy_info["last_modify_ts"] = int(time.time() * 1000)
        
        try:
            result = await self.db.execute(
                "INSERT INTO proxy_pool (proxy_type, ip, port, username, password, country, "
                "region, city, isp, speed, anonymity, uptime, priority, tags, description, "
                "add_ts, last_modify_ts) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (proxy_info["proxy_type"], proxy_info["ip"], proxy_info["port"], 
                 proxy_info.get("username"), proxy_info.get("password"), proxy_info.get("country"),
                 proxy_info.get("region"), proxy_info.get("city"), proxy_info.get("isp"),
                 proxy_info.get("speed"), proxy_info.get("anonymity"), proxy_info.get("uptime"),
                 proxy_info.get("priority", 0), proxy_info.get("tags"), proxy_info.get("description"),
                 proxy_info["add_ts"], proxy_info["last_modify_ts"])
            )
            
            return result
        except Exception as e:
            import logging
            logging.error(f"添加代理失败: {e}")
            # 记录到tools.utils.logger
            try:
                from tools import utils
                utils.logger.error(f"添加代理失败: {e}")
            except ImportError:
                pass
            raise RuntimeError(f"添加代理失败: {e}")
    
    async def update_proxy(self, proxy_id: int, update_data: Dict[str, Any]) -> bool:
        """更新代理"""
        self._ensure_initialized()
        
        if not self.db:
            raise RuntimeError("数据库连接不可用")
        
        update_data["last_modify_ts"] = int(time.time() * 1000)
        
        try:
            set_clause = ", ".join([f"{k} = %s" for k in update_data.keys()])
            values = list(update_data.values()) + [proxy_id]
            
            result = await self.db.execute(
                f"UPDATE proxy_pool SET {set_clause} WHERE id = %s",
                values
            )
            
            return result > 0
        except Exception as e:
            import logging
            logging.error(f"更新代理失败: {e}")
            # 记录到tools.utils.logger
            try:
                from tools import utils
                utils.logger.error(f"更新代理失败: {e}")
            except ImportError:
                pass
            raise RuntimeError(f"更新代理失败: {e}")
    
    async def delete_proxy(self, proxy_id: int) -> bool:
        """删除代理"""
        self._ensure_initialized()
        
        if not self.db:
            raise RuntimeError("数据库连接不可用")
        
        try:
            result = await self.db.execute("DELETE FROM proxy_pool WHERE id = %s", (proxy_id,))
            return result > 0
        except Exception as e:
            import logging
            logging.error(f"删除代理失败: {e}")
            # 记录到tools.utils.logger
            try:
                from tools import utils
                utils.logger.error(f"删除代理失败: {e}")
            except ImportError:
                pass
            raise RuntimeError(f"删除代理失败: {e}")
    
    async def check_proxy(self, proxy_info: ProxyInfo) -> bool:
        """检测代理可用性"""
        self._ensure_initialized()
        try:
            proxy_url = proxy_info.proxy_url
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    "http://httpbin.org/ip",
                    proxy=proxy_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # 记录检测日志
                        if self.db:
                            try:
                                await self.db.execute(
                                    "INSERT INTO proxy_check_log (proxy_id, check_type, check_url, "
                                    "response_time, success, check_result, add_ts) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                    (proxy_info.id, "health", "http://httpbin.org/ip", 
                                     int(response.headers.get("X-Response-Time", 0)), 1, 
                                     json.dumps(data), int(time.time() * 1000))
                                )
                            except Exception as log_error:
                                # 记录日志失败不影响代理检测结果
                                import logging
                                logging.debug(f"记录代理检测日志失败: {log_error}")
                                pass
                        return True
                    return False
        except Exception as e:
            # 记录失败日志
            if self.db:
                try:
                    await self.db.execute(
                        "INSERT INTO proxy_check_log (proxy_id, check_type, check_url, "
                        "success, error_message, add_ts) VALUES (%s, %s, %s, %s, %s, %s)",
                        (proxy_info.id, "health", "http://httpbin.org/ip", 0, str(e), int(time.time() * 1000))
                    )
                except Exception as log_error:
                    # 记录日志失败不影响代理检测结果
                    import logging
                    logging.debug(f"记录代理检测日志失败: {log_error}")
                    pass
            return False
    
    async def get_proxy_stats(self) -> Dict[str, Any]:
        """获取代理统计信息"""
        self._ensure_initialized()
        
        if not self.db:
            return {
                "total": 0,
                "active": 0,
                "available": 0,
                "avg_speed": 0,
                "avg_uptime": 0
            }
        
        try:
            stats = await self.db.get_first(
                "SELECT COUNT(*) as total, "
                "SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) as active, "
                "SUM(CASE WHEN last_check_result = 1 THEN 1 ELSE 0 END) as available, "
                "AVG(speed) as avg_speed, "
                "AVG(uptime) as avg_uptime "
                "FROM proxy_pool"
            )
            
            if not stats:
                return {
                    "total": 0,
                    "active": 0,
                    "available": 0,
                    "avg_speed": 0,
                    "avg_uptime": 0
                }
            
            return {
                "total": stats.get("total", 0),
                "active": stats.get("active", 0),
                "available": stats.get("available", 0),
                "avg_speed": round(stats.get("avg_speed") or 0, 2),
                "avg_uptime": round(stats.get("avg_uptime") or 0, 2)
            }
        except Exception as e:
            # 如果数据库查询失败，返回默认值
            import logging
            logging.warning(f"获取代理统计失败: {e}")
            # 记录到tools.utils.logger
            try:
                from tools import utils
                utils.logger.warning(f"获取代理统计失败: {e}")
            except ImportError:
                pass
            return {
                "total": 0,
                "active": 0,
                "available": 0,
                "avg_speed": 0,
                "avg_uptime": 0
            }
    
    async def get_strategies(self) -> List[Dict[str, Any]]:
        """获取所有策略"""
        self._ensure_initialized()
        
        if not self.db:
            # 如果没有数据库连接，返回默认策略列表
            return [
                {"id": 1, "name": "round_robin", "description": "轮询策略", "is_default": 1},
                {"id": 2, "name": "random", "description": "随机策略", "is_default": 0},
                {"id": 3, "name": "weighted", "description": "权重策略", "is_default": 0},
                {"id": 4, "name": "failover", "description": "故障转移策略", "is_default": 0},
                {"id": 5, "name": "geo_based", "description": "地理位置策略", "is_default": 0},
                {"id": 6, "name": "smart", "description": "智能策略", "is_default": 0}
            ]
        
        try:
            rows = await self.db.query(
                "SELECT * FROM proxy_strategy WHERE status = 1 ORDER BY is_default DESC, id ASC"
            )
            return rows or []
        except Exception as e:
            # 如果表不存在或其他错误，返回默认策略列表
            import logging
            logging.warning(f"获取代理策略失败: {e}")
            # 记录到tools.utils.logger
            try:
                from tools import utils
                utils.logger.warning(f"获取代理策略失败: {e}")
            except ImportError:
                pass
            return [
                {"id": 1, "name": "round_robin", "description": "轮询策略", "is_default": 1},
                {"id": 2, "name": "random", "description": "随机策略", "is_default": 0},
                {"id": 3, "name": "weighted", "description": "权重策略", "is_default": 0},
                {"id": 4, "name": "failover", "description": "故障转移策略", "is_default": 0},
                {"id": 5, "name": "geo_based", "description": "地理位置策略", "is_default": 0},
                {"id": 6, "name": "smart", "description": "智能策略", "is_default": 0}
            ] 