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
Cookie有效期分析工具
分析各平台登录cookies的有效期和重要性
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from tools import utils


class CookieAnalyzer:
    """Cookie分析器"""
    
    def __init__(self):
        # 各平台Cookie有效期配置
        self.cookie_expiry_config = {
            "xhs": {
                "a1": {"type": "long_term", "expiry_days": 365, "importance": "critical"},
                "web_session": {"type": "session", "expiry_days": 7, "importance": "critical"},
                "unread": {"type": "medium_term", "expiry_days": 30, "importance": "high"},
                "webId": {"type": "long_term", "expiry_days": 365, "importance": "medium"},
                "xsecappid": {"type": "fixed", "expiry_days": None, "importance": "low"},
                "websectiga": {"type": "session", "expiry_days": 1, "importance": "medium"},
                "sec_poison_id": {"type": "session", "expiry_days": 1, "importance": "low"},
                "gid": {"type": "session", "expiry_days": 1, "importance": "low"},
                "webBuild": {"type": "fixed", "expiry_days": None, "importance": "low"},
                "loadts": {"type": "session", "expiry_days": 1, "importance": "low"},
                "acw_tc": {"type": "session", "expiry_days": 1, "importance": "low"},
                "abRequestId": {"type": "session", "expiry_days": 1, "importance": "low"}
            },
            "dy": {
                "passport_csrf_token": {"type": "session", "expiry_days": 1, "importance": "critical"},
                "passport_csrf_token_default": {"type": "session", "expiry_days": 1, "importance": "critical"},
                "ttwid": {"type": "long_term", "expiry_days": 365, "importance": "critical"},
                "LOGIN_STATUS": {"type": "session", "expiry_days": 1, "importance": "high"},
                "douyin.com": {"type": "session", "expiry_days": 1, "importance": "medium"}
            },
            "ks": {
                "passToken": {"type": "long_term", "expiry_days": 365, "importance": "critical"},
                "userId": {"type": "long_term", "expiry_days": 365, "importance": "critical"},
                "kuaishou.server.webday7_st": {"type": "session", "expiry_days": 7, "importance": "high"},
                "kuaishou.server.webday7_ph": {"type": "session", "expiry_days": 7, "importance": "high"}
            },
            "bili": {
                "SESSDATA": {"type": "long_term", "expiry_days": 365, "importance": "critical"},
                "DedeUserID": {"type": "long_term", "expiry_days": 365, "importance": "critical"},
                "bili_jct": {"type": "long_term", "expiry_days": 365, "importance": "critical"},
                "sid": {"type": "session", "expiry_days": 1, "importance": "medium"}
            }
        }
    
    def analyze_cookies(self, platform: str, cookies: Dict[str, str]) -> Dict[str, Any]:
        """
        分析cookies的有效期和重要性
        
        Args:
            platform: 平台名称
            cookies: cookies字典
            
        Returns:
            分析结果
        """
        if platform not in self.cookie_expiry_config:
            return {"error": f"不支持的平台: {platform}"}
        
        config = self.cookie_expiry_config[platform]
        analysis_result = {
            "platform": platform,
            "total_cookies": len(cookies),
            "critical_cookies": [],
            "high_importance_cookies": [],
            "medium_importance_cookies": [],
            "low_importance_cookies": [],
            "unknown_cookies": [],
            "estimated_expiry": None,
            "login_strength": "unknown"
        }
        
        # 分析每个cookie
        for cookie_name, cookie_value in cookies.items():
            if cookie_name in config:
                cookie_info = config[cookie_name]
                importance = cookie_info["importance"]
                expiry_days = cookie_info["expiry_days"]
                
                cookie_analysis = {
                    "name": cookie_name,
                    "value_length": len(cookie_value),
                    "importance": importance,
                    "type": cookie_info["type"],
                    "expiry_days": expiry_days,
                    "is_valid": len(cookie_value) > 10  # 简单有效性检查
                }
                
                if importance == "critical":
                    analysis_result["critical_cookies"].append(cookie_analysis)
                elif importance == "high":
                    analysis_result["high_importance_cookies"].append(cookie_analysis)
                elif importance == "medium":
                    analysis_result["medium_importance_cookies"].append(cookie_analysis)
                elif importance == "low":
                    analysis_result["low_importance_cookies"].append(cookie_analysis)
            else:
                # 未知cookie
                analysis_result["unknown_cookies"].append({
                    "name": cookie_name,
                    "value_length": len(cookie_value),
                    "importance": "unknown",
                    "type": "unknown",
                    "expiry_days": None,
                    "is_valid": len(cookie_value) > 5
                })
        
        # 计算预估有效期
        analysis_result["estimated_expiry"] = self._calculate_estimated_expiry(analysis_result)
        
        # 计算登录强度
        analysis_result["login_strength"] = self._calculate_login_strength(analysis_result)
        
        return analysis_result
    
    def _calculate_estimated_expiry(self, analysis_result: Dict[str, Any]) -> Optional[str]:
        """计算预估有效期"""
        critical_cookies = analysis_result["critical_cookies"]
        high_cookies = analysis_result["high_importance_cookies"]
        
        if not critical_cookies and not high_cookies:
            return None
        
        # 找到最短的有效期
        min_expiry_days = float('inf')
        for cookies in [critical_cookies, high_cookies]:
            for cookie in cookies:
                if cookie["expiry_days"] and cookie["expiry_days"] < min_expiry_days:
                    min_expiry_days = cookie["expiry_days"]
        
        if min_expiry_days == float('inf'):
            return None
        
        # 计算预估过期时间
        estimated_expiry = datetime.now() + timedelta(days=min_expiry_days)
        return estimated_expiry.strftime("%Y-%m-%d %H:%M:%S")
    
    def _calculate_login_strength(self, analysis_result: Dict[str, Any]) -> str:
        """计算登录强度"""
        critical_count = len([c for c in analysis_result["critical_cookies"] if c["is_valid"]])
        high_count = len([c for c in analysis_result["high_importance_cookies"] if c["is_valid"]])
        medium_count = len([c for c in analysis_result["medium_importance_cookies"] if c["is_valid"]])
        
        if critical_count >= 2:
            return "strong"
        elif critical_count >= 1 and high_count >= 1:
            return "medium"
        elif critical_count >= 1 or (high_count >= 2):
            return "weak"
        else:
            return "invalid"
    
    def get_cookie_importance_summary(self, platform: str) -> Dict[str, Any]:
        """获取平台cookie重要性总结"""
        if platform not in self.cookie_expiry_config:
            return {"error": f"不支持的平台: {platform}"}
        
        config = self.cookie_expiry_config[platform]
        summary = {
            "platform": platform,
            "critical_cookies": [],
            "high_importance_cookies": [],
            "medium_importance_cookies": [],
            "low_importance_cookies": []
        }
        
        for cookie_name, cookie_info in config.items():
            importance = cookie_info["importance"]
            cookie_summary = {
                "name": cookie_name,
                "type": cookie_info["type"],
                "expiry_days": cookie_info["expiry_days"],
                "description": self._get_cookie_description(platform, cookie_name)
            }
            
            if importance == "critical":
                summary["critical_cookies"].append(cookie_summary)
            elif importance == "high":
                summary["high_importance_cookies"].append(cookie_summary)
            elif importance == "medium":
                summary["medium_importance_cookies"].append(cookie_summary)
            elif importance == "low":
                summary["low_importance_cookies"].append(cookie_summary)
        
        return summary
    
    def _get_cookie_description(self, platform: str, cookie_name: str) -> str:
        """获取cookie描述"""
        descriptions = {
            "xhs": {
                "a1": "用户身份标识，长期有效",
                "web_session": "会话标识，短期有效",
                "unread": "用户状态标识，包含用户ID信息",
                "webId": "设备标识，长期有效",
                "xsecappid": "应用标识，固定值"
            },
            "dy": {
                "passport_csrf_token": "CSRF令牌，防止跨站请求伪造",
                "ttwid": "用户身份标识，长期有效",
                "LOGIN_STATUS": "登录状态标识"
            },
            "ks": {
                "passToken": "用户身份令牌，长期有效",
                "userId": "用户ID，长期有效",
                "kuaishou.server.webday7_st": "会话令牌，短期有效",
                "kuaishou.server.webday7_ph": "会话令牌，短期有效"
            },
            "bili": {
                "SESSDATA": "会话数据，长期有效",
                "DedeUserID": "用户ID，长期有效",
                "bili_jct": "CSRF令牌，长期有效"
            }
        }
        
        return descriptions.get(platform, {}).get(cookie_name, "未知用途")


# 便捷函数
def analyze_platform_cookies(platform: str, cookies: Dict[str, str]) -> Dict[str, Any]:
    """分析平台cookies"""
    analyzer = CookieAnalyzer()
    return analyzer.analyze_cookies(platform, cookies)


def get_platform_cookie_summary(platform: str) -> Dict[str, Any]:
    """获取平台cookie总结"""
    analyzer = CookieAnalyzer()
    return analyzer.get_cookie_importance_summary(platform)
