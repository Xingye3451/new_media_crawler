# 爬虫错误处理和重试机制使用指南

## 概述

本系统实现了完善的爬虫错误处理和重试机制，能够自动处理权限丢失、验证码、频率限制等常见问题，支持账号切换和智能重试。

## 核心功能

### 1. 错误类型检测

系统能够自动检测以下错误类型：

- **权限丢失** (`PERMISSION_DENIED`): 检测到403状态码或权限相关错误
- **验证码要求** (`CAPTCHA_REQUIRED`): 检测到471/461状态码或验证码相关错误
- **频率限制** (`RATE_LIMITED`): 检测到429状态码或频率限制错误
- **需要登录** (`LOGIN_REQUIRED`): 检测到登录状态失效
- **账号被封** (`ACCOUNT_BLOCKED`): 检测到账号被封禁
- **网络错误** (`NETWORK_ERROR`): 检测到网络连接问题
- **未知错误** (`UNKNOWN_ERROR`): 其他未分类错误

### 2. 智能重试机制

- **指数退避**: 重试延迟时间按指数增长
- **随机抖动**: 避免多个请求同时重试
- **最大重试次数**: 默认3次，可配置
- **错误类型过滤**: 某些错误类型不进行重试

### 3. 账号切换功能

- **自动账号切换**: 遇到权限或登录问题时自动切换账号
- **账号池管理**: 从数据库加载可用账号列表
- **智能选择**: 根据登录状态和成功率选择最佳账号
- **切换限制**: 防止无限切换账号

### 4. 错误处理流程

```
错误发生 → 错误类型检测 → 决定处理策略 → 执行处理 → 记录日志
    ↓
权限丢失/登录失效 → 尝试切换账号 → 重试操作
    ↓
验证码/频率限制 → 等待延迟 → 重试操作
    ↓
账号被封 → 切换账号 → 重试操作
    ↓
达到最大重试次数 → 终止操作 → 记录失败
```

## 使用方法

### 1. 基本使用

```python
from utils.crawler_error_handler import create_error_handler, RetryConfig

# 创建错误处理器
retry_config = RetryConfig(
    max_retries=3,
    base_delay=2.0,
    max_delay=30.0,
    account_switch_enabled=True,
    max_account_switches=3
)

error_handler = await create_error_handler("xhs", "task_id", retry_config)
```

### 2. 使用重试包装器

```python
from utils.crawler_error_handler import RetryableCrawlerOperation

async def my_crawler_operation():
    # 你的爬虫操作
    return await crawler.search_by_keywords(...)

# 使用重试包装器
retry_op = RetryableCrawlerOperation(error_handler)
results = await retry_op.execute(my_crawler_operation)
```

### 3. 便捷函数

```python
from utils.crawler_error_handler import execute_with_retry

# 直接执行带重试的操作
results = await execute_with_retry(
    platform="xhs",
    operation=my_crawler_operation,
    task_id="task_123"
)
```

## 配置选项

### RetryConfig 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_retries` | int | 3 | 最大重试次数 |
| `base_delay` | float | 2.0 | 基础延迟时间（秒） |
| `max_delay` | float | 30.0 | 最大延迟时间（秒） |
| `exponential_base` | float | 2.0 | 指数退避基数 |
| `jitter` | bool | True | 是否添加随机抖动 |
| `account_switch_enabled` | bool | True | 是否启用账号切换 |
| `max_account_switches` | int | 3 | 最大账号切换次数 |

## 错误处理策略

### 1. 权限丢失处理

- **检测**: 403状态码或权限相关错误消息
- **处理**: 尝试切换账号，如果失败则终止
- **重试**: 切换账号后重试操作

### 2. 验证码处理

- **检测**: 471/461状态码或验证码相关错误
- **处理**: 等待延迟后重试，考虑切换账号
- **重试**: 最多重试3次

### 3. 频率限制处理

- **检测**: 429状态码或频率限制错误
- **处理**: 增加延迟时间后重试
- **重试**: 使用指数退避策略

### 4. 登录失效处理

- **检测**: 登录状态相关错误
- **处理**: 尝试切换账号
- **重试**: 切换账号后重试

### 5. 账号被封处理

- **检测**: 账号封禁相关错误
- **处理**: 立即切换账号
- **重试**: 使用新账号重试

## 日志记录

系统会自动记录详细的错误信息：

```
[ERROR_HANDLER_xhs] permission_denied: 权限丢失，需要重新登录
[ERROR_HANDLER_xhs] Task: task_123, Account: account_456
[ERROR_HANDLER_xhs] 等待 4.00 秒后重试 (第 2 次)
[ERROR_HANDLER_xhs] 切换到账号: 测试账号 (ID: account_789)
```

## 错误摘要

系统提供错误摘要功能，包含：

- 总错误数量
- 各类型错误统计
- 账号切换次数
- 当前账号信息
- 可用账号数量

## 集成到现有代码

### 1. 单平台爬虫

已在 `api/crawler_core.py` 中集成，自动处理所有爬取操作。

### 2. 多平台爬虫

已在 `api/multi_platform_crawler.py` 中集成，每个平台独立处理错误。

### 3. 平台客户端

已在 `media_platform/xhs/client.py` 中增强错误检测。

## 测试

运行测试脚本验证功能：

```bash
python test_error_handler.py
```

## 最佳实践

### 1. 错误处理优先级

1. **账号切换**: 权限丢失、登录失效、账号被封
2. **延迟重试**: 验证码、频率限制、网络错误
3. **终止操作**: 达到最大重试次数或不可恢复错误

### 2. 配置建议

- **生产环境**: 使用默认配置，确保稳定性
- **测试环境**: 减少重试次数，加快测试速度
- **高频率场景**: 增加延迟时间，避免触发限制

### 3. 监控建议

- 监控错误摘要统计
- 关注账号切换频率
- 记录重试成功率
- 设置告警阈值

## 故障排除

### 1. 常见问题

**Q: 为什么重试后仍然失败？**
A: 检查是否达到最大重试次数，或遇到不可恢复的错误类型。

**Q: 账号切换不生效？**
A: 检查数据库中的账号状态，确保有可用的有效账号。

**Q: 延迟时间过长？**
A: 调整 `base_delay` 和 `max_delay` 参数。

### 2. 调试技巧

- 启用详细日志记录
- 检查错误摘要信息
- 验证账号状态
- 测试网络连接

## 扩展开发

### 1. 添加新的错误类型

```python
class ErrorType(Enum):
    NEW_ERROR_TYPE = "new_error_type"

# 在 detect_error_type 方法中添加检测逻辑
```

### 2. 自定义处理策略

```python
def should_retry(self, error_type: ErrorType) -> bool:
    # 自定义重试逻辑
    pass
```

### 3. 集成新的平台

```python
# 在平台客户端中添加错误检测
if response.status_code == NEW_ERROR_CODE:
    raise Exception("新的错误类型")
```

## 总结

本错误处理机制提供了：

- ✅ 自动错误检测和分类
- ✅ 智能重试策略
- ✅ 账号切换功能
- ✅ 详细的日志记录
- ✅ 灵活的配置选项
- ✅ 完善的测试覆盖

通过合理配置和使用，能够显著提高爬虫的稳定性和成功率。
