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
API验证工具类
提供各平台登录状态的API验证功能
"""

import aiohttp
import asyncio
from typing import Dict, List, Any, Optional
from tools import utils
from constant.douyin import DOUYIN_AID, DOUYIN_SERVICE_NAME, DOUYIN_TTWID_CHECK_URL


class APILoginValidator:
    """API登录验证器"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    def _build_cookie_string(self, cookies: List[Dict[str, Any]]) -> str:
        """构建cookie字符串"""
        return "; ".join([f"{c['name']}={c['value']}" for c in cookies])
    
    async def verify_xhs_login(self, cookies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证小红书登录状态 - 使用未读消息接口"""
        try:
            cookie_str = self._build_cookie_string(cookies)
            
            # 小红书未读消息API - 更简单有效的验证方式
            url = "https://edith.xiaohongshu.com/api/sns/web/unread_count"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'Cookie': cookie_str,
                'Referer': 'https://www.xiaohongshu.com/',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin'
            }
            
            async with self.session.get(url, headers=headers, timeout=10) as response:
                response_text = await response.text()
                utils.logger.debug(f"小红书未读消息API响应状态: {response.status}")
                utils.logger.debug(f"小红书未读消息API响应内容: {response_text[:200]}")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        if data.get('code') == 0 and data.get('success') == True:
                            unread_data = data.get('data', {})
                            utils.logger.info(f"✅ 小红书登录验证成功！未读消息: {unread_data.get('unread_count', 0)}")
                            return {
                                "is_logged_in": True,
                                "message": "小红书未读消息API验证通过",
                                "user_info": {
                                    "unread_count": unread_data.get('unread_count', 0),
                                    "likes": unread_data.get('likes', 0),
                                    "connections": unread_data.get('connections', 0),
                                    "mentions": unread_data.get('mentions', 0),
                                    "platform": "xiaohongshu"
                                }
                            }
                        elif data.get('code') == -100:
                            utils.logger.warning(f"小红书登录已过期（code: {data.get('code')}）")
                            return {"is_logged_in": False, "message": "登录已过期"}
                        elif data.get('code') == -101:
                            utils.logger.warning(f"小红书无登录信息（code: {data.get('code')}）")
                            return {"is_logged_in": False, "message": "无登录信息"}
                        else:
                            utils.logger.warning(f"小红书API返回失败: {data}")
                            return {"is_logged_in": False, "message": f"小红书API验证失败: {data.get('msg', '未知错误')}"}
                    except Exception as e:
                        utils.logger.error(f"小红书API响应解析失败: {e}")
                        return {"is_logged_in": False, "message": "API响应解析失败"}
                elif response.status == 401:
                    utils.logger.warning("小红书登录已过期（401）")
                    return {"is_logged_in": False, "message": "登录已过期"}
                elif response.status == 403:
                    utils.logger.warning("小红书访问被拒绝（403）")
                    return {"is_logged_in": False, "message": "访问被拒绝"}
                else:
                    utils.logger.warning(f"小红书API请求失败，状态码: {response.status}")
                    return {"is_logged_in": False, "message": f"API请求失败: {response.status}"}
                    
        except aiohttp.ClientError as e:
            utils.logger.error(f"小红书API请求异常: {e}")
            return {"is_logged_in": False, "message": f"网络请求异常: {str(e)}"}
        except asyncio.TimeoutError:
            utils.logger.error("小红书API请求超时")
            return {"is_logged_in": False, "message": "请求超时"}
        except Exception as e:
            utils.logger.error(f"小红书登录验证失败: {e}")
            return {"is_logged_in": False, "message": f"验证失败: {str(e)}"}
    
    async def verify_douyin_login(self, cookies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证抖音登录状态 - 使用ttwid/check接口"""
        try:
            cookie_str = self._build_cookie_string(cookies)
            
            # 抖音登录验证API - 更简单有效的验证方式
            url = DOUYIN_TTWID_CHECK_URL
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'Cookie': cookie_str,
                'Referer': 'https://www.douyin.com/',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Content-Type': 'application/json'
            }
            
            # 固定参数
            payload = {
                "aid": DOUYIN_AID,
                "service": DOUYIN_SERVICE_NAME
            }
            
            async with self.session.post(url, headers=headers, json=payload, timeout=10) as response:
                response_text = await response.text()
                utils.logger.debug(f"抖音ttwid/check API响应状态: {response.status}")
                utils.logger.debug(f"抖音ttwid/check API响应内容: {response_text[:200]}")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        if data.get('status_code') == 0 and data.get('message') == 'check pass':
                            utils.logger.info(f"✅ 抖音登录验证成功！")
                            return {
                                "is_logged_in": True,
                                "message": "抖音ttwid/check API验证通过",
                                "user_info": {
                                    "platform": "douyin",
                                    "status": "logged_in",
                                    "sub_status_code": data.get('sub_status_code', 0)
                                }
                            }
                        else:
                            utils.logger.warning(f"抖音API返回失败: {data}")
                            return {"is_logged_in": False, "message": "抖音API验证失败"}
                    except Exception as e:
                        utils.logger.error(f"抖音API响应解析失败: {e}")
                        return {"is_logged_in": False, "message": "API响应解析失败"}
                elif response.status == 401:
                    utils.logger.warning("抖音登录已过期（401）")
                    return {"is_logged_in": False, "message": "登录已过期"}
                elif response.status == 403:
                    utils.logger.warning("抖音访问被拒绝（403）")
                    return {"is_logged_in": False, "message": "访问被拒绝"}
                else:
                    utils.logger.warning(f"抖音API请求失败，状态码: {response.status}")
                    return {"is_logged_in": False, "message": f"API请求失败: {response.status}"}
                    
        except aiohttp.ClientError as e:
            utils.logger.error(f"抖音API请求异常: {e}")
            return {"is_logged_in": False, "message": f"网络请求异常: {str(e)}"}
        except asyncio.TimeoutError:
            utils.logger.error("抖音API请求超时")
            return {"is_logged_in": False, "message": "请求超时"}
        except Exception as e:
            utils.logger.error(f"抖音登录验证失败: {e}")
            return {"is_logged_in": False, "message": f"验证失败: {str(e)}"}
    
    async def verify_kuaishou_login(self, cookies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证快手登录状态 - 使用checkLoginQuery GraphQL接口"""
        try:
            cookie_str = self._build_cookie_string(cookies)
            
            # 快手GraphQL API
            url = "https://www.kuaishou.com/graphql"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'Cookie': cookie_str,
                'Referer': 'https://www.kuaishou.com/',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Content-Type': 'application/json'
            }
            
            # 固定的GraphQL查询
            payload = {
                "operationName": "checkLoginQuery",
                "variables": {},
                "query": "query checkLoginQuery {\n  checkLogin\n}\n"
            }
            
            utils.logger.debug(f"快手checkLoginQuery请求参数: {payload}")
            
            async with self.session.post(url, headers=headers, json=payload, timeout=10) as response:
                response_text = await response.text()
                utils.logger.debug(f"快手checkLoginQuery API响应状态: {response.status}")
                utils.logger.debug(f"快手checkLoginQuery API响应内容: {response_text[:200]}")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        
                        # 检查返回结果
                        if (data.get('data') and 
                            'checkLogin' in data['data'] and 
                            data['data']['checkLogin'] is True):
                            
                            utils.logger.info(f"✅ 快手登录验证成功！checkLogin: {data['data']['checkLogin']}")
                            return {
                                "is_logged_in": True,
                                "message": "快手checkLoginQuery API验证通过",
                                "user_info": {
                                    "platform": "kuaishou",
                                    "status": "logged_in",
                                    "check_login": data['data']['checkLogin']
                                }
                            }
                        else:
                            utils.logger.warning(f"快手checkLoginQuery API返回失败: {data}")
                            return {"is_logged_in": False, "message": "快手checkLoginQuery API验证失败"}
                    except Exception as e:
                        utils.logger.error(f"快手checkLoginQuery API响应解析失败: {e}")
                        return {"is_logged_in": False, "message": "API响应解析失败"}
                elif response.status == 401:
                    utils.logger.warning("快手登录已过期（401）")
                    return {"is_logged_in": False, "message": "登录已过期"}
                elif response.status == 403:
                    utils.logger.warning("快手访问被拒绝（403）")
                    return {"is_logged_in": False, "message": "访问被拒绝"}
                else:
                    utils.logger.warning(f"快手checkLoginQuery API请求失败，状态码: {response.status}")
                    return {"is_logged_in": False, "message": f"API请求失败: {response.status}"}
                    
        except aiohttp.ClientError as e:
            utils.logger.error(f"快手checkLoginQuery API请求异常: {e}")
            return {"is_logged_in": False, "message": f"网络请求异常: {str(e)}"}
        except asyncio.TimeoutError:
            utils.logger.error("快手checkLoginQuery API请求超时")
            return {"is_logged_in": False, "message": "请求超时"}
        except Exception as e:
            utils.logger.error(f"快手登录验证失败: {e}")
            return {"is_logged_in": False, "message": f"验证失败: {str(e)}"}
    
    async def verify_bilibili_login(self, cookies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证B站登录状态"""
        try:
            cookie_str = self._build_cookie_string(cookies)
            
            # B站用户信息API
            url = "https://api.bilibili.com/x/web-interface/nav"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'Cookie': cookie_str,
                'Referer': 'https://www.bilibili.com/',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            async with self.session.get(url, headers=headers, timeout=10) as response:
                response_text = await response.text()
                utils.logger.debug(f"B站API响应状态: {response.status}")
                utils.logger.debug(f"B站API响应内容: {response_text[:200]}")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        if data.get('code') == 0 and data.get('data'):
                            user_data = data['data']
                            utils.logger.info(f"✅ B站登录验证成功！用户: {user_data.get('uname', '未知')}")
                            return {
                                "is_logged_in": True,
                                "message": "B站API验证通过",
                                "user_info": {
                                    "nickname": user_data.get('uname'),
                                    "user_id": user_data.get('mid'),
                                    "avatar": user_data.get('face'),
                                    "level": user_data.get('level_info', {}).get('current_level'),
                                    "vip_type": user_data.get('vipType')
                                }
                            }
                        else:
                            utils.logger.warning(f"B站API返回失败: {data}")
                            return {"is_logged_in": False, "message": "B站API验证失败"}
                    except Exception as e:
                        utils.logger.error(f"B站API响应解析失败: {e}")
                        return {"is_logged_in": False, "message": "API响应解析失败"}
                elif response.status == 401:
                    utils.logger.warning("B站登录已过期（401）")
                    return {"is_logged_in": False, "message": "登录已过期"}
                elif response.status == 403:
                    utils.logger.warning("B站访问被拒绝（403）")
                    return {"is_logged_in": False, "message": "访问被拒绝"}
                else:
                    utils.logger.warning(f"B站API请求失败，状态码: {response.status}")
                    return {"is_logged_in": False, "message": f"API请求失败: {response.status}"}
                    
        except aiohttp.ClientError as e:
            utils.logger.error(f"B站API请求异常: {e}")
            return {"is_logged_in": False, "message": f"网络请求异常: {str(e)}"}
        except asyncio.TimeoutError:
            utils.logger.error("B站API请求超时")
            return {"is_logged_in": False, "message": "请求超时"}
        except Exception as e:
            utils.logger.error(f"B站登录验证失败: {e}")
            return {"is_logged_in": False, "message": f"验证失败: {str(e)}"}


# 便捷函数
async def verify_login_by_api(platform: str, cookies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """通过API验证登录状态"""
    async with APILoginValidator() as validator:
        if platform == "xhs":
            return await validator.verify_xhs_login(cookies)
        elif platform == "dy":
            return await validator.verify_douyin_login(cookies)
        elif platform == "ks":
            return await validator.verify_kuaishou_login(cookies)
        elif platform == "bili":
            return await validator.verify_bilibili_login(cookies)
        else:
            return {"is_logged_in": False, "message": f"不支持的平台: {platform}"}
