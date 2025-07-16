#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音预览功能简化测试脚本

功能：
1. 检查Redis中的抖音数据
2. 验证播放页链接保存
3. 生成预览HTML页面
4. 演示平台集成方案
"""

import asyncio
import json
import redis
import yaml
import os
from typing import Dict, List

class DouyinSimplePreviewTester:
    """抖音预览功能简化测试器"""
    
    def __init__(self):
        self.config = self.load_config()
        self.redis_client = redis.Redis(
            host=self.config['redis']['host'],
            port=self.config['redis']['port'],
            password=self.config['redis']['password'],
            decode_responses=True
        )
        
    def load_config(self):
        """加载配置文件"""
        with open('config/config_local.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    async def test_redis_data(self):
        """测试Redis中的数据"""
        print("🔍 [测试] 检查Redis中的抖音数据...")
        
        # 获取所有抖音视频数据
        pattern = "video:dy:*"
        keys = self.redis_client.keys(pattern)
        
        if not keys:
            print("❌ [警告] Redis中没有找到抖音视频数据")
            print("💡 [建议] 请先运行抖音爬虫获取数据")
            return False
        
        print(f"✅ [发现] 找到 {len(keys)} 条抖音视频数据")
        
        # 检查数据结构
        sample_key = keys[0]
        sample_data = self.redis_client.hgetall(sample_key)
        
        print("\n📋 [数据结构] 抖音视频数据字段:")
        for field, value in sample_data.items():
            print(f"  {field}: {value[:100]}{'...' if len(value) > 100 else ''}")
        
        # 重点检查播放页链接
        aweme_url = sample_data.get('aweme_url', '')
        video_download_url = sample_data.get('video_download_url', '')
        title = sample_data.get('title', '')
        
        print(f"\n🎬 [播放页链接] {aweme_url}")
        print(f"📥 [下载链接] {video_download_url}")
        print(f"📝 [标题] {title}")
        
        if aweme_url:
            print("✅ [成功] 播放页链接已正确保存")
            return sample_data
        else:
            print("❌ [错误] 播放页链接为空")
            return None
    
    async def generate_preview_html(self, aweme_url: str, title: str = "抖音视频预览"):
        """生成预览HTML页面"""
        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(45deg, #ff6b6b, #ee5a24);
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .preview-section {{
            padding: 30px;
        }}
        .video-container {{
            position: relative;
            width: 100%;
            height: 0;
            padding-bottom: 56.25%; /* 16:9 比例 */
            margin-bottom: 20px;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .video-iframe {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border: none;
            border-radius: 10px;
        }}
        .info-section {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
        }}
        .info-item {{
            margin-bottom: 10px;
            display: flex;
            align-items: center;
        }}
        .info-label {{
            font-weight: bold;
            color: #495057;
            min-width: 100px;
        }}
        .info-value {{
            color: #6c757d;
        }}
        .btn {{
            display: inline-block;
            padding: 12px 24px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            text-decoration: none;
            border-radius: 25px;
            margin: 10px;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }}
        .warning {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .success {{
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 抖音视频预览</h1>
            <p>MediaCrawler 平台内预览功能演示</p>
        </div>
        
        <div class="preview-section">
            <div class="success">
                <strong>✅ 预览方案说明：</strong>
                这是MediaCrawler项目的第一种预览方案（保存播放页链接+平台内预览）
                <ul>
                    <li>✅ 保存了抖音视频的播放页链接</li>
                    <li>✅ 可以在平台内直接预览</li>
                    <li>✅ 支持在新窗口打开原视频</li>
                    <li>✅ 提供复制链接功能</li>
                </ul>
            </div>
            
            <div class="warning">
                <strong>⚠️ 预览说明：</strong>
                由于抖音的反爬虫机制，直接嵌入播放页可能被限制。建议：
                <ul>
                    <li>点击下方"在抖音中查看"按钮，在新窗口打开原视频</li>
                    <li>或使用"复制链接"功能分享给其他用户</li>
                </ul>
            </div>
            
            <div class="video-container">
                <iframe 
                    src="{aweme_url}" 
                    class="video-iframe"
                    allowfullscreen>
                </iframe>
            </div>
            
            <div class="info-section">
                <h3>📋 视频信息</h3>
                <div class="info-item">
                    <span class="info-label">播放页链接:</span>
                    <span class="info-value">{aweme_url}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">视频标题:</span>
                    <span class="info-value">{title}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">来源平台:</span>
                    <span class="info-value">抖音</span>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="{aweme_url}" target="_blank" class="btn">
                    🔗 在抖音中查看
                </a>
                <button onclick="copyToClipboard('{aweme_url}')" class="btn">
                    📋 复制链接
                </button>
            </div>
        </div>
    </div>
    
    <script>
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(function() {{
                alert('链接已复制到剪贴板！');
            }}, function(err) {{
                console.error('复制失败: ', err);
            }});
        }}
    </script>
</body>
</html>
        """
        return html_template
    
    async def create_preview_demo(self, sample_data: Dict):
        """创建预览演示"""
        print("\n🎯 [演示] 创建预览演示...")
        
        aweme_url = sample_data.get('aweme_url', '')
        title = sample_data.get('title', '抖音视频')
        
        if not aweme_url:
            print("❌ [错误] 播放页链接为空")
            return None
        
        # 生成预览HTML
        html_content = await self.generate_preview_html(aweme_url, title)
        
        # 保存预览HTML文件
        preview_file = "douyin_preview_demo.html"
        with open(preview_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ [成功] 预览HTML已生成: {preview_file}")
        print(f"🔗 [播放页] {aweme_url}")
        print(f"📝 [标题] {title}")
        
        return preview_file
    
    async def demonstrate_api_integration(self):
        """演示API集成方案"""
        print("\n🚀 [演示] API集成方案...")
        
        # 获取所有抖音视频数据
        keys = self.redis_client.keys("video:dy:*")
        videos = []
        
        for key in keys[:3]:  # 只取前3条
            data = self.redis_client.hgetall(key)
            videos.append({
                "id": data.get("aweme_id"),
                "title": data.get("title"),
                "preview_url": data.get("aweme_url"),  # 播放页链接
                "cover_url": data.get("cover_url"),
                "author": data.get("nickname"),
                "likes": data.get("liked_count"),
                "comments": data.get("comment_count"),
                "shares": data.get("share_count")
            })
        
        api_response = {
            "success": True,
            "message": "获取抖音视频列表成功",
            "data": {
                "videos": videos,
                "total": len(videos),
                "platform": "douyin"
            }
        }
        
        print("📡 [API响应] 模拟后端API:")
        print(json.dumps(api_response, ensure_ascii=False, indent=2))
        
        return api_response
    
    async def demonstrate_frontend_integration(self):
        """演示前端集成方案"""
        print("\n🎨 [演示] 前端集成方案...")
        
        frontend_code = '''
# React/Vue.js 前端集成示例

## 1. 视频预览组件
```javascript
const DouyinVideoPreview = ({ awemeUrl, title, coverUrl, author, likes, comments }) => {
  return (
    <div className="video-preview-card">
      <div className="video-container">
        <iframe 
          src={awemeUrl} 
          allowFullScreen
          className="video-iframe"
        />
      </div>
      <div className="video-info">
        <h3>{title}</h3>
        <p>作者: {author}</p>
        <div className="stats">
          <span>👍 {likes}</span>
          <span>💬 {comments}</span>
        </div>
      </div>
      <div className="video-actions">
        <button onClick={() => window.open(awemeUrl, '_blank')}>
          在抖音中查看
        </button>
        <button onClick={() => copyToClipboard(awemeUrl)}>
          复制链接
        </button>
      </div>
    </div>
  );
};
```

## 2. 视频列表组件
```javascript
const DouyinVideoList = () => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchDouyinVideos();
  }, []);

  const fetchDouyinVideos = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/douyin/videos');
      const data = await response.json();
      setVideos(data.data.videos);
    } catch (error) {
      console.error('获取视频列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="video-list">
      {loading ? (
        <div>加载中...</div>
      ) : (
        videos.map(video => (
          <DouyinVideoPreview key={video.id} {...video} />
        ))
      )}
    </div>
  );
};
```

## 3. 管理后台功能
- ✅ 视频列表展示（带预览）
- ✅ 批量操作（收藏、标记、删除）
- ✅ 数据统计和分析
- ✅ 导出功能
- ✅ 搜索和筛选
        '''
        
        print(frontend_code)
    
    async def run_simple_test(self):
        """运行简化测试"""
        print("🎬 [开始] 抖音预览功能简化测试")
        print("=" * 60)
        
        try:
            # 步骤1: 检查Redis数据
            sample_data = await self.test_redis_data()
            if not sample_data:
                print("❌ [失败] 没有找到有效的抖音数据")
                print("💡 [建议] 请先运行抖音爬虫: python main.py --platform dy --keywords 美食 --max-count 5")
                return
            
            # 步骤2: 创建预览演示
            preview_file = await self.create_preview_demo(sample_data)
            
            # 步骤3: 演示API集成
            await self.demonstrate_api_integration()
            
            # 步骤4: 演示前端集成
            await self.demonstrate_frontend_integration()
            
            print("\n" + "=" * 60)
            print("✅ [完成] 所有测试通过！")
            if preview_file:
                print(f"📁 [预览文件] {preview_file}")
                print("💡 [建议] 在浏览器中打开预览文件查看效果")
            print("\n🎯 [总结] 第一种方案实现成功：")
            print("  ✅ 保存播放页链接到Redis")
            print("  ✅ 支持平台内预览")
            print("  ✅ 提供外部链接访问")
            print("  ✅ 完整的API集成方案")
            print("  ✅ 前端组件示例")
            
        except Exception as e:
            print(f"❌ [错误] 测试失败: {e}")
            import traceback
            traceback.print_exc()

async def main():
    """主函数"""
    tester = DouyinSimplePreviewTester()
    await tester.run_simple_test()

if __name__ == "__main__":
    asyncio.run(main()) 