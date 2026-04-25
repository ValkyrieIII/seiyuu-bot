# 数据库设计文档

## 概述

QQ声优机器人使用 MySQL 8.0 数据库来管理声优信息、图片资源、用户冷却状态和请求日志。

## ER 图

```
voice_actors (1) ──── (N) images
     ↑                    
     │                    
     └──── (N) aliases    

voice_actors (1) ──── (N) request_logs

user_cooldowns (独立表)

request_logs (1) ──── (?) images
```

## 表详细设计

### 1. voice_actors 表 - 声优基础信息

| 字段        | 类型         | 约束                        | 说明                 |
| ----------- | ------------ | --------------------------- | -------------------- |
| id          | INT          | PRIMARY KEY, AUTO_INCREMENT | 声优唯一标识         |
| name        | VARCHAR(255) | UNIQUE, NOT NULL            | 声优名称             |
| description | TEXT         | NULL                        | 声优简介             |
| image_count | INT          | DEFAULT 0                   | 图片数量（计数缓存） |
| is_active   | TINYINT      | DEFAULT 1                   | 是否激活（逻辑删除） |
| created_at  | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP   | 创建时间             |
| updated_at  | TIMESTAMP    | ON UPDATE CURRENT_TIMESTAMP | 更新时间             |

**索引**：
- `PRIMARY KEY (id)`
- `UNIQUE KEY (name)`
- `INDEX idx_is_active (is_active)`

**样例数据**：
```sql
INSERT INTO voice_actors VALUES
(1, '中岛由贵', '日本著名声优', 150, 1, NOW(), NOW()),
(2, '花澤香菜', '代表作很多', 200, 1, NOW(), NOW());
```

---

### 2. images 表 - 图片资源

| 字段           | 类型         | 约束                        | 说明                |
| -------------- | ------------ | --------------------------- | ------------------- |
| id             | INT          | PRIMARY KEY, AUTO_INCREMENT | 图片唯一标识        |
| voice_actor_id | INT          | FOREIGN KEY, NOT NULL       | 所属声优ID          |
| filename       | VARCHAR(255) | UNIQUE, NOT NULL            | 文件名（去重）      |
| file_path      | VARCHAR(512) | NOT NULL                    | 完整文件路径        |
| size_kb        | INT          | DEFAULT 0                   | 文件大小（KB）      |
| file_hash      | VARCHAR(64)  | NULL                        | MD5哈希（去重检查） |
| is_active      | TINYINT      | DEFAULT 1                   | 是否激活            |
| created_at     | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP   | 上传时间            |
| updated_at     | TIMESTAMP    | ON UPDATE CURRENT_TIMESTAMP | 更新时间            |

**约束**：
- FOREIGN KEY (voice_actor_id) REFERENCES voice_actors(id) ON DELETE CASCADE

**索引**：
- `PRIMARY KEY (id)`
- `UNIQUE KEY (filename)`
- `FOREIGN KEY (voice_actor_id)`
- `INDEX idx_is_active (is_active)`
- `INDEX idx_file_hash (file_hash)` - 用于快速去重

**样例数据**：
```sql
INSERT INTO images VALUES
(1, 1, '中岛由贵_000001.jpg', '/app/images/中岛由贵/中岛由贵_000001.jpg', 256, 'a1b2c3d4e5f6...', 1, NOW(), NOW()),
(2, 1, '中岛由贵_000002.jpg', '/app/images/中岛由贵/中岛由贵_000002.jpg', 512, 'b2c3d4e5f6g7...', 1, NOW(), NOW());
```

---

### 3. aliases 表 - 别名映射

| 字段                  | 类型         | 约束                        | 说明                       |
| --------------------- | ------------ | --------------------------- | -------------------------- |
| id                    | INT          | PRIMARY KEY, AUTO_INCREMENT | 别名唯一标识               |
| alias_name            | VARCHAR(255) | NOT NULL                    | 别名                       |
| target_voice_actor_id | INT          | FOREIGN KEY, NOT NULL       | 目标声优ID                 |
| is_global             | TINYINT      | DEFAULT 1                   | 是否为全局别名             |
| user_id               | INT          | NULL                        | 用户ID（用户自定义时使用） |
| description           | TEXT         | NULL                        | 别名说明                   |
| priority              | INT          | DEFAULT 0                   | 优先级（高优先级先匹配）   |
| is_active             | TINYINT      | DEFAULT 1                   | 是否激活                   |
| created_by            | INT          | NULL                        | 创建者ID                   |
| created_at            | TIMESTAMP    | DEFAULT CURRENT_TIMESTAMP   | 创建时间                   |
| updated_at            | TIMESTAMP    | ON UPDATE CURRENT_TIMESTAMP | 更新时间                   |

