# 🧪 QQ 声优机器人 - 完整测试指南

## 📋 测试目标

验证以下功能：
1. ✅ 图片重命名脚本自动更新数据库
2. ✅ 数据库同步功能正常
3. ✅ 机器人能正确读取数据库图片记录
4. ✅ 机器人能在 QQ 群中成功发送图片

---

## 🚀 快速开始测试

### **步骤 1：重新构建并启动服务**

```powershell
cd C:\Users\i\Desktop\qqbot

# 关闭所有容器
docker-compose down

# 重新构建 NoneBot 镜像（包含最新代码修改）
docker-compose build --no-cache nonebot

# 启动所有服务
docker-compose up -d

# 等待服务就绪（约15秒）
Start-Sleep -Seconds 15

# 查看容器状态
docker-compose ps
```

**预期结果：**
- mysql: `healthy` ✅
- napcat: `running` ✅
- nonebot: `running` ✅

---

### **步骤 2：检查中岛由贵文件夹中的文件**

```powershell
docker-compose exec nonebot ls -lah /app/images/中岛由贵/
```

**预期结果：**
应该看到你上传的图片文件，例如：
```
-rw-r--r-- 1 root root 492K Apr 20 00:38 中岛由贵_001.jpg
```
或者其他文件名。

---

### **步骤 3：运行图片重命名脚本（带数据库更新）**

```powershell
docker-compose exec nonebot python /app/bot/manage.py rename-images "中岛由贵"
```

**预期输出示例：**
```
============================================================
重命名声优图片: 中岛由贵
============================================================
2026-04-20 XX:XX:XX | INFO | bot.plugins.voice_actor.utils:220 - 开始重命名 中岛由贵 的 1 张图片
2026-04-20 XX:XX:XX | INFO | bot.plugins.voice_actor.utils:244 - ✓ 重命名: [旧名字] → 中岛由贵_001.jpg
2026-04-20 XX:XX:XX | INFO | bot.plugins.voice_actor.utils:245 -   修改时间: 2026-04-20 XX:XX:XX
2026-04-20 XX:XX:XX | INFO | bot.plugins.voice_actor.utils:245 -   数据库记录已更新

✅ 完成! 成功处理 1 张图片
```

**关键验证点：**
- ✅ 显示"数据库记录已更新"或"创建新记录"

---

### **步骤 4：同步数据库（扫描文件系统）**

```powershell
docker-compose exec nonebot python /app/bot/manage.py sync-database
```

**预期输出示例：**
```
============================================================
扫描文件系统并同步数据库
============================================================
2026-04-20 XX:XX:XX | INFO | ... - 开始扫描声优文件夹...
2026-04-20 XX:XX:XX | INFO | ... - + 添加记录: 中岛由贵/中岛由贵_001.jpg

============================================================
📊 同步完成
✅ 添加新记录: 1 条
============================================================
```

**关键验证点：**
- ✅ 显示"添加新记录"数量 > 0

---

### **步骤 5：验证数据库中的 Image 记录**

```powershell
# 查看中岛由贵相关的所有图片记录
docker-compose exec mysql mysql -u qqbot -pqqbot123 qqbot -e "SELECT id, voice_actor_id, filename, file_path, is_active, created_at FROM images WHERE voice_actor_id = (SELECT id FROM voice_actors WHERE name='中岛由贵');"
```

**预期结果：**
```
+----+----------------+------------------------+-----------------------------------------------+-----------+---------------------+
| id | voice_actor_id | filename               | file_path                                     | is_active | created_at          |
+----+----------------+------------------------+-----------------------------------------------+-----------+---------------------+
|  1 |              1 | 中岛由贵_001.jpg       | /app/images/中岛由贵/中岛由贵_001.jpg       |         1 | 2026-04-20 XX:XX:XX |
+----+----------------+------------------------+-----------------------------------------------+-----------+---------------------+
```

**关键验证点：**
- ✅ `filename` 是规范的命名格式（声优名_序号.扩展名）
- ✅ `file_path` 路径正确
- ✅ `is_active` = 1（表示激活状态）

