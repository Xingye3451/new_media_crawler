-- 视频元数据表
CREATE TABLE IF NOT EXISTS video_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- 基础信息
    platform VARCHAR(50) NOT NULL COMMENT '平台名称',
    content_id VARCHAR(100) NOT NULL COMMENT '内容ID',
    title VARCHAR(500) COMMENT '视频标题',
    description TEXT COMMENT '视频描述',
    author VARCHAR(200) COMMENT '作者',
    author_id VARCHAR(100) COMMENT '作者ID',
    
    -- 存储信息
    storage_type VARCHAR(20) NOT NULL COMMENT '存储类型: local/minio',
    file_path VARCHAR(500) NOT NULL COMMENT '文件路径',
    file_size INT COMMENT '文件大小(字节)',
    file_hash VARCHAR(64) COMMENT '文件哈希值',
    content_type VARCHAR(100) COMMENT '文件类型',
    local_path VARCHAR(500) COMMENT '本地文件路径',
    
    -- 视频信息
    duration FLOAT COMMENT '视频时长(秒)',
    width INT COMMENT '视频宽度',
    height INT COMMENT '视频高度',
    fps FLOAT COMMENT '帧率',
    bitrate INT COMMENT '比特率',
    format VARCHAR(20) COMMENT '视频格式',
    
    -- 统计信息
    view_count INT DEFAULT 0 COMMENT '播放次数',
    like_count INT DEFAULT 0 COMMENT '点赞数',
    comment_count INT DEFAULT 0 COMMENT '评论数',
    share_count INT DEFAULT 0 COMMENT '分享数',
    
    -- 标签和分类
    tags JSON COMMENT '标签列表',
    category VARCHAR(100) COMMENT '分类',
    
    -- 时间信息
    publish_time DATETIME COMMENT '发布时间',
    crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '爬取时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 状态信息
    is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否已删除',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态: active/deleted/error',
    
    -- 扩展信息
    extra_data JSON COMMENT '扩展数据',
    
    -- 索引
    INDEX idx_platform_content_id (platform, content_id),
    INDEX idx_platform (platform),
    INDEX idx_author (author),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status),
    INDEX idx_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='视频元数据表';

-- 存储统计表
CREATE TABLE IF NOT EXISTS storage_statistics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- 统计信息
    total_files INT DEFAULT 0 COMMENT '总文件数',
    total_size BIGINT DEFAULT 0 COMMENT '总大小(字节)',
    local_files INT DEFAULT 0 COMMENT '本地文件数',
    local_size BIGINT DEFAULT 0 COMMENT '本地文件大小',
    minio_files INT DEFAULT 0 COMMENT 'MinIO文件数',
    minio_size BIGINT DEFAULT 0 COMMENT 'MinIO文件大小',
    
    -- 平台统计
    platform_stats JSON COMMENT '按平台统计',
    
    -- 时间信息
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='存储统计表';

-- 下载任务表
CREATE TABLE IF NOT EXISTS download_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- 任务信息
    task_id VARCHAR(100) NOT NULL COMMENT '任务ID',
    platform VARCHAR(50) NOT NULL COMMENT '平台名称',
    content_id VARCHAR(100) NOT NULL COMMENT '内容ID',
    video_url TEXT NOT NULL COMMENT '视频URL',
    
    -- 任务状态
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/downloading/completed/failed',
    progress FLOAT DEFAULT 0 COMMENT '进度(0-100)',
    error_message TEXT COMMENT '错误信息',
    
    -- 重试信息
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    max_retries INT DEFAULT 3 COMMENT '最大重试次数',
    next_retry_time DATETIME COMMENT '下次重试时间',
    
    -- 时间信息
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    started_at DATETIME COMMENT '开始时间',
    completed_at DATETIME COMMENT '完成时间',
    
    -- 索引
    INDEX idx_task_id (task_id),
    INDEX idx_platform_content_id (platform, content_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='下载任务表';

-- 文件访问日志表
CREATE TABLE IF NOT EXISTS file_access_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- 访问信息
    metadata_id INT NOT NULL COMMENT '元数据ID',
    access_type VARCHAR(20) NOT NULL COMMENT '访问类型: download/stream/view',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    user_agent TEXT COMMENT '用户代理',
    
    -- 访问结果
    status_code INT COMMENT '状态码',
    response_time INT COMMENT '响应时间(毫秒)',
    bytes_transferred BIGINT COMMENT '传输字节数',
    
    -- 时间信息
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '访问时间',
    
    -- 索引
    INDEX idx_metadata_id (metadata_id),
    INDEX idx_access_type (access_type),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (metadata_id) REFERENCES video_metadata(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文件访问日志表'; 