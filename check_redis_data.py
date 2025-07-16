#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Redis中的抖音数据
"""

import redis
import yaml
import json

def load_config():
    """加载配置文件"""
    with open('config/config_local.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    """主函数"""
    config = load_config()
    
    # 连接Redis
    redis_client = redis.Redis(
        host=config['redis']['host'],
        port=config['redis']['port'],
        password=config['redis']['password'],
        decode_responses=True
    )
    
    print("🔍 [检查] Redis中的抖音数据...")
    
    # 检查所有key
    all_keys = redis_client.keys("*")
    print(f"📊 [总数] Redis中共有 {len(all_keys)} 个key")
    
    # 查找抖音相关的key
    douyin_keys = []
    for key in all_keys:
        if 'dy' in key or 'douyin' in key:
            douyin_keys.append(key)
    
    print(f"🎬 [抖音] 找到 {len(douyin_keys)} 个抖音相关key")
    
    if douyin_keys:
        print("\n📋 [抖音Keys]:")
        for key in douyin_keys:
            print(f"  {key}")
        
        # 检查第一个抖音key的数据
        sample_key = douyin_keys[0]
        print(f"\n🔍 [检查] 第一个抖音key: {sample_key}")
        
        # 获取数据类型
        key_type = redis_client.type(sample_key)
        print(f"📝 [类型] {key_type}")
        
        if key_type == 'hash':
            # 如果是hash类型，获取所有字段
            data = redis_client.hgetall(sample_key)
            print(f"📊 [字段数] {len(data)}")
            print("\n📋 [数据内容]:")
            for field, value in data.items():
                print(f"  {field}: {value[:100]}{'...' if len(value) > 100 else ''}")
        elif key_type == 'string':
            # 如果是string类型
            data = redis_client.get(sample_key)
            print(f"📝 [内容] {data[:200]}{'...' if len(data) > 200 else ''}")
        elif key_type == 'list':
            # 如果是list类型
            data = redis_client.lrange(sample_key, 0, -1)
            print(f"📝 [列表长度] {len(data)}")
            if data:
                print(f"📝 [第一个元素] {data[0][:100]}{'...' if len(data[0]) > 100 else ''}")
    
    # 检查特定模式的key
    patterns = [
        "dy:video:*",
        "dy:*",
        "*douyin*",
        "*video*"
    ]
    
    print("\n🔍 [模式搜索]:")
    for pattern in patterns:
        keys = redis_client.keys(pattern)
        print(f"  {pattern}: {len(keys)} 个")
        if keys:
            print(f"    示例: {keys[0]}")
    
    # 检查Redis连接
    try:
        redis_client.ping()
        print("\n✅ [连接] Redis连接正常")
    except Exception as e:
        print(f"\n❌ [连接] Redis连接失败: {e}")

if __name__ == "__main__":
    main() 