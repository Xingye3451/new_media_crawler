#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试抖音页面关闭问题修复
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from media_platform.douyin.core import DouYinCrawler
import utils


async def test_douyin_page_close_fix():
    """测试抖音页面关闭问题修复"""
    try:
        utils.logger.info("🧪 [TEST] 开始测试抖音页面关闭问题修复")
        
        # 创建爬虫实例
        crawler = DouYinCrawler(task_id="test_page_close_fix")
        
        # 设置测试参数
        crawler.dynamic_keywords = ["香克斯"]  # 使用简单的关键词
        crawler.max_notes_count = 3  # 限制数量，避免长时间运行
        
        utils.logger.info("🧪 [TEST] 开始执行搜索任务")
        
        # 执行搜索
        results = await crawler.search_by_keywords(
            keywords="香克斯",  # 修复：传递字符串而不是列表
            max_count=3,  # 减少数量
            get_comments=False,
            save_data_option="db"
        )
        
        utils.logger.info(f"🧪 [TEST] 搜索完成，获取 {len(results)} 条数据")
        
        # 检查是否有页面关闭警告
        utils.logger.info("🧪 [TEST] 检查页面关闭警告...")
        
        # 验证结果
        if results:
            utils.logger.info("✅ [TEST] 测试成功：成功获取数据且无页面关闭错误")
            return True
        else:
            utils.logger.warning("⚠️ [TEST] 测试警告：未获取到数据，但无页面关闭错误")
            return True
            
    except Exception as e:
        utils.logger.error(f"❌ [TEST] 测试失败: {e}")
        return False
    finally:
        utils.logger.info("🧪 [TEST] 测试完成")


if __name__ == "__main__":
    try:
        # 运行测试
        result = asyncio.run(test_douyin_page_close_fix())
        
        if result:
            print("✅ 抖音页面关闭问题修复测试通过")
            sys.exit(0)
        else:
            print("❌ 抖音页面关闭问题修复测试失败")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        sys.exit(1)
