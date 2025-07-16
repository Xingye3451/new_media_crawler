-- MediaCrawler 数据库设置脚本
-- 需要以 root 用户或具有管理员权限的用户执行

-- 1. 创建数据库
CREATE DATABASE IF NOT EXISTS `mediacrawler` 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 2. 创建用户（如果不存在）
CREATE USER IF NOT EXISTS 'aiuser'@'%' IDENTIFIED BY 'edcghj98578';

-- 3. 授予用户对 mediacrawler 数据库的所有权限
GRANT ALL PRIVILEGES ON `mediacrawler`.* TO 'aiuser'@'%';

-- 4. 刷新权限
FLUSH PRIVILEGES;

-- 5. 显示结果
SELECT 'Database setup completed successfully!' as status;

-- 6. 验证权限
SHOW GRANTS FOR 'aiuser'@'%'; 