---

### **步骤 6：QQ 群中测试机器人发图**

#### **6.1 在 QQ 群中发送消息**

在任何 QQ 群中发送：
```
中岛由贵
```

#### **6.2 预期机器人回复**

机器人应该立即回复：
```
给你 中岛由贵 的图片~
[图片]
```

#### **6.3 检查日志确认**

```powershell
docker-compose logs nonebot --tail 30
```

**预期日志输出：**
```
2026-04-20 XX:XX:XX [INFO] 收到消息 - 用户: XXXXXX, 群: XXXXXX, 内容: 中岛由贵
2026-04-20 XX:XX:XX [INFO] 成功响应请求 - 用户: XXXXXX, 声优: 中岛由贵, 耗时: XXXms
```

---

## 🔍 故障排查

### **问题 1：机器人没有回复**

**检查日志：**
```powershell
docker-compose logs nonebot --tail 50 | findstr "中岛由贵"
```

**可能原因及解决方案：**

| 症状               | 原因             | 解决方案                                                                     |
| ------------------ | ---------------- | ---------------------------------------------------------------------------- |
| 日志中无"收到消息" | NapCat 连接失败  | 检查 NapCat 是否已登录：`docker-compose logs napcat \| findstr "Login"`      |
| "未找到声优"       | 别名解析失败     | 确认声优名称完全匹配，如"中岛由贵"                                           |
| "没有可用的图片"   | 数据库中没有记录 | 运行 `sync-database` 命令重新同步                                            |
| "图片文件不存在"   | 文件路径错误     | 验证文件是否存在：`docker-compose exec nonebot ls -la /app/images/中岛由贵/` |

---

### **问题 2：重命名脚本出错**

**完整错误日志：**
```powershell
docker-compose exec nonebot python /app/bot/manage.py rename-images "中岛由贵" 2>&1
```

**常见错误：**
- `声优 X 不存在于数据库` - 检查声优名称拼写
- `文件夹中没有图片` - 检查文件夹是否有 jpg/png 等图片文件

---

### **问题 3：同步数据库报错**

```powershell
docker-compose exec nonebot python /app/bot/manage.py sync-database 2>&1
```

**查看完整错误堆栈。** 常见原因：
- 数据库连接失败
- 文件权限问题
- 路径不存在

---

## 📊 测试检查清单

完成以下所有验证：

- [ ] 容器全部启动成功（docker-compose ps）
- [ ] 文件夹中有图片文件
- [ ] 重命名脚本成功执行
- [ ] 重命名日志显示"数据库记录已更新"
- [ ] 同步数据库成功执行
- [ ] 数据库中存在激活状态的 Image 记录
- [ ] 在 QQ 群中成功收到机器人发送的图片
- [ ] NoneBot 日志中显示"成功响应请求"

---

## 💡 关键改进说明

### **改进 1：重命名脚本自动更新数据库**

**文件：** `backend/bot/plugins/voice_actor/utils.py`

重命名函数现在：
1. 重命名文件
2. 查询数据库中的对应记录
3. 更新 `filename` 和 `file_path`
4. 如果没有记录则创建新记录
5. 记录完整的日志

**代码位置：** `rename_images_in_folder()` 函数第 220-310 行

### **改进 2：数据库同步函数**

**文件：** `backend/bot/plugins/voice_actor/utils.py`

新增 `sync_database_with_files()` 函数：
1. 扫描文件系统中的所有图片
2. 检查数据库是否有对应记录
3. 添加缺失的数据库记录
4. 标记已删除的文件为不活跃
5. 返回处理统计

**代码位置：** `sync_database_with_files()` 函数第 343-440 行

### **改进 3：管理命令**

**文件：** `backend/bot/manage.py`

新增命令：
- `sync-database` - 扫描并同步数据库

**代码位置：** `main()` 函数 elif 分支

---

## 📞 需要帮助？

如果测试过程中遇到问题，请提供：
1. 完整的命令输出
2. 相关的日志片段
3. 你尝试的步骤
4. 期望的结果 vs 实际的结果
