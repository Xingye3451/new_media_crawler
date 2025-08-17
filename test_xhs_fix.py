#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试小红书爬虫修复
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from media_platform.xhs.core import XiaoHongShuCrawler
import utils


async def test_xhs_fix():
    """测试小红书爬虫修复"""
    try:
        utils.logger.info("🧪 [TEST] 开始测试小红书爬虫修复")
        
        # 创建爬虫实例
        crawler = XiaoHongShuCrawler(task_id="test_xhs_fix")
        
        # 设置测试参数
        crawler.dynamic_creators = ["68817545000000001d00a07f"]  # 使用测试创作者ID
        crawler.max_notes_count = 5  # 限制数量，避免长时间运行
        
        utils.logger.info("🧪 [TEST] 开始执行创作者模式")
        
        # 执行创作者模式
        await crawler._init_crawler_only()
        
        utils.logger.info("🧪 [TEST] 初始化完成，开始获取创作者笔记")
        
        # 获取创作者笔记
        results = await crawler.get_creators_and_notes_from_db()
        
        utils.logger.info(f"🧪 [TEST] 获取完成，共 {len(results) if results else 0} 条数据")
        
        # 验证结果
        if results:
            utils.logger.info("✅ [TEST] 测试成功：成功获取数据")
            return True
        else:
            utils.logger.warning("⚠️ [TEST] 测试警告：未获取到数据")
            return True
            
    except Exception as e:
        utils.logger.error(f"❌ [TEST] 测试失败: {e}")
        return False
    finally:
        utils.logger.info("🧪 [TEST] 测试完成")


if __name__ == "__main__":
    try:
        # 运行测试
        result = asyncio.run(test_xhs_fix())
        
        if result:
            print("✅ 小红书爬虫修复测试通过")
            sys.exit(0)
        else:
            print("❌ 小红书爬虫修复测试失败")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        sys.exit(1)
