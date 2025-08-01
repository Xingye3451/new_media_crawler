# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  

# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/4/6 15:30
# @Desc    : 统一存储实现 - 多平台内容统一存储

import asyncio
import json
import time
from typing import Dict, List, Optional
from tools import utils

from base.base_crawler import AbstractStore
from store.unified_store import (
    query_content_by_content_id,
    add_new_content,
    update_content_by_content_id,
    query_comment_by_comment_id,
    add_new_comment,
    update_comment_by_comment_id,
    get_content_list,
    get_comment_list
)


class UnifiedStoreImplement(AbstractStore):
    """统一存储实现类"""
    
    def __init__(self, platform: str, redis_callback=None):
        """
        初始化统一存储实现
        
        Args:
            platform: 平台名称 (douyin, xhs, kuaishou, bilibili, weibo, zhihu, tieba)
            redis_callback: Redis回调函数
        """
        self.platform = platform
        self.redis_callback = redis_callback
        self.collected_data = []  # 收集爬取到的数据
        # 添加存储锁，确保串行化存储操作，避免数据库连接竞争
        self._storage_lock = asyncio.Lock()
        
    def set_redis_callback(self, callback):
        """设置Redis回调函数"""
        self.redis_callback = callback
    
    async def store_content(self, content_item: Dict):
        """
        统一内容存储实现
        
        Args:
            content_item: 内容字典
        """
        # 使用锁确保串行化存储，避免数据库连接竞争
        async with self._storage_lock:
            try:
                # 获取内容ID
                content_id = self._get_content_id(content_item)
                if not content_id:
                    utils.logger.error(f"[UnifiedStore] 无法获取内容ID: {content_item}")
                    return
                
                # 检查是否已存在
                existing_content = await query_content_by_content_id(self.platform, content_id)
                
                if not existing_content:
                    # 新增内容
                    task_id = content_item.get("task_id")
                    await add_new_content(self.platform, content_item, task_id)
                    utils.logger.debug(f"✅ [UnifiedStore] 新增内容成功: {self.platform}/{content_id}")
                else:
                    # 更新内容
                    await update_content_by_content_id(self.platform, content_id, content_item)
                    utils.logger.debug(f"✅ [UnifiedStore] 更新内容成功: {self.platform}/{content_id}")
                
                # 收集数据用于返回
                self.collected_data.append(content_item)
                
                # 存储到Redis
                if self.redis_callback:
                    await self.redis_callback(self.platform, content_item, "content")
                    
            except Exception as e:
                utils.logger.error(f"❌ [UnifiedStore] 存储内容失败: {self.platform}/{content_item.get('content_id', 'unknown')}, 错误: {e}")
                import traceback
                utils.logger.error(f"[UnifiedStore] 错误堆栈: {traceback.format_exc()}")
    
    async def store_comment(self, comment_item: Dict):
        """
        统一评论存储实现
        
        Args:
            comment_item: 评论字典
        """
        try:
            # 获取评论ID
            comment_id = self._get_comment_id(comment_item)
            if not comment_id:
                utils.logger.error(f"[UnifiedStore] 无法获取评论ID: {comment_item}")
                return
            
            # 检查是否已存在
            existing_comment = await query_comment_by_comment_id(self.platform, comment_id)
            
            if not existing_comment:
                # 新增评论
                await add_new_comment(self.platform, comment_item)
                utils.logger.debug(f"✅ [UnifiedStore] 新增评论成功: {self.platform}/{comment_id}")
            else:
                # 更新评论
                await update_comment_by_comment_id(self.platform, comment_id, comment_item)
                utils.logger.debug(f"✅ [UnifiedStore] 更新评论成功: {self.platform}/{comment_id}")
            
            # 存储到Redis
            if self.redis_callback:
                await self.redis_callback(self.platform, comment_item, "comment")
                
        except Exception as e:
            utils.logger.error(f"❌ [UnifiedStore] 存储评论失败: {self.platform}/{comment_item.get('comment_id', 'unknown')}, 错误: {e}")
    
    async def store_creator(self, creator_item: Dict):
        """
        统一创作者存储实现
        
        Args:
            creator_item: 创作者字典
        """
        try:
            # 存储到Redis
            if self.redis_callback:
                await self.redis_callback(self.platform, creator_item, "creator")
                
        except Exception as e:
            utils.logger.error(f"❌ [UnifiedStore] 存储创作者失败: {self.platform}/{creator_item.get('creator_id', 'unknown')}, 错误: {e}")
    
    def _get_content_id(self, content_item: Dict) -> Optional[str]:
        """获取内容ID"""
        # 根据平台获取对应的内容ID字段
        id_mapping = {
            "douyin": "aweme_id",
            "xhs": "note_id", 
            "kuaishou": "photo_id",
            "bilibili": "bvid",
            "weibo": "id",
            "zhihu": "id",
            "tieba": "tid"
        }
        
        id_field = id_mapping.get(self.platform)
        if id_field and id_field in content_item:
            return content_item[id_field]
        
        # 如果没有找到，尝试通用字段
        for field in ["content_id", "id", "video_id", "note_id"]:
            if field in content_item:
                return content_item[field]
        
        return None
    
    def _get_comment_id(self, comment_item: Dict) -> Optional[str]:
        """获取评论ID"""
        # 根据平台获取对应的评论ID字段
        id_mapping = {
            "douyin": "comment_id",
            "xhs": "comment_id",
            "kuaishou": "comment_id", 
            "bilibili": "comment_id",
            "weibo": "comment_id",
            "zhihu": "comment_id",
            "tieba": "comment_id"
        }
        
        id_field = id_mapping.get(self.platform)
        if id_field and id_field in comment_item:
            return comment_item[id_field]
        
        # 如果没有找到，尝试通用字段
        for field in ["comment_id", "id", "cid"]:
            if field in comment_item:
                return comment_item[field]
        
        return None
    
    async def get_all_content(self) -> List[Dict]:
        """
        获取所有存储的内容
        
        Returns:
            List[Dict]: 内容列表
        """
        utils.logger.info(f"[UnifiedStore] 获取存储内容 - 共收集到 {len(self.collected_data)} 条数据")
        return self.collected_data


class UnifiedStoreFactory:
    """统一存储工厂类"""
    
    @staticmethod
    def create_store(platform: str, redis_callback=None) -> UnifiedStoreImplement:
        """
        创建统一存储实例
        
        Args:
            platform: 平台名称
            redis_callback: Redis回调函数
            
        Returns:
            UnifiedStoreImplement: 统一存储实例
        """
        return UnifiedStoreImplement(platform, redis_callback) 