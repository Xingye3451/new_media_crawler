# 青果代理重新设计说明

## 更新概述

根据用户反馈，我们对青果代理系统进行了重大重新设计，主要目标是：

1. **移除需要登录token的功能**（如余额查询）
2. **更新通道查询API**，使用正确的接口
3. **代理与平台解耦**，所有平台通用
4. **重新设计代理管理**，支持启用/禁用功能

## 主要更新内容

### 1. 移除余额查询功能

**原因：** 余额查询需要登录token和cookie，无法通过API Key直接获取

**更新内容：**
- 移除 `get_balance()` 方法的实际API调用
- 返回默认值并提示需要登录token
- 从Web界面移除余额显示

### 2. 更新通道查询API

**更新前：** 使用错误的API端点
**更新后：** 使用正确的API：`https://longterm.proxy.qg.net/channels`

**API返回格式：**
```json
{
    "code": "SUCCESS",
    "data": {
        "total": 1,
        "idle": 0
    }
}
```

**更新内容：**
- 更新 `get_channels()` 方法返回字典格式
- 包含总数、空闲数、使用中数量
- Web界面显示详细的通道状态信息

### 3. 代理与平台解耦

**设计理念：** 代理作为通用资源，不再与特定平台绑定

**更新内容：**

#### 3.1 数据模型更新
```python
class ProxyInfo(BaseModel):
    # 移除字段
    platform: Optional[str] = None      # 删除
    account_id: Optional[int] = None    # 删除
    
    # 新增字段
    enabled: bool = True                # 是否启用
    speed: Optional[int] = None         # 速度(ms)
    description: Optional[str] = None   # 描述信息
```

#### 3.2 代理状态枚举更新
```python
class ProxyStatus(str, Enum):
    ACTIVE = "active"           # 活跃
    EXPIRED = "expired"         # 已过期
    FAILED = "failed"           # 失败
    ROTATING = "rotating"       # 轮换中
    DISABLED = "disabled"       # 已禁用 (新增)
```

#### 3.3 方法签名更新
```python
# 更新前
async def extract_proxy(self, platform: str = None, account_id: int = None, region: str = "北京", isp: str = "电信")

# 更新后
async def extract_proxy(self, region: str = "北京", isp: str = "电信", description: str = None)

# 更新前
async def get_proxy_for_platform(self, platform: str, account_id: int = None)

# 更新后
async def get_available_proxy(self)
```

### 4. 新增代理管理功能

#### 4.1 启用/禁用代理
```python
async def enable_proxy(self, proxy_id: str) -> bool
async def disable_proxy(self, proxy_id: str) -> bool
```

#### 4.2 代理速度测试
```python
async def test_proxy_speed(self, proxy_id: str) -> dict
```

### 5. Web界面重新设计

#### 5.1 移除功能
- 余额显示
- 平台筛选器
- 账号ID筛选器

#### 5.2 新增功能
- 启用状态筛选器
- 区域筛选器
- 代理启用/禁用按钮
- 区域和描述信息显示

#### 5.3 表格列更新
```
更新前: 代理ID | IP | 端口 | 类型 | 平台 | 提供商 | 状态 | 速度 | 成功率 | 使用次数 | 最后使用 | 操作
更新后: 代理ID | IP | 端口 | 类型 | 提供商 | 状态 | 启用 | 速度 | 成功率 | 使用次数 | 区域 | 描述 | 操作
```

### 6. 青果代理面板更新

#### 6.1 账户信息区域
- 移除余额显示
- 更新通道状态显示（总数/空闲/使用中）
- 显示可用资源地区数量
- 显示可用代理数量

#### 6.2 代理操作区域
- 移除平台选择
- 添加区域和运营商选择
- 添加描述信息输入
- 限制批量提取数量（最大10个）

## 技术实现细节

### 1. 数据库字段更新

需要更新 `proxy_pool` 表结构：

```sql
-- 移除字段
ALTER TABLE proxy_pool DROP COLUMN platform;
ALTER TABLE proxy_pool DROP COLUMN account_id;

-- 新增字段
ALTER TABLE proxy_pool ADD COLUMN enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE proxy_pool ADD COLUMN speed INT;
ALTER TABLE proxy_pool ADD COLUMN description TEXT;
```

### 2. API接口更新

#### 2.1 通道查询接口
```python
# 返回格式
{
    "success": True,
    "channels": {
        "total": 1,
        "idle": 0,
        "in_use": 1
    }
}
```

#### 2.2 代理提取接口
```python
# 请求参数
{
    "region": "北京",
    "isp": "电信", 
    "description": "测试代理"
}

# 返回格式
{
    "success": True,
    "proxy": {
        "ip": "192.168.1.1",
        "port": 8080,
        "area": "北京市市辖区",
        "description": "青果代理 - 北京 电信"
    }
}
```

### 3. 通道数量限制

根据API返回的通道信息，系统会：
- 检查可用通道数量
- 限制提取数量不超过空闲通道数
- 避免超出限制导致代理失效

## 使用方式

### 1. 基本代理提取
```python
from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager

async def extract_proxy():
    manager = await get_qingguo_proxy_manager()
    
    # 提取代理（不再需要平台参数）
    proxy = await manager.extract_proxy(
        region="北京",
        isp="电信",
        description="测试代理"
    )
```

### 2. 获取可用代理
```python
async def get_proxy():
    manager = await get_qingguo_proxy_manager()
    
    # 获取可用代理（所有平台通用）
    proxy = await manager.get_available_proxy()
```

### 3. 代理管理
```python
async def manage_proxy():
    manager = await get_qingguo_proxy_manager()
    
    # 启用代理
    await manager.enable_proxy(proxy_id)
    
    # 禁用代理
    await manager.disable_proxy(proxy_id)
    
    # 测试速度
    result = await manager.test_proxy_speed(proxy_id)
```

## 兼容性说明

### 1. 向后兼容
- 保持现有API接口的基本结构
- 现有代码无需大幅修改
- 逐步迁移到新的代理管理方式

### 2. 数据库迁移
- 需要执行数据库结构更新
- 现有数据会自动适配新结构
- 建议在测试环境先验证

### 3. 配置更新
- 无需更新配置文件
- 环境变量保持不变
- API Key和密码继续使用

## 测试验证

### 1. 功能测试
```bash
# 测试区域映射
python test/test_region_mapping.py

# 测试青果代理功能
python test/test_qingguo_long_term_proxy.py
```

### 2. Web界面测试
- 访问代理管理页面
- 测试青果代理面板
- 验证启用/禁用功能
- 检查筛选器工作正常

## 注意事项

1. **通道限制**：提取代理数量不能超过可用通道数
2. **余额查询**：需要登录token，暂时无法通过API获取
3. **平台解耦**：代理不再与特定平台绑定，所有平台通用
4. **启用状态**：新增启用/禁用功能，可以灵活控制代理使用

## 更新日志

- **v1.4.0**: 移除余额查询，更新通道API
- **v1.5.0**: 代理与平台解耦，支持启用/禁用
- **v1.6.0**: 重新设计Web界面，优化用户体验
