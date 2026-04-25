USE qqbot;

-- 声优表
CREATE TABLE IF NOT EXISTS voice_actors (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '声优ID',
    name VARCHAR(255) NOT NULL UNIQUE COMMENT '声优名称',
    description TEXT COMMENT '声优简介',
    image_count INT DEFAULT 0 COMMENT '图片数量',
    is_active TINYINT DEFAULT 1 COMMENT '是否激活',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_name (name),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='声优基础信息表';

-- 图片表
CREATE TABLE IF NOT EXISTS images (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '图片ID',
    voice_actor_id INT NOT NULL COMMENT '声优ID',
    filename VARCHAR(255) NOT NULL UNIQUE COMMENT '文件名',
    file_path VARCHAR(512) NOT NULL COMMENT '文件路径',
    size_kb INT DEFAULT 0 COMMENT '文件大小（KB）',
    file_hash VARCHAR(64) COMMENT 'MD5哈希值（去重）',
    is_active TINYINT DEFAULT 1 COMMENT '是否激活',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (voice_actor_id) REFERENCES voice_actors(id) ON DELETE CASCADE,
    INDEX idx_voice_actor_id (voice_actor_id),
    INDEX idx_is_active (is_active),
    INDEX idx_file_hash (file_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='图片资源表';

-- 别名表
CREATE TABLE IF NOT EXISTS aliases (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '别名ID',
    alias_name VARCHAR(255) NOT NULL COMMENT '别名',
    target_voice_actor_id INT NOT NULL COMMENT '目标声优ID',
    is_global TINYINT DEFAULT 1 COMMENT '是否为全局别名',
    user_id INT COMMENT '用户ID（用户自定义别名时使用）',
    description TEXT COMMENT '别名说明',
    priority INT DEFAULT 0 COMMENT '优先级',
    is_active TINYINT DEFAULT 1 COMMENT '是否激活',
    created_by INT COMMENT '创建者ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (target_voice_actor_id) REFERENCES voice_actors(id) ON DELETE CASCADE,
    UNIQUE KEY unique_alias (alias_name, user_id),
    INDEX idx_alias_name (alias_name),
    INDEX idx_voice_actor_id (target_voice_actor_id),
    INDEX idx_user_id (user_id),
    INDEX idx_is_global (is_global)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='别名映射表';

-- 用户冷却表
CREATE TABLE IF NOT EXISTS user_cooldowns (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '冷却ID',
    user_id INT NOT NULL COMMENT '用户ID',
    command_type VARCHAR(64) NOT NULL COMMENT '命令类型',
    last_request_time BIGINT NOT NULL COMMENT '最后请求时间戳（毫秒）',
    cooldown_duration INT DEFAULT 1 COMMENT '冷却时长（秒）',
    request_count INT DEFAULT 1 COMMENT '请求计数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY unique_user_command (user_id, command_type),
    INDEX idx_user_id (user_id),
    INDEX idx_last_request_time (last_request_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户冷却状态表';

-- 请求日志表（可选，用于数据分析）
CREATE TABLE IF NOT EXISTS request_logs (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '日志ID',
    user_id INT NOT NULL COMMENT '用户ID',
    group_id INT COMMENT '群组ID',
    command VARCHAR(64) NOT NULL COMMENT '命令',
    voice_actor_id INT COMMENT '请求的声优ID',
    image_id INT COMMENT '返回的图片ID',
    status VARCHAR(32) NOT NULL DEFAULT 'success' COMMENT '状态（success/cooldown/notfound/error）',
    response_time_ms INT COMMENT '响应时间（毫秒）',
    error_message TEXT COMMENT '错误信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '请求时间',
    INDEX idx_user_id (user_id),
    INDEX idx_group_id (group_id),
    INDEX idx_command (command),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='请求日志表';

-- 创建视图：统计每个声优的图片数量
CREATE OR REPLACE VIEW v_voice_actor_stats AS
SELECT 
    va.id,
    va.name,
    COUNT(i.id) as image_count,
    GROUP_CONCAT(a.alias_name) as aliases
FROM voice_actors va
LEFT JOIN images i ON va.id = i.voice_actor_id AND i.is_active = 1
LEFT JOIN aliases a ON va.id = a.target_voice_actor_id AND a.is_active = 1
WHERE va.is_active = 1
GROUP BY va.id, va.name;
