import pytest
import asyncio
import json
from store.douyin.douyin_store_sql import add_new_content, query_content_by_content_id

@pytest.mark.asyncio
async def test_add_and_query_content():
    test_content = {
        "aweme_id": "test_123456",
        "aweme_type": "video",  # 必须字段
        "title": "测试视频",
        "tags": ["搞笑", "测试"],  # list 类型
        "meta": {"author": "张三", "duration": 120},  # dict 类型
        "desc": "单元测试内容",
        "create_time": 0,  # 必须字段
        "add_ts": 0,       # 必须字段
        "last_modify_ts": 0  # 必须字段
    }
    # 新增
    row_id = await add_new_content(test_content)
    assert row_id > 0

    # 查询
    result = await query_content_by_content_id("test_123456")
    assert result["aweme_id"] == "test_123456"
    # 数据库查出来是 str，业务层可 json.loads
    tags = result["tags"]
    if isinstance(tags, str):
        tags = json.loads(tags)
    assert tags == ["搞笑", "测试"]
    meta = result["meta"]
    if isinstance(meta, str):
        meta = json.loads(meta)
    assert meta == {"author": "张三", "duration": 120} 