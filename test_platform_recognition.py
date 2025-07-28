#!/usr/bin/env python3
"""
测试平台识别功能
"""

def test_platform_recognition():
    """测试平台识别功能"""
    
    # 测试数据
    test_cases = [
        # 小红书
        {
            "platform": "xhs",
            "url": "http://sns-video-bd.xhscdn.com/pre_post/1040g0cg31ke9r65c34a05p3f1a14mq5cui9tveg",
            "expected": "小红书"
        },
        {
            "platform": "xhs",
            "url": "https://www.xiaohongshu.com/explore/6885b86c000000002400c6ae",
            "expected": "小红书"
        },
        
        # 抖音
        {
            "platform": "dy",
            "url": "https://www.douyin.com/video/7123456789012345678",
            "expected": "抖音"
        },
        {
            "platform": "dy",
            "url": "http://aweme.snssdk.com/aweme/v1/play/",
            "expected": "抖音"
        },
        
        # 快手
        {
            "platform": "ks",
            "url": "https://www.kuaishou.com/short-video/123456789",
            "expected": "快手"
        },
        {
            "platform": "ks",
            "url": "https://gifshow.com/short-video/123456789",
            "expected": "快手"
        },
        
        # B站
        {
            "platform": "bili",
            "url": "https://www.bilibili.com/video/BV1234567890",
            "expected": "B站"
        },
        {
            "platform": "bili",
            "url": "https://b23.tv/BV1234567890",
            "expected": "B站"
        },
        
        # 微博
        {
            "platform": "wb",
            "url": "https://weibo.com/1234567890/1234567890",
            "expected": "微博"
        },
        {
            "platform": "wb",
            "url": "https://video.weibo.com/show?fid=1234567890",
            "expected": "微博"
        },
        
        # 知乎
        {
            "platform": "zhihu",
            "url": "https://www.zhihu.com/zvideo/1234567890",
            "expected": "知乎"
        },
        {
            "platform": "zhihu",
            "url": "https://www.zhihu.com/question/1234567890",
            "expected": "知乎"
        }
    ]
    
    print("🔍 测试平台识别功能...")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        platform = test_case["platform"]
        url = test_case["url"]
        expected = test_case["expected"]
        
        # 模拟平台识别逻辑
        detected_platform = detect_platform(platform, url)
        
        print(f"测试 {i}:")
        print(f"  平台参数: {platform}")
        print(f"  URL: {url}")
        print(f"  期望: {expected}")
        print(f"  识别结果: {detected_platform}")
        print(f"  状态: {'✅ 通过' if detected_platform == expected else '❌ 失败'}")
        print("-" * 40)
    
    print("🎉 平台识别测试完成！")

def detect_platform(platform: str, url: str) -> str:
    """模拟平台识别逻辑"""
    platform = platform.lower()
    url_lower = url.lower()
    
    # 平台识别逻辑
    if (platform == "xhs" or 
        'xiaohongshu' in url_lower or 
        'xhscdn' in url_lower or 
        'xhs' in url_lower):
        return "小红书"
        
    elif (platform == "dy" or 
          'douyin' in url_lower or 
          'aweme' in url_lower or
          'amemv' in url_lower):
        return "抖音"
        
    elif (platform == "ks" or 
          'kuaishou' in url_lower or 
          'gifshow' in url_lower or
          'ks' in url_lower):
        return "快手"
        
    elif (platform == "bili" or 
          'bilibili' in url_lower or 
          'b23.tv' in url_lower or
          'bilivideo' in url_lower):
        return "B站"
        
    elif (platform == "wb" or 
          'weibo' in url_lower or 
          'sina' in url_lower):
        return "微博"
        
    elif (platform == "zhihu" or 
          'zhihu' in url_lower):
        return "知乎"
        
    else:
        return "未知平台"

def test_referer_generation():
    """测试Referer生成"""
    
    print("\n🔍 测试Referer生成...")
    print("=" * 60)
    
    platforms = [
        ("xhs", "小红书"),
        ("dy", "抖音"),
        ("ks", "快手"),
        ("bili", "B站"),
        ("wb", "微博"),
        ("zhihu", "知乎")
    ]
    
    for platform, name in platforms:
        referer = get_referer(platform)
        print(f"{name} ({platform}): {referer}")
    
    print("🎉 Referer生成测试完成！")

def get_referer(platform: str) -> str:
    """获取平台对应的Referer"""
    referer_map = {
        "xhs": "https://www.xiaohongshu.com/",
        "dy": "https://www.douyin.com/",
        "ks": "https://www.kuaishou.com/",
        "bili": "https://www.bilibili.com/",
        "wb": "https://weibo.com/",
        "zhihu": "https://www.zhihu.com/"
    }
    return referer_map.get(platform, "https://www.google.com/")

if __name__ == "__main__":
    test_platform_recognition()
    test_referer_generation() 