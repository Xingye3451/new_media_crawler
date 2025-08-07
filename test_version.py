#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试版本读取功能
"""

import os
import sys

def read_version():
    """读取 VERSION 文件"""
    version_file = "VERSION"
    if os.path.exists(version_file):
        with open(version_file, 'r', encoding='utf-8') as f:
            version = f.read().strip()
            print(f"✅ 成功读取版本: {version}")
            return version
    else:
        print(f"❌ VERSION 文件不存在: {version_file}")
        return None

def test_docker_version():
    """测试 Docker 版本环境变量"""
    print("\n=== 测试 Docker 版本环境变量 ===")
    
    # 模拟 Docker 构建时的环境变量
    os.environ['VERSION'] = 'v1.0.0'
    os.environ['BUILD_DATE'] = '2024-01-01T00:00:00Z'
    os.environ['VCS_REF'] = 'abc123'
    
    print(f"VERSION: {os.environ.get('VERSION', '未设置')}")
    print(f"BUILD_DATE: {os.environ.get('BUILD_DATE', '未设置')}")
    print(f"VCS_REF: {os.environ.get('VCS_REF', '未设置')}")

def test_docker_compose_version():
    """测试 docker-compose 版本变量"""
    print("\n=== 测试 docker-compose 版本变量 ===")
    
    # 模拟 docker-compose 环境变量
    os.environ['VERSION'] = 'v1.0.0'
    
    compose_vars = {
        'VERSION': os.environ.get('VERSION', 'v1.0.0'),
        'APP_VERSION': os.environ.get('APP_VERSION', 'v1.0.0'),
    }
    
    print("docker-compose 环境变量:")
    for key, value in compose_vars.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    print("MediaCrawler 版本测试")
    print("=" * 30)
    
    # 测试版本文件读取
    version = read_version()
    
    # 测试 Docker 版本
    test_docker_version()
    
    # 测试 docker-compose 版本
    test_docker_compose_version()
    
    print(f"\n✅ 版本测试完成，当前版本: {version}")
