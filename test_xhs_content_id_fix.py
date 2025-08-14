#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书content_id字段修复验证脚本
"""

import asyncio
import json
from datetime import datetime

# 模拟小红书数据结构
test_xhs_data = {
    "note_id": "665d515a0000000003031ab9",  # 这是内容ID
    "type": "video",
    "desc": "这是一个测试笔记",
    "user": {
        "user_id": "user123",
        "nickname": "测试用户",
        "avatar": "https://example.com/avatar.jpg"
    },
    "interact_info": {
        "liked_count": 100,
        "comment_count": 50,
        "share_count": 20,
        "collected_count": 30
    },
    "image_list": [
        {"url_default": "https://example.com/image1.jpg"}
    ],
    "tag_list": [{"name": "测试", "type": "topic"}],
    "time": 1640995200000,
    "last_update_time": 1640995200000,
    "ip_location": "北京",
    "source_keyword": "测试关键词"
}

def test_field_mapping():
    """测试字段映射"""
    print("=" * 80)
    print("🔄 测试小红书字段映射修复")
    print("=" * 80)
    
    # 导入字段映射函数
    try:
        from store.unified_store import map_platform_fields
        print("✅ 成功导入字段映射函数")
        
        # 测试映射
        mapped_data = map_platform_fields("xhs", test_xhs_data)
        print(f"📊 映射后字段数: {len(mapped_data)}")
        print(f"📋 映射后字段: {list(mapped_data.keys())}")
        
        # 检查关键字段
        content_id = mapped_data.get("content_id")
        print(f"🎯 content_id: {content_id}")
        
        if content_id and content_id == test_xhs_data["note_id"]:
            print("✅ content_id字段映射正确")
        else:
            print("❌ content_id字段映射错误")
            print(f"   期望值: {test_xhs_data['note_id']}")
            print(f"   实际值: {content_id}")
        
        # 检查其他重要字段
        important_fields = ["content_type", "title", "author_id", "like_count"]
        for field in important_fields:
            value = mapped_data.get(field)
            print(f"📌 {field}: {value}")
        
        return mapped_data
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(f"📊 错误堆栈: {traceback.format_exc()}")
        return None

def test_database_insertion():
    """测试数据库插入（模拟）"""
    print("\n" + "=" * 80)
    print("🔄 测试数据库插入（模拟）")
    print("=" * 80)
    
    try:
        from store.unified_store import map_platform_fields, serialize_for_db, filter_fields_for_table, UNIFIED_CONTENT_FIELDS
        
        # 映射字段
        mapped_data = map_platform_fields("xhs", test_xhs_data)
        
        # 添加时间戳
        import time
        now_ts = int(time.time() * 1000)
        mapped_data["add_ts"] = now_ts
        mapped_data["last_modify_ts"] = now_ts
        
        # 序列化数据
        safe_item = serialize_for_db(mapped_data)
        print(f"📊 序列化后字段数: {len(safe_item)}")
        
        # 过滤字段
        safe_item = filter_fields_for_table(safe_item, UNIFIED_CONTENT_FIELDS)
        print(f"📊 过滤后字段数: {len(safe_item)}")
        
        # 检查content_id是否存在
        if "content_id" in safe_item:
            content_id = safe_item["content_id"]
            print(f"✅ content_id存在: {content_id}")
            
            if content_id and content_id != "":
                print("✅ content_id字段有效，可以插入数据库")
                return True
            else:
                print("❌ content_id字段为空")
                return False
        else:
            print("❌ content_id字段不存在")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(f"📊 错误堆栈: {traceback.format_exc()}")
        return False

async def main():
    """主函数"""
    print("🚀 小红书content_id字段修复验证脚本")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 测试字段映射
        mapped_data = test_field_mapping()
        
        if mapped_data:
            # 测试数据库插入
            success = test_database_insertion()
            
            if success:
                print("\n" + "=" * 80)
                print("✅ 所有测试通过！content_id字段修复成功")
                print("=" * 80)
            else:
                print("\n" + "=" * 80)
                print("❌ 数据库插入测试失败")
                print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("❌ 字段映射测试失败")
            print("=" * 80)
            
    except Exception as e:
        print(f"\n❌ 测试过程中发生异常: {e}")
    
    print(f"\n⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())