**约束**：
- FOREIGN KEY (target_voice_actor_id) REFERENCES voice_actors(id) ON DELETE CASCADE
- UNIQUE KEY (alias_name, user_id) - 同一用户不能有重复别名

**索引**：
- `PRIMARY KEY (id)`
- `UNIQUE KEY (alias_name, user_id)`
- `FOREIGN KEY (target_voice_actor_id)`
- `INDEX idx_alias_name (alias_name)`
- `INDEX idx_is_global (is_global)`

**样例数据**：
```sql
INSERT INTO aliases VALUES
(1, '贵贵', 1, 1, NULL, '中岛由贵的昵称', 10, 1, 0, NOW(), NOW()),
(2, '由贵', 1, 1, NULL, '中岛由贵的缩写', 5, 1, 0, NOW(), NOW()),
(3, '香菜', 2, 1, NULL, '花澤香菜的昵称', 5, 1, 0, NOW(), NOW());
```

**别名解析优先级**：
1. 用户自定义别名（user_id != NULL）- 优先级最高
2. 全局别名 - 按 priority 降序排列
3. 直接匹配声优名称

---

### 4. user_cooldowns 表 - 用户冷却状态

| 字段              | 类型        | 约束                        | 说明                   |
| ----------------- | ----------- | --------------------------- | ---------------------- |
| id                | INT         | PRIMARY KEY, AUTO_INCREMENT | 冷却ID                 |
| user_id           | INT         | NOT NULL                    | 用户QQ号               |
| command_type      | VARCHAR(64) | NOT NULL                    | 命令类型               |
| last_request_time | BIGINT      | NOT NULL                    | 最后请求时间戳（毫秒） |
| cooldown_duration | INT         | DEFAULT 1                   | 冷却时长（秒）         |
| request_count     | INT         | DEFAULT 1                   | 请求计数               |
| created_at        | TIMESTAMP   | DEFAULT CURRENT_TIMESTAMP   | 记录创建时间           |
| updated_at        | TIMESTAMP   | ON UPDATE CURRENT_TIMESTAMP | 记录更新时间           |

**约束**：
- UNIQUE KEY (user_id, command_type) - 同一用户的同一命令只有一条记录

**索引**：
- `PRIMARY KEY (id)`
- `UNIQUE KEY (user_id, command_type)`
- `INDEX idx_last_request_time (last_request_time)` - 用于清理过期记录

**冷却逻辑**：
- 当用户请求时，检查距上次请求的时间间隔
- 如果小于 cooldown_duration，则拒绝请求并返回剩余冷却时间
- 否则更新 last_request_time 并执行请求

**样例数据**：
```sql
INSERT INTO user_cooldowns VALUES
(1, 123456789, 'voice_actor', 1705315200000, 1, 5, NOW(), NOW());
-- 用户123456789的voice_actor命令最后请求时间戳为1705315200000，冷却1秒，已请求5次
```

---

### 5. request_logs 表 - 请求日志

| 字段             | 类型        | 约束                        | 说明             |
| ---------------- | ----------- | --------------------------- | ---------------- |
| id               | INT         | PRIMARY KEY, AUTO_INCREMENT | 日志ID           |
| user_id          | INT         | NOT NULL                    | 用户QQ号         |
| group_id         | INT         | NULL                        | 群组ID           |
| command          | VARCHAR(64) | NOT NULL                    | 命令             |
| voice_actor_id   | INT         | NULL                        | 请求的声优ID     |
| image_id         | INT         | NULL                        | 返回的图片ID     |
| status           | VARCHAR(32) | DEFAULT 'success'           | 响应状态         |
| response_time_ms | INT         | NULL                        | 响应时间（毫秒） |
| error_message    | TEXT        | NULL                        | 错误信息         |
| created_at       | TIMESTAMP   | DEFAULT CURRENT_TIMESTAMP   | 请求时间         |

**索引**：
- `PRIMARY KEY (id)`
- `INDEX idx_user_id (user_id)`
- `INDEX idx_group_id (group_id)`
- `INDEX idx_command (command)`
- `INDEX idx_created_at (created_at)` - 用于按时间查询

