"""
任务清理初始化模块
用于启动定期清理任务，防止内存泄漏
"""

import asyncio
from tools import utils

async def init_task_cleanup():
    """初始化任务清理机制"""
    try:
        utils.logger.info("🔄 启动任务清理机制...")
        
        # 导入清理函数
        from api.crawler_core import start_task_cleanup
        from api.multi_platform_crawler import start_multi_platform_task_cleanup
        
        # 启动单平台任务清理
        asyncio.create_task(start_task_cleanup())
        utils.logger.info("✅ 单平台任务清理已启动")
        
        # 启动多平台任务清理
        asyncio.create_task(start_multi_platform_task_cleanup())
        utils.logger.info("✅ 多平台任务清理已启动")
        
        utils.logger.info("✅ 任务清理机制初始化完成")
        
    except Exception as e:
        utils.logger.error(f"❌ 任务清理机制初始化失败: {e}")

# 如果直接运行此脚本
if __name__ == "__main__":
    asyncio.run(init_task_cleanup()) 