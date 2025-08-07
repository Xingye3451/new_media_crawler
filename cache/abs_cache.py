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
抽象缓存基类
定义缓存接口的抽象方法
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class AbstractCache(ABC):
    """抽象缓存基类"""
    
    @abstractmethod
    def set(self, key: str, value: Any, expire_time: Optional[int] = None) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            expire_time: 过期时间（秒）
        
        Returns:
            bool: 是否设置成功
        """
        pass
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            Any: 缓存值，如果不存在或已过期则返回None
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        删除缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 是否删除成功
        """
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        检查缓存键是否存在
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 是否存在
        """
        pass
    
    @abstractmethod
    def keys(self, pattern: str = "*") -> List[str]:
        """
        获取匹配模式的键列表
        
        Args:
            pattern: 匹配模式
        
        Returns:
            List[str]: 键列表
        """
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """
        清空所有缓存
        
        Returns:
            bool: 是否清空成功
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        关闭缓存连接
        """
        pass