**状态值**：
- `success` - 成功
- `cooldown` - 冷却中
- `notfound` - 未找到声优
- `no_image` - 声优无可用图片
- `file_missing` - 文件不存在
- `error` - 其他错误

**样例数据**：
```sql
INSERT INTO request_logs VALUES
(1, 123456789, 987654321, 'voice_actor', 1, 5, 'success', 150, NULL, NOW()),
(2, 123456789, 987654321, 'voice_actor', NULL, NULL, 'cooldown', 50, '冷却中', NOW());
```

---

## 视图

### v_voice_actor_stats 视图 - 声优统计

用于快速查询声优的图片数量和别名列表。

```sql
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
```

**样例查询**：
```sql
SELECT * FROM v_voice_actor_stats;
-- 结果：
-- id | name       | image_count | aliases
-- 1  | 中岛由贵   | 150         | 贵贵,由贵
-- 2  | 花澤香菜   | 200         | 香菜
```

---

## 常用查询

### 查询声优的所有激活图片

```sql
SELECT * FROM images 
WHERE voice_actor_id = ? AND is_active = 1 
ORDER BY created_at DESC;
```

### 获取别名映射

```sql
SELECT va.* FROM voice_actors va
LEFT JOIN aliases a ON va.id = a.target_voice_actor_id
WHERE a.alias_name = ? AND a.is_active = 1 AND va.is_active = 1
ORDER BY a.priority DESC
LIMIT 1;
```

### 查询用户的请求历史

```sql
SELECT * FROM request_logs
WHERE user_id = ? AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY created_at DESC;
```

### 统计请求成功率

```sql
SELECT 
    DATE(created_at) as request_date,
    SUM(IF(status = 'success', 1, 0)) as success_count,
    COUNT(*) as total_count,
    ROUND(SUM(IF(status = 'success', 1, 0)) / COUNT(*) * 100, 2) as success_rate
FROM request_logs
GROUP BY DATE(created_at)
ORDER BY request_date DESC;
```

---

## 性能优化建议

### 1. 索引策略

- **频繁查询的列**：name, alias_name, user_id, created_at - 已建立索引
- **组合查询**：考虑为 (voice_actor_id, is_active, created_at) 建立复合索引
- **模糊查询**：暂不支持，可在应用层实现

### 2. 数据清理

```sql
-- 定期删除过期日志（超过30天）
DELETE FROM request_logs 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- 清理过期冷却记录（已冷却结束）
DELETE FROM user_cooldowns 
WHERE UNIX_TIMESTAMP(updated_at) * 1000 + cooldown_duration * 1000 < UNIX_TIMESTAMP(NOW()) * 1000;
```

### 3. 分区策略（可选）

对大数据量表（如 request_logs）按月份分区：

```sql
ALTER TABLE request_logs 
PARTITION BY RANGE (MONTH(created_at)) (
    PARTITION p01 VALUES LESS THAN (2),
    PARTITION p02 VALUES LESS THAN (3),
    -- ... 12 个分区
    PARTITION p12 VALUES LESS THAN (13)
);
```

---

## 备份和恢复

### 备份

```bash
# 导出整个数据库
mysqldump -u qqbot -p qqbot > backup.sql

# 在 Docker 中备份
docker exec qqbot-mysql mysqldump -u qqbot -pqqbot123 qqbot > backup.sql
```

### 恢复

```bash
# 恢复数据库
mysql -u qqbot -p qqbot < backup.sql

# 在 Docker 中恢复
docker exec -i qqbot-mysql mysql -u qqbot -pqqbot123 qqbot < backup.sql
```

---

## 故障排查

### 检查表结构

```sql
DESCRIBE voice_actors;
SHOW INDEX FROM images;
```

### 检查数据完整性

```sql
-- 查找孤立的图片（声优已删除）
SELECT i.* FROM images i
LEFT JOIN voice_actors va ON i.voice_actor_id = va.id
WHERE va.id IS NULL;

-- 查找无图片的激活声优
SELECT va.* FROM voice_actors va
LEFT JOIN images i ON va.id = i.voice_actor_id AND i.is_active = 1
WHERE va.is_active = 1
GROUP BY va.id
HAVING COUNT(i.id) = 0;
```

### 性能调试

```sql
-- 查看慢查询日志
SHOW VARIABLES LIKE 'long_query_time';
SET GLOBAL long_query_time = 2;

-- 解析查询计划
EXPLAIN SELECT * FROM images WHERE voice_actor_id = 1 AND is_active = 1;
```
