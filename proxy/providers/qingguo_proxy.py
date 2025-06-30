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
# @Desc    : 青果代理HTTP实现，官方文档：https://www.qg.net/doc/2145.html
import os
import re
from typing import Dict, List

import httpx
from pydantic import BaseModel, Field

from proxy import IpCache, IpInfoModel, ProxyProvider
from proxy.types import ProviderNameEnum
from tools import utils


class QingguoProxyModel(BaseModel):
    ip: str = Field("ip")
    port: int = Field("端口")
    expire_ts: int = Field("过期时间")


def parse_qingguo_proxy(proxy_info: str) -> QingguoProxyModel:
    """
    解析青果代理的IP信息
    格式：ip:port,expire_timestamp
    Args:
        proxy_info: 代理信息字符串

    Returns:
        QingguoProxyModel: 解析后的代理模型

    """
    pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5}),(\d+)'
    match = re.search(pattern, proxy_info)
    if not match or not match.groups():
        raise Exception("not match qingguo proxy info")

    return QingguoProxyModel(
        ip=match.groups()[0],
        port=int(match.groups()[1]),
        expire_ts=int(match.groups()[2])
    )


class QingguoProxy(ProxyProvider):
    def __init__(self, qg_key: str, qg_pwd: str = None):
        """
        青果代理初始化
        Args:
            qg_key: 青果代理的Key
            qg_pwd: 青果代理的密码（可选）
        """
        self.qg_key = qg_key
        self.qg_pwd = qg_pwd
        self.api_base = "https://proxy.qg.net/"
        self.ip_cache = IpCache()
        self.proxy_brand_name = ProviderNameEnum.QINGGUO_PROVIDER.value
        self.params = {
            "Key": self.qg_key,
            "format": "json",
            "sep": 1,
        }
        if self.qg_pwd:
            self.params["Pwd"] = self.qg_pwd

    async def get_proxies(self, num: int) -> List[IpInfoModel]:
        """
        青果代理实现 - 短效代理（弹性提取）
        Args:
            num: 需要获取的代理数量

        Returns:
            List[IpInfoModel]: 代理IP列表

        """
        uri = "allocate"

        # 优先从缓存中拿 IP
        ip_cache_list = self.ip_cache.load_all_ip(proxy_brand_name=self.proxy_brand_name)
        if len(ip_cache_list) >= num:
            return ip_cache_list[:num]

        # 如果缓存中的数量不够，从IP代理商获取补上，再存入缓存中
        need_get_count = num - len(ip_cache_list)
        self.params.update({"num": need_get_count})

        ip_infos: List[IpInfoModel] = []
        async with httpx.AsyncClient() as client:
            response = await client.get(self.api_base + uri, params=self.params)

            if response.status_code != 200:
                utils.logger.error(f"[QingguoProxy.get_proxies] status code not 200 and response.txt:{response.text}")
                raise Exception("get ip error from proxy provider and status code not 200 ...")

            # 青果代理返回的是纯文本格式，每行一个代理
            proxy_text = response.text.strip()
            if not proxy_text:
                utils.logger.error(f"[QingguoProxy.get_proxies] empty response")
                raise Exception("get ip error from proxy provider and empty response ...")

            # 检查是否返回错误信息
            if proxy_text.startswith("error"):
                utils.logger.error(f"[QingguoProxy.get_proxies] error response: {proxy_text}")
                raise Exception(f"get ip error from proxy provider: {proxy_text}")

            proxy_list = proxy_text.split("\n")
            for proxy in proxy_list:
                if not proxy.strip():
                    continue
                try:
                    proxy_model = parse_qingguo_proxy(proxy.strip())
                    ip_info_model = IpInfoModel(
                        ip=proxy_model.ip,
                        port=proxy_model.port,
                        user=self.qg_key,  # 青果代理使用Key作为用户名
                        password=self.qg_pwd or "",  # 密码可能为空
                        expired_time_ts=proxy_model.expire_ts,
                    )
                    ip_key = f"{self.proxy_brand_name}_{ip_info_model.ip}_{ip_info_model.port}"
                    self.ip_cache.set_ip(ip_key, ip_info_model.model_dump_json(), ex=ip_info_model.expired_time_ts)
                    ip_infos.append(ip_info_model)
                except Exception as e:
                    utils.logger.error(f"[QingguoProxy.get_proxies] parse proxy error: {proxy}, error: {e}")
                    continue

        return ip_cache_list + ip_infos

    async def release_proxy(self, proxy_ip: str, proxy_port: int) -> bool:
        """
        释放代理IP
        Args:
            proxy_ip: 代理IP
            proxy_port: 代理端口

        Returns:
            bool: 是否释放成功

        """
        uri = "release"
        release_params = {
            "Key": self.qg_key,
            "ip": proxy_ip,
            "port": proxy_port
        }
        if self.qg_pwd:
            release_params["Pwd"] = self.qg_pwd

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.api_base + uri, params=release_params)
                if response.status_code == 200:
                    result = response.text.strip()
                    if result == "success":
                        utils.logger.info(f"[QingguoProxy.release_proxy] release proxy {proxy_ip}:{proxy_port} success")
                        return True
                    else:
                        utils.logger.error(f"[QingguoProxy.release_proxy] release proxy failed: {result}")
                        return False
                else:
                    utils.logger.error(f"[QingguoProxy.release_proxy] release proxy status code not 200: {response.status_code}")
                    return False
        except Exception as e:
            utils.logger.error(f"[QingguoProxy.release_proxy] release proxy exception: {e}")
            return False

    async def get_balance(self) -> float:
        """
        获取账户余额
        Returns:
            float: 账户余额

        """
        uri = "query"
        balance_params = {"Key": self.qg_key}
        if self.qg_pwd:
            balance_params["Pwd"] = self.qg_pwd

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.api_base + uri, params=balance_params)
                if response.status_code == 200:
                    result = response.text.strip()
                    try:
                        balance = float(result)
                        utils.logger.info(f"[QingguoProxy.get_balance] current balance: {balance}")
                        return balance
                    except ValueError:
                        utils.logger.error(f"[QingguoProxy.get_balance] invalid balance format: {result}")
                        return 0.0
                else:
                    utils.logger.error(f"[QingguoProxy.get_balance] query balance status code not 200: {response.status_code}")
                    return 0.0
        except Exception as e:
            utils.logger.error(f"[QingguoProxy.get_balance] query balance exception: {e}")
            return 0.0


def new_qingguo_proxy() -> QingguoProxy:
    """
    构造青果代理HTTP实例
    Returns:
        QingguoProxy: 青果代理实例

    """
    return QingguoProxy(
        qg_key=os.getenv("qg_key", "你的青果代理Key"),
        qg_pwd=os.getenv("qg_pwd", ""),  # 青果代理密码可选
    )
