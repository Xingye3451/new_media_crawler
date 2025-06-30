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
# @Time    : 2024/4/5 09:43
# @Desc    : 青果代理测试脚本
import asyncio
import os
from proxy.providers.qingguo_proxy import new_qingguo_proxy, parse_qingguo_proxy


async def test_qingguo_proxy():
    """
    测试青果代理功能
    """
    print("=== 青果代理测试开始 ===")
    
    # 设置测试环境变量
    os.environ["qg_key"] = "your_qingguo_key_here"  # 请替换为实际的Key
    os.environ["qg_pwd"] = "your_qingguo_pwd_here"  # 请替换为实际的密码（可选）
    
    try:
        # 创建青果代理实例
        qingguo_proxy = new_qingguo_proxy()
        print(f"✓ 青果代理实例创建成功")
        
        # 测试获取账户余额
        print("\n--- 测试获取账户余额 ---")
        balance = await qingguo_proxy.get_balance()
        print(f"账户余额: {balance}")
        
        # 测试获取代理IP
        print("\n--- 测试获取代理IP ---")
        proxies = await qingguo_proxy.get_proxies(2)
        print(f"获取到 {len(proxies)} 个代理IP:")
        
        for i, proxy in enumerate(proxies, 1):
            print(f"  代理 {i}: {proxy.ip}:{proxy.port}")
            print(f"    用户名: {proxy.user}")
            print(f"    密码: {proxy.password}")
            print(f"    过期时间: {proxy.expired_time_ts}")
            
            # 测试释放代理（如果有代理的话）
            if i == 1:  # 只测试第一个代理
                print(f"\n--- 测试释放代理 {proxy.ip}:{proxy.port} ---")
                release_result = await qingguo_proxy.release_proxy(proxy.ip, proxy.port)
                print(f"释放结果: {'成功' if release_result else '失败'}")
        
        print("\n=== 青果代理测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_parse_qingguo_proxy():
    """
    测试解析青果代理信息
    """
    print("\n=== 测试解析青果代理信息 ===")
    
    # 测试用例
    test_cases = [
        "192.168.1.1:8080,1640995200",  # 正常格式
        "10.0.0.1:3128,1640995200",     # 正常格式
        "invalid_format",               # 无效格式
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case}")
        try:
            result = parse_qingguo_proxy(test_case)
            print(f"✓ 解析成功: IP={result.ip}, Port={result.port}, Expire={result.expire_ts}")
        except Exception as e:
            print(f"❌ 解析失败: {e}")


if __name__ == "__main__":
    # 测试解析功能
    test_parse_qingguo_proxy()
    
    # 测试代理功能（需要有效的Key）
    asyncio.run(test_qingguo_proxy()) 