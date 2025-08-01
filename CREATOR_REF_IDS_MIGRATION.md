# Creator Ref IDs 字段迁移说明

## 概述

本次迁移将 `crawler_tasks` 表中的 `creator_ref_id` 字段改为 `creator_ref_ids` JSON字段，支持存储多个创作者ID，以适应创作者主页模式可以选择多个创作者的需求。

## 修改内容

### 1. 数据库结构修改

#### 字段变更
- **原字段**: `creator_ref_id` (VARCHAR(100))
- **新字段**: `creator_ref_ids` (JSON)
- **说明**: 支持存储多个创作者ID的JSON数组

#### 索引变更
- **原索引**: `idx_crawler_tasks_creator_ref_id`
- **新索引**: `idx_crawler_tasks_creator_ref_ids(50)`

### 2. 数据模型修改

#### models/task_models.py
```python
# 修改前
creator_ref_id = Column(String(100), comment='创作者引用ID（当crawler_type为creator时，关联unified_creator表）')

# 修改后
creator_ref_ids = Column(JSON, comment='创作者引用ID列表（当crawler_type为creator时，关联unified_creator表）')
```

#### 请求模型修改
```python
# 修改前
creator_ref_id: Optional[str] = Field(None, description="创作者引用ID（当crawler_type为creator时，关联unified_creator表）")

# 修改后
creator_ref_ids: Optional[List[str]] = Field(None, description="创作者引用ID列表（当crawler_type为creator时，关联unified_creator表）")
```

### 3. API层修改

#### api/crawler_core.py
- 修改任务创建逻辑，支持多个创作者ID
- 更新 `update_task_creator_ref_ids` 函数
- 支持从 `selected_creators` 参数获取创作者列表

```python
# 处理创作者ID列表
creator_ref_ids = None
if request.crawler_type == "creator":
    if hasattr(request, 'selected_creators') and request.selected_creators:
        creator_ref_ids = request.selected_creators
    elif hasattr(request, 'creator_ref_ids') and request.creator_ref_ids:
        creator_ref_ids = request.creator_ref_ids
    elif hasattr(request, 'creator_ref_id') and request.creator_ref_id:
        creator_ref_ids = [request.creator_ref_id]
```

### 4. 爬虫层修改

#### media_platform/kuaishou/core.py
- 更新创作者ID获取逻辑
- 修改任务更新函数调用

#### media_platform/bilibili/core.py
- 更新创作者ID获取逻辑
- 修改任务更新函数调用

### 5. 服务层修改

#### services/task_result_service.py
- 更新任务信息获取逻辑
- 支持新的 `creator_ref_ids` 字段

### 6. 前端修改

#### static/task_detail.html
- 更新创作者信息展示逻辑
- 支持JSON数组解析
- 暂时只显示第一个创作者信息

```javascript
// 修改前
if (taskInfo.task_info?.creator_ref_id) {
    loadCreatorDetail(taskInfo.task_info.creator_ref_id);
}

// 修改后
if (taskInfo.task_info?.creator_ref_ids) {
    const creatorIds = Array.isArray(taskInfo.task_info.creator_ref_ids) 
        ? taskInfo.task_info.creator_ref_ids 
        : JSON.parse(taskInfo.task_info.creator_ref_ids || '[]');
    
    if (creatorIds.length > 0) {
        loadCreatorDetail(creatorIds[0]); // 暂时只显示第一个创作者
    }
}
```

## 迁移步骤

### 1. 执行数据库迁移

```bash
# 方法1: 使用SQL脚本
mysql -u username -p database_name < update_creator_ref_id_field.sql

# 方法2: 使用Python迁移脚本
python migrate_creator_ref_ids.py
```

### 2. 验证迁移结果

```bash
# 运行测试脚本
python test_creator_ref_ids_migration.py
```

### 3. 重启服务

```bash
# 重启API服务
systemctl restart mediacrawler
```

## 数据格式示例

### 存储格式
```json
{
  "creator_ref_ids": ["creator_1", "creator_2", "creator_3"]
}
```

### API请求格式
```json
{
  "platform": "ks",
  "crawler_type": "creator",
  "selected_creators": ["creator_1", "creator_2", "creator_3"],
  "keywords": "测试关键词",
  "max_notes_count": 50
}
```

## 兼容性说明

### 向后兼容
- 支持单个创作者ID的旧格式
- 自动转换为数组格式存储

### 向前兼容
- 新创建的创作者任务使用数组格式
- 前端暂时只显示第一个创作者信息

## 注意事项

1. **备份数据**: 执行迁移前请务必备份数据库
2. **测试验证**: 迁移后请运行测试脚本验证功能
3. **服务重启**: 修改完成后需要重启相关服务
4. **前端适配**: 后续可以扩展前端支持显示多个创作者信息

## 故障排除

### 常见问题

1. **JSON解析错误**
   - 检查数据库字段类型是否为JSON
   - 验证存储的数据格式

2. **索引创建失败**
   - 检查MySQL版本是否支持JSON索引
   - 确认索引名称不冲突

3. **前端显示异常**
   - 检查JavaScript JSON解析逻辑
   - 验证API返回的数据格式

### 回滚方案

如果迁移出现问题，可以执行以下SQL回滚：

```sql
-- 恢复原字段
ALTER TABLE crawler_tasks ADD COLUMN creator_ref_id VARCHAR(100) COMMENT '创作者引用ID（当crawler_type为creator时，关联unified_creator表）';

-- 迁移数据（如果有）
UPDATE crawler_tasks 
SET creator_ref_id = JSON_UNQUOTE(JSON_EXTRACT(creator_ref_ids, '$[0]'))
WHERE creator_ref_ids IS NOT NULL;

-- 删除新字段
ALTER TABLE crawler_tasks DROP COLUMN creator_ref_ids;
```

## 后续优化

1. **前端多创作者展示**: 扩展前端支持显示多个创作者信息
2. **创作者切换功能**: 添加创作者切换界面
3. **批量创作者管理**: 支持批量操作多个创作者
4. **创作者统计**: 为每个创作者添加独立的统计信息 