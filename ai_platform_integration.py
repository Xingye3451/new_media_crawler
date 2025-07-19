# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  

"""
AI赋能平台集成示例
展示如何在AI赋能平台中调用MediaCrawler的登录验证功能
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
import httpx


class AIPlatformCrawlerClient:
    """AI赋能平台爬虫客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.current_session_id = None
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
    
    async def check_login_status(self, platform: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """检查登录状态"""
        url = f"{self.base_url}/api/v1/login/check"
        data = {
            "platform": platform,
            "session_id": session_id
        }
        
        response = await self.client.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    async def start_login_process(self, platform: str, login_type: str = "qrcode", 
                                session_id: Optional[str] = None) -> Dict[str, Any]:
        """启动登录流程"""
        url = f"{self.base_url}/api/v1/login/start"
        data = {
            "platform": platform,
            "login_type": login_type,
            "session_id": session_id
        }
        
        response = await self.client.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    async def wait_for_verification(self, session_id: str, timeout: int = 300) -> Dict[str, Any]:
        """等待验证完成"""
        url = f"{self.base_url}/api/v1/login/wait-verification"
        data = {
            "session_id": session_id,
            "timeout": timeout
        }
        
        response = await self.client.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    async def start_crawler_task(self, platform: str, **kwargs) -> Dict[str, Any]:
        """启动爬虫任务"""
        url = f"{self.base_url}/api/v1/crawler/start"
        data = {
            "platform": platform,
            "session_id": self.current_session_id,
            **kwargs
        }
        
        response = await self.client.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        url = f"{self.base_url}/api/v1/crawler/status/{task_id}"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()
    
    async def get_session_cookies(self, session_id: str) -> Dict[str, Any]:
        """获取会话cookies"""
        url = f"{self.base_url}/api/v1/login/sessions/{session_id}/cookies"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()


class AIPlatformIntegration:
    """AI赋能平台集成类"""
    
    def __init__(self, crawler_base_url: str = "http://localhost:8000"):
        self.crawler_client = AIPlatformCrawlerClient(crawler_base_url)
        self.platform_configs = {
            "xhs": {
                "name": "小红书",
                "login_types": ["qrcode", "phone"],
                "default_login_type": "qrcode"
            },
            "dy": {
                "name": "抖音",
                "login_types": ["qrcode", "phone"],
                "default_login_type": "qrcode"
            },
            "ks": {
                "name": "快手",
                "login_types": ["qrcode", "phone"],
                "default_login_type": "qrcode"
            }
        }
    
    async def ensure_login(self, platform: str, force_relogin: bool = False) -> Dict[str, Any]:
        """确保平台已登录"""
        print(f"[AI平台] 检查 {self.platform_configs[platform]['name']} 登录状态...")
        
        # 检查登录状态
        login_status = await self.crawler_client.check_login_status(platform)
        
        if login_status["status"] == "logged_in" and not force_relogin:
            print(f"[AI平台] {self.platform_configs[platform]['name']} 已登录")
            self.crawler_client.current_session_id = login_status["session_id"]
            return {
                "success": True,
                "message": "已登录",
                "session_id": login_status["session_id"],
                "verification_required": False
            }
        
        # 需要登录
        print(f"[AI平台] {self.platform_configs[platform]['name']} 需要登录")
        
        # 启动登录流程
        login_result = await self.crawler_client.start_login_process(
            platform=platform,
            login_type=self.platform_configs[platform]["default_login_type"]
        )
        
        if login_result["verification_required"]:
            # 需要手动验证
            verification_info = self._prepare_verification_ui(login_result)
            
            return {
                "success": False,
                "message": "需要手动验证",
                "verification_required": True,
                "verification_info": verification_info,
                "session_id": login_result["session_id"]
            }
        else:
            # 登录成功
            self.crawler_client.current_session_id = login_result["session_id"]
            return {
                "success": True,
                "message": "登录成功",
                "session_id": login_result["session_id"],
                "verification_required": False
            }
    
    def _prepare_verification_ui(self, login_result: Dict[str, Any]) -> Dict[str, Any]:
        """准备验证UI信息"""
        verification_type = login_result.get("verification_type")
        verification_data = login_result.get("verification_data", {})
        
        if verification_type == "qrcode":
            return {
                "type": "qrcode",
                "title": "扫描二维码登录",
                "description": "请使用手机扫描二维码完成登录",
                "qrcode_url": verification_data.get("qrcode_url"),
                "browser_url": verification_data.get("browser_url"),
                "instructions": [
                    "1. 打开手机上的对应APP",
                    "2. 扫描二维码",
                    "3. 在手机上确认登录",
                    "4. 等待验证完成"
                ]
            }
        elif verification_type == "sms":
            return {
                "type": "sms",
                "title": "手机验证码登录",
                "description": "请在浏览器中完成手机验证码登录",
                "browser_url": verification_data.get("browser_url"),
                "instructions": [
                    "1. 在浏览器中输入手机号",
                    "2. 获取验证码",
                    "3. 输入验证码完成登录",
                    "4. 等待验证完成"
                ]
            }
        else:
            return {
                "type": "manual",
                "title": "手动验证",
                "description": "请在浏览器中完成验证",
                "browser_url": verification_data.get("browser_url"),
                "instructions": [
                    "1. 在浏览器中完成验证",
                    "2. 等待验证完成"
                ]
            }
    
    async def wait_for_verification_completion(self, session_id: str, 
                                             timeout: int = 300) -> Dict[str, Any]:
        """等待验证完成"""
        print(f"[AI平台] 等待验证完成...")
        
        try:
            result = await self.crawler_client.wait_for_verification(session_id, timeout)
            
            if result["status"] == "success":
                print(f"[AI平台] 验证完成，登录成功")
                self.crawler_client.current_session_id = session_id
                return {
                    "success": True,
                    "message": "验证完成，登录成功",
                    "session_id": session_id,
                    "cookies": result.get("cookies"),
                    "local_storage": result.get("local_storage")
                }
            else:
                print(f"[AI平台] 验证失败: {result['message']}")
                return {
                    "success": False,
                    "message": result["message"],
                    "session_id": session_id
                }
                
        except Exception as e:
            print(f"[AI平台] 等待验证异常: {e}")
            return {
                "success": False,
                "message": f"等待验证异常: {e}",
                "session_id": session_id
            }
    
    async def start_crawling_with_login_check(self, platform: str, **kwargs) -> Dict[str, Any]:
        """启动爬取任务（带登录检查）"""
        print(f"[AI平台] 启动 {self.platform_configs[platform]['name']} 爬取任务...")
        
        # 确保已登录
        login_result = await self.ensure_login(platform)
        
        if not login_result["success"]:
            if login_result["verification_required"]:
                return {
                    "success": False,
                    "message": "需要手动验证",
                    "verification_required": True,
                    "verification_info": login_result["verification_info"],
                    "session_id": login_result["session_id"]
                }
            else:
                return {
                    "success": False,
                    "message": login_result["message"]
                }
        
        # 启动爬取任务
        try:
            task_result = await self.crawler_client.start_crawler_task(platform, **kwargs)
            
            return {
                "success": True,
                "message": "爬取任务已启动",
                "task_id": task_result["task_id"],
                "session_id": login_result["session_id"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"启动爬取任务失败: {e}"
            }
    
    async def monitor_task_progress(self, task_id: str, 
                                  check_interval: int = 5) -> Dict[str, Any]:
        """监控任务进度"""
        print(f"[AI平台] 监控任务进度: {task_id}")
        
        while True:
            try:
                status = await self.crawler_client.get_task_status(task_id)
                
                if status["status"] == "completed":
                    print(f"[AI平台] 任务完成")
                    return {
                        "success": True,
                        "message": "任务完成",
                        "result": status["result"]
                    }
                elif status["status"] == "failed":
                    print(f"[AI平台] 任务失败: {status['error']}")
                    return {
                        "success": False,
                        "message": f"任务失败: {status['error']}"
                    }
                elif status["status"] == "need_login":
                    print(f"[AI平台] 任务需要登录")
                    return {
                        "success": False,
                        "message": "需要登录",
                        "need_login": True,
                        "session_id": status.get("session_id")
                    }
                elif status["status"] == "need_verification":
                    print(f"[AI平台] 任务需要验证")
                    return {
                        "success": False,
                        "message": "需要验证",
                        "need_verification": True,
                        "session_id": status.get("session_id")
                    }
                else:
                    print(f"[AI平台] 任务状态: {status['status']}")
                    await asyncio.sleep(check_interval)
                    
            except Exception as e:
                print(f"[AI平台] 监控任务异常: {e}")
                await asyncio.sleep(check_interval)


# AI赋能平台前端集成示例
class AIPlatformFrontend:
    """AI赋能平台前端集成示例"""
    
    def __init__(self):
        self.integration = AIPlatformIntegration()
    
    async def handle_crawler_request(self, platform: str, keywords: str, 
                                   max_count: int = 100) -> Dict[str, Any]:
        """处理爬虫请求"""
        print(f"[前端] 收到爬虫请求: {platform} - {keywords}")
        
        # 启动爬取任务
        result = await self.integration.start_crawling_with_login_check(
            platform=platform,
            crawler_type="search",
            keywords=keywords,
            max_notes_count=max_count,
            save_data_option="db"
        )
        
        if not result["success"]:
            if result.get("verification_required"):
                # 需要验证，返回验证信息给前端
                return {
                    "type": "verification_required",
                    "message": result["message"],
                    "verification_info": result["verification_info"],
                    "session_id": result["session_id"]
                }
            else:
                # 其他错误
                return {
                    "type": "error",
                    "message": result["message"]
                }
        
        # 任务启动成功，开始监控
        task_id = result["task_id"]
        monitor_result = await self.integration.monitor_task_progress(task_id)
        
        if monitor_result["success"]:
            return {
                "type": "success",
                "message": "爬取完成",
                "result": monitor_result["result"]
            }
        else:
            if monitor_result.get("need_login"):
                # 需要重新登录
                return {
                    "type": "need_login",
                    "message": "需要重新登录",
                    "session_id": monitor_result["session_id"]
                }
            elif monitor_result.get("need_verification"):
                # 需要验证
                return {
                    "type": "need_verification",
                    "message": "需要验证",
                    "session_id": monitor_result["session_id"]
                }
            else:
                return {
                    "type": "error",
                    "message": monitor_result["message"]
                }
    
    async def handle_verification_completion(self, session_id: str) -> Dict[str, Any]:
        """处理验证完成"""
        print(f"[前端] 处理验证完成: {session_id}")
        
        result = await self.integration.wait_for_verification_completion(session_id)
        
        if result["success"]:
            return {
                "type": "success",
                "message": "验证完成，可以继续爬取",
                "session_id": session_id
            }
        else:
            return {
                "type": "error",
                "message": result["message"]
            }


# 使用示例
async def example_usage():
    """使用示例"""
    frontend = AIPlatformFrontend()
    
    # 示例1: 正常爬取流程
    print("=== 示例1: 正常爬取流程 ===")
    result = await frontend.handle_crawler_request("xhs", "美食", 50)
    print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 示例2: 需要验证的情况
    print("\n=== 示例2: 需要验证的情况 ===")
    result = await frontend.handle_crawler_request("dy", "旅游", 30)
    if result["type"] == "verification_required":
        print(f"需要验证: {result['verification_info']}")
        
        # 模拟用户完成验证
        print("用户完成验证...")
        verification_result = await frontend.handle_verification_completion(result["session_id"])
        print(f"验证结果: {verification_result}")
    
    # 关闭客户端
    await frontend.integration.crawler_client.close()


# 前端JavaScript集成示例
FRONTEND_JS_EXAMPLE = """
// AI赋能平台前端JavaScript集成示例

class MediaCrawlerClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async checkLoginStatus(platform, sessionId = null) {
        const response = await fetch(`${this.baseUrl}/api/v1/login/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform, session_id: sessionId })
        });
        return await response.json();
    }
    
    async startLoginProcess(platform, loginType = 'qrcode', sessionId = null) {
        const response = await fetch(`${this.baseUrl}/api/v1/login/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                platform, 
                login_type: loginType, 
                session_id: sessionId 
            })
        });
        return await response.json();
    }
    
    async waitForVerification(sessionId, timeout = 300) {
        const response = await fetch(`${this.baseUrl}/api/v1/login/wait-verification`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, timeout })
        });
        return await response.json();
    }
    
    async startCrawlerTask(platform, options = {}) {
        const response = await fetch(`${this.baseUrl}/api/v1/crawler/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform, ...options })
        });
        return await response.json();
    }
    
    async getTaskStatus(taskId) {
        const response = await fetch(`${this.baseUrl}/api/v1/crawler/status/${taskId}`);
        return await response.json();
    }
}

// 使用示例
async function handleCrawlerRequest(platform, keywords) {
    const client = new MediaCrawlerClient();
    
    try {
        // 检查登录状态
        const loginStatus = await client.checkLoginStatus(platform);
        
        if (loginStatus.status !== 'logged_in') {
            // 需要登录
            const loginResult = await client.startLoginProcess(platform);
            
            if (loginResult.verification_required) {
                // 显示验证UI
                showVerificationUI(loginResult);
                return;
            }
        }
        
        // 启动爬取任务
        const taskResult = await client.startCrawlerTask(platform, {
            crawler_type: 'search',
            keywords: keywords,
            max_notes_count: 100
        });
        
        // 监控任务进度
        monitorTaskProgress(taskResult.task_id);
        
    } catch (error) {
        console.error('爬虫请求失败:', error);
        showError('爬虫请求失败: ' + error.message);
    }
}

function showVerificationUI(loginResult) {
    const verificationInfo = loginResult.verification_info;
    
    if (verificationInfo.type === 'qrcode') {
        // 显示二维码
        showQRCodeModal(verificationInfo);
    } else if (verificationInfo.type === 'sms') {
        // 显示短信验证界面
        showSMSModal(verificationInfo);
    }
}

async function handleVerificationComplete(sessionId) {
    const client = new MediaCrawlerClient();
    
    try {
        const result = await client.waitForVerification(sessionId);
        
        if (result.status === 'success') {
            showSuccess('验证完成，可以继续爬取');
            // 继续之前的爬取任务
        } else {
            showError('验证失败: ' + result.message);
        }
    } catch (error) {
        showError('验证异常: ' + error.message);
    }
}

function showQRCodeModal(verificationInfo) {
    // 显示二维码模态框
    const modal = document.createElement('div');
    modal.className = 'verification-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>${verificationInfo.title}</h3>
            <p>${verificationInfo.description}</p>
            <img src="${verificationInfo.qrcode_url}" alt="登录二维码">
            <div class="instructions">
                ${verificationInfo.instructions.map(instruction => 
                    `<p>${instruction}</p>`
                ).join('')}
            </div>
            <button onclick="checkVerificationStatus()">检查验证状态</button>
        </div>
    `;
    document.body.appendChild(modal);
}

function showSMSModal(verificationInfo) {
    // 显示短信验证模态框
    const modal = document.createElement('div');
    modal.className = 'verification-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>${verificationInfo.title}</h3>
            <p>${verificationInfo.description}</p>
            <div class="instructions">
                ${verificationInfo.instructions.map(instruction => 
                    `<p>${instruction}</p>`
                ).join('')}
            </div>
            <a href="${verificationInfo.browser_url}" target="_blank">
                在浏览器中打开
            </a>
            <button onclick="checkVerificationStatus()">检查验证状态</button>
        </div>
    `;
    document.body.appendChild(modal);
}
"""

if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
    
    # 输出前端JavaScript示例
    print("\n=== 前端JavaScript集成示例 ===")
    print(FRONTEND_JS_EXAMPLE) 