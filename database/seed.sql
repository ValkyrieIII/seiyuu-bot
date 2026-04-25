USE qqbot;

-- 插入示例声优数据
INSERT INTO voice_actors (name, description, image_count, is_active) VALUES
('中岛由贵', '日本著名声优，代表作《進撃の巨人》里欧-莱纳', 0, 1),
('佐藤利奈', '日本声优，代表作《K》《心理测量者》', 0, 1),
('花澤香菜', '日本声优，代表作《物语系列》《进击的巨人》', 0, 1),
('水树奈奈', '日本声优、歌手，代表作《魔法少女奈叶》', 0, 1),
('大西沙织', '日本声优，代表作《Re:从零开始的异世界生活》', 0, 1)
ON DUPLICATE KEY UPDATE name=name;

-- 插入示例全局别名
INSERT INTO aliases (alias_name, target_voice_actor_id, is_global, description, priority, is_active, created_by) VALUES
('贵贵', 1, 1, '中岛由贵的昵称', 10, 1, 0),
('由贵', 1, 1, '中岛由贵的缩写', 5, 1, 0),
('莱纳声优', 1, 1, '进击的巨人角色关联', 3, 1, 0),
('利奈', 2, 1, '佐藤利奈的昵称', 5, 1, 0),
('香菜', 3, 1, '花澤香菜的昵称', 5, 1, 0),
('水树', 4, 1, '水树奈奈的缩写', 5, 1, 0),
('奈奈', 4, 1, '水树奈奈的昵称', 10, 1, 0),
('沙织', 5, 1, '大西沙织的昵称', 5, 1, 0)
ON DUPLICATE KEY UPDATE alias_name=alias_name;
