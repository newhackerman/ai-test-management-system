-- 创建数据库
CREATE DATABASE IF NOT EXISTS aitestdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE aitestdb;

-- 创建用户（可选）
CREATE USER IF NOT EXISTS 'aitest'@'%' IDENTIFIED BY 'AItestdb123';
GRANT ALL PRIVILEGES ON aitestdb.* TO 'aitest'@'%';
FLUSH PRIVILEGES;

-- 显示数据库信息
SELECT 'Database initialized successfully' as message;