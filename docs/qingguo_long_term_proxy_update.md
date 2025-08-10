# 青果长效代理更新说明

## 更新概述

根据青果代理API的实际返回数据，我们对青果长效代理功能进行了重要更新，确保代理提取时只使用可用的区域。

## 主要更新内容

### 1. API资源查询优化

**更新前：**
- 使用基础API查询资源
- 参数格式不匹配实际API

**更新后：**
- 使用长效代理API查询资源：`https://longterm.proxy.qg.net/resources`
- 正确解析API返回的JSON格式数据
- 支持区域可用性检查

### 2. 区域可用性验证

新增功能：
- `get_available_regions()`: 获取可用的区域和运营商组合
- `is_region_available()`: 检查指定区域和运营商是否可用
- `get_random_available_region()`: 获取随机可用区域

### 3. 代理提取优化

**更新前：**
- 直接使用区域映射，不验证可用性
- 可能提取到不可用的区域

**更新后：**
- 提取前验证区域可用性
- 如果指定区域不可用，自动选择随机可用区域
- 使用API返回的准确区域编码

### 4. 区域映射更新

根据API返回的数据格式，更新了区域映射：

**省份映射更新：**
```python
# 更新前
"北京": "110000"
# 更新后  
"北京市市辖区": "110100"
```

**城市映射更新：**
```python
# 更新前
"北京": "110000"
# 更新后
"北京市市辖区": "110100"
```

### 5. 简化区域名称支持

新增简化区域名称映射，支持常用简称：
```python
simplified_mapping = {
    "北京": "北京市市辖区",
    "上海": "上海市市辖区",
    "广州": "广东省广州市",
    # ... 更多城市
}
```

## API数据结构

根据 [青果代理API](https://longterm.proxy.qg.net/resources?key=EEFECFB3&pwd=E169CFB91ACD) 返回的数据结构：

```json
{
  "code": "SUCCESS",
  "data": [
    {
      "area": "北京市市辖区",
      "area_code": 110100,
      "isp": "电信",
      "isp_code": 1,
      "available": true
    }
  ]
}
```

## 使用示例

### 1. 基本代理提取

```python
from proxy.qingguo_long_term_proxy import get_qingguo_proxy_manager

async def extract_proxy():
    manager = await get_qingguo_proxy_manager()
    
    # 提取代理（会自动验证区域可用性）
    proxy = await manager.extract_proxy(
        platform="xhs",
        account_id=1,
        region="北京",
        isp="电信"
    )
    
    if proxy:
        print(f"提取成功: {proxy.ip}:{proxy.port}")
```

### 2. 查询可用区域

```python
async def check_available_regions():
    manager = await get_qingguo_proxy_manager()
    
    # 获取所有可用区域
    available_regions = await manager.get_available_regions()
    
    for region, isps in available_regions.items():
        print(f"{region}: {[isp['isp'] for isp in isps]}")
```

### 3. 验证区域可用性

```python
async def verify_region():
    manager = await get_qingguo_proxy_manager()
    
    # 检查特定区域是否可用
    is_available = await manager.is_region_available("北京", "电信")
    print(f"北京电信: {'可用' if is_available else '不可用'}")
```

## 测试验证

### 1. 区域映射测试

```bash
conda activate mediacrawler
python test/test_region_mapping.py
```

### 2. 完整功能测试

```bash
conda activate mediacrawler
python test/test_qingguo_long_term_proxy.py
```

## 配置要求

### 环境变量

```bash
export QG_PROXY_KEY="your_qingguo_key_here"
export QG_PROXY_PWD="your_qingguo_pwd_here"  # 可选
```

### 配置文件

在 `config/config_local.yaml` 中配置：

```yaml
proxy:
  qingguo_key: "your_qingguo_key_here"
  qingguo_pwd: "your_qingguo_pwd_here"  # 可选
```

## 注意事项

1. **区域可用性**：提取代理前会自动验证区域可用性
2. **自动回退**：如果指定区域不可用，会自动选择随机可用区域
3. **编码匹配**：使用API返回的准确区域编码，确保提取成功
4. **错误处理**：完善的错误处理和日志记录

## 兼容性

- 保持向后兼容，现有代码无需修改
- 支持简化的区域名称（如"北京"、"上海"）
- 支持完整的区域名称（如"北京市市辖区"）

## 性能优化

- 缓存可用区域信息，避免重复API调用
- 智能区域选择，提高代理提取成功率
- 异步处理，支持高并发场景

## 故障排除

### 常见问题

1. **区域不可用**
   - 检查API返回的可用区域列表
   - 使用 `get_available_regions()` 查看当前可用区域

2. **编码不匹配**
   - 确保使用正确的区域名称格式
   - 检查区域映射配置

3. **API调用失败**
   - 验证Key和密码是否正确
   - 检查网络连接和API状态

### 调试方法

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 启用详细日志
utils.logger.setLevel(logging.DEBUG)
```

## 更新日志

- **v1.0.0**: 初始版本
- **v1.1.0**: 添加区域可用性验证
- **v1.2.0**: 优化API调用和错误处理
- **v1.3.0**: 更新区域映射，支持API格式
