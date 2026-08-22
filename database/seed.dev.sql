-- 开发环境样例数据，仅由 docker-compose.dev.yml 挂载。

INSERT INTO voice_actors (name, description, image_count, is_active) VALUES
('中岛由贵', '开发样例声优', 0, 1),
('佐藤利奈', '开发样例声优', 0, 1),
('花澤香菜', '开发样例声优', 0, 1),
('水树奈奈', '开发样例声优', 0, 1),
('大西沙织', '开发样例声优', 0, 1)
ON DUPLICATE KEY UPDATE name = VALUES(name);

INSERT INTO aliases (
    alias_name,
    target_voice_actor_id,
    is_global,
    description,
    priority,
    is_active,
    created_by
)
SELECT '贵贵', id, 1, '开发样例别名', 10, 1, 0
FROM voice_actors
WHERE name = '中岛由贵'
ON DUPLICATE KEY UPDATE alias_name = VALUES(alias_name);

INSERT INTO aliases (
    alias_name,
    target_voice_actor_id,
    is_global,
    description,
    priority,
    is_active,
    created_by
)
SELECT '香菜', id, 1, '开发样例别名', 5, 1, 0
FROM voice_actors
WHERE name = '花澤香菜'
ON DUPLICATE KEY UPDATE alias_name = VALUES(alias_name);
