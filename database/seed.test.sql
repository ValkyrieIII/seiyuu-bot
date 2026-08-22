-- 测试环境固定数据。测试必须依赖这些稳定名称，不使用真实或开发数据。

INSERT INTO voice_actors (name, description, image_count, is_active) VALUES
('测试声优', '自动化测试专用数据', 0, 1)
ON DUPLICATE KEY UPDATE description = VALUES(description), is_active = 1;

INSERT INTO aliases (
    alias_name,
    target_voice_actor_id,
    is_global,
    description,
    priority,
    is_active,
    created_by
)
SELECT '测试别名', id, 1, '自动化测试专用别名', 100, 1, 0
FROM voice_actors
WHERE name = '测试声优'
ON DUPLICATE KEY UPDATE priority = VALUES(priority), is_active = 1;
