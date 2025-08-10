# 青果代理查询同步解决方案

## 问题描述

用户使用query方法查询青果代理API：
```
https://longterm.proxy.qg.net/query?key=EEFECFB3&pwd=E169CFB91ACD
```

返回结果：
```json
{
    "code": "SUCCESS",
    "data": [
        {
            "server": "tunpool-tyk37.qg.net:19702",
            "area": "110100",
            "distinct": false
        }
    ],
    "request_id": "cc9f3fae-5064-4fb9-9bcc-9e7efe68e575"
}
```

但是系统显示可用代理数量为0，说明query API返回的代理信息没有正确同步到数据库。

## 解决方案

### 1. 新增代理同步功能

#### 1.1 核心方法
在 `proxy/qingguo_long_term_proxy.py` 中新增了两个方法：

```python
async def sync_proxies_from_query(self):
    """从query API同步代理信息到数据库"""
    # 调用query API获取当前代理
    # 解析返回的代理信息
    # 同步到数据库

async def _sync_proxy_to_db(self, proxy_data: dict):
    """将单个代理信息同步到数据库"""
    # 解析代理服务器地址
    # 创建代理信息对象
    # 保存到数据库
```

#### 1.2 API接口
新增API接口 `/api/v1/qingguo/sync-from-query`：

```python
@proxy_router.post("/qingguo/sync-from-query")
async def sync_qingguo_proxies_from_query():
    """从query API同步代理信息到数据库"""
    # 调用同步方法
    # 返回同步结果
```

#### 1.3 Web界面
在代理管理页面添加"同步代理信息"按钮：

```html
<button onclick="syncQingguoProxiesFromQuery()">同步代理信息</button>
```

### 2. 修复数据类型问题

修复了 `get_in_use_proxies` 方法中的数据类型错误：

```python
# 修复前
id=row.get('id'),

# 修复后  
id=str(row.get('id')),  # 确保id是字符串类型
```

### 3. 优化空闲数检查逻辑

#### 3.1 提取前检查
在 `extract_proxy` 方法中添加空闲数检查：

```python
# 首先检查通道空闲数
channels = await self.get_channels()
idle_count = channels.get("idle", 0)

# 如果空闲数为0，需要先删除一些现有代理
if idle_count == 0:
    await self._cleanup_old_proxies_for_extraction()
```

#### 3.2 批量提取限制
在批量提取API中添加数量限制：

```python
# 如果请求数量大于空闲数，调整提取数量
if count > idle_count:
    actual_count = min(count, idle_count)
else:
    actual_count = count
```

## 使用方法

### 1. 手动同步
点击Web界面中的"同步代理信息"按钮，系统会自动：
- 调用query API获取当前代理
- 解析代理信息
- 保存到数据库
- 显示同步结果

### 2. API调用
```bash
curl -X POST http://localhost:8000/api/v1/qingguo/sync-from-query
```

### 3. 程序调用
```python
from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager

proxy_manager = await get_qingguo_proxy_manager()
synced_proxies = await proxy_manager.sync_proxies_from_query()
```

## 测试验证

### 1. 同步测试
运行 `test_proxy_sync.py` 验证同步功能：

```bash
python test_proxy_sync.py
```

### 2. 提取测试
运行 `test_proxy_extraction.py` 验证提取功能：

```bash
python test_proxy_extraction.py
```

## 功能特点

### 1. 自动同步
- 支持从query API自动同步代理信息
- 自动解析代理服务器地址和认证信息
- 自动设置过期时间和状态

### 2. 智能清理
- 当空闲数为0时，自动清理旧代理
- 优先清理未使用的代理
- 按最后使用时间和创建时间排序

### 3. 数量限制
- 批量提取数量不能超过空闲数
- 自动调整提取数量
- 提供详细的错误提示

### 4. 数据一致性
- 确保数据库中的代理信息与API一致
- 修复数据类型问题
- 提供完整的错误处理

## 配置说明

### 1. 青果代理配置
在 `config/config_local.yaml` 中配置：

```yaml
qingguo_proxy:
  key: "EEFECFB3"
  pwd: "E169CFB91ACD"
  business_api_base: "https://longterm.proxy.qg.net"
```

### 2. 数据库配置
确保数据库连接正常，代理池表结构完整。

## 注意事项

1. **API限制**：query API可能有调用频率限制
2. **数据同步**：建议定期同步代理信息
3. **错误处理**：系统会记录详细的错误日志
4. **性能优化**：大量代理时考虑分批处理

## 后续优化

1. **定时同步**：添加定时任务自动同步代理信息
2. **增量同步**：只同步新增或变更的代理
3. **状态监控**：实时监控代理状态变化
4. **性能优化**：优化数据库查询和更新操作
