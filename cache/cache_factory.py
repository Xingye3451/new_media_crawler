# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  

"""
缓存工厂类
根据配置创建不同类型的缓存实例
"""

import json
import time
from typing import Any, Dict, List, Optional
from threading import Lock

from .abs_cache import AbstractCache
import config


class MemoryCache(AbstractCache):
    """内存缓存实现"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
    
    def set(self, key: str, value: Any, expire_time: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            with self._lock:
                expire_at = None
                if expire_time:
                    expire_at = time.time() + expire_time
                
                self._cache[key] = {
                    'value': value,
                    'expire_at': expire_at
                }
                return True
        except Exception:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            with self._lock:
                if key not in self._cache:
                    return None
                
                cache_item = self._cache[key]
                
                # 检查是否过期
                if cache_item['expire_at'] and time.time() > cache_item['expire_at']:
                    del self._cache[key]
                    return None
                
                return cache_item['value']
        except Exception:
            return None
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            with self._lock:
                if key in self._cache:
                    del self._cache[key]
                    return True
                return False
        except Exception:
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存键是否存在"""
        try:
            with self._lock:
                if key not in self._cache:
                    return False
                
                # 检查是否过期
                cache_item = self._cache[key]
                if cache_item['expire_at'] and time.time() > cache_item['expire_at']:
                    del self._cache[key]
                    return False
                
                return True
        except Exception:
            return False
    
    def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的键列表"""
        try:
            with self._lock:
                result = []
                current_time = time.time()
                
                for key in list(self._cache.keys()):
                    # 检查是否过期
                    cache_item = self._cache[key]
                    if cache_item['expire_at'] and current_time > cache_item['expire_at']:
                        del self._cache[key]
                        continue
                    
                    # 简单的模式匹配（支持*通配符）
                    if self._match_pattern(key, pattern):
                        result.append(key)
                
                return result
        except Exception:
            return []
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """简单的模式匹配"""
        if pattern == "*":
            return True
        
        # 简单的通配符匹配
        if "*" in pattern:
            parts = pattern.split("*")
            if len(parts) == 2:
                return key.startswith(parts[0]) and key.endswith(parts[1])
            elif len(parts) == 1:
                return key.startswith(parts[0]) or key.endswith(parts[0])
        
        return key == pattern
    
    def clear(self) -> bool:
        """清空所有缓存"""
        try:
            with self._lock:
                self._cache.clear()
                return True
        except Exception:
            return False
    
    def close(self) -> None:
        """关闭缓存连接（内存缓存无需关闭）"""
        pass


class RedisCache(AbstractCache):
    """Redis缓存实现"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, 
                 password: Optional[str] = None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._redis = None
        self._connect()
    
    def _connect(self):
        """连接Redis"""
        try:
            import redis
            self._redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True
            )
            # 测试连接
            self._redis.ping()
        except Exception as e:
            print(f"Redis连接失败: {e}")
            self._redis = None
    
    def set(self, key: str, value: Any, expire_time: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            if not self._redis:
                return False
            
            # 序列化值
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            if expire_time:
                return self._redis.setex(key, expire_time, value)
            else:
                return self._redis.set(key, value)
        except Exception:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            if not self._redis:
                return None
            
            value = self._redis.get(key)
            if value is None:
                return None
            
            # 尝试反序列化
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception:
            return None
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            if not self._redis:
                return False
            return bool(self._redis.delete(key))
        except Exception:
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存键是否存在"""
        try:
            if not self._redis:
                return False
            return bool(self._redis.exists(key))
        except Exception:
            return False
    
    def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的键列表"""
        try:
            if not self._redis:
                return []
            return self._redis.keys(pattern)
        except Exception:
            return []
    
    def clear(self) -> bool:
        """清空所有缓存"""
        try:
            if not self._redis:
                return False
            self._redis.flushdb()
            return True
        except Exception:
            return False
    
    def close(self) -> None:
        """关闭缓存连接"""
        try:
            if self._redis:
                self._redis.close()
        except Exception:
            pass


class CacheFactory:
    """缓存工厂类"""
    
    @staticmethod
    def create_cache(cache_type: str = "memory", **kwargs) -> AbstractCache:
        """
        创建缓存实例
        
        Args:
            cache_type: 缓存类型 ("memory" 或 "redis")
            **kwargs: 其他参数
        
        Returns:
            AbstractCache: 缓存实例
        """
        if cache_type == "memory":
            return MemoryCache()
        elif cache_type == "redis":
            # 从配置中获取Redis连接参数
            host = kwargs.get('host', getattr(config, 'REDIS_DB_HOST', 'localhost'))
            port = kwargs.get('port', getattr(config, 'REDIS_DB_PORT', 6379))
            db = kwargs.get('db', getattr(config, 'REDIS_DB_NUM', 0))
            password = kwargs.get('password', getattr(config, 'REDIS_DB_PWD', None))
            
            return RedisCache(host=host, port=port, db=db, password=password)
        else:
            raise ValueError(f"不支持的缓存类型: {cache_type}")
