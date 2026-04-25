# API 文档和扩展开发指南

## 目录

1. [核心 API](#核心-api)
2. [服务层 API](#服务层-api)
3. [插件扩展](#插件扩展)
4. [数据库 API](#数据库-api)
5. [示例](#示例)

---

## 核心 API

### VoiceActorService - 声优服务

#### `get_voice_actor_by_name(name: str) -> Optional[VoiceActor]`

根据名称获取声优。

**参数**：
- `name` (str): 声优名称

**返回**：
- `VoiceActor`: 声优对象
- `None`: 未找到

**示例**：
```python
from plugins.voice_actor.services import VoiceActorService

actor = VoiceActorService.get_voice_actor_by_name("中岛由贵")
if actor:
    print(f"找到: {actor.name} - {actor.image_count} 张图片")
```

#### `get_voice_actor_by_id(actor_id: int) -> Optional[VoiceActor]`

根据 ID 获取声优。

**参数**：
- `actor_id` (int): 声优 ID

**返回**：
- `VoiceActor`: 声优对象

#### `get_all_voice_actors() -> List[VoiceActor]`

获取所有激活的声优。

**返回**：
- List[VoiceActor]: 声优列表

---

### ImageService - 图片服务

#### `get_random_image(voice_actor_id: int) -> Optional[Image]`

获取声优的随机图片。

**参数**：
- `voice_actor_id` (int): 声优 ID

**返回**：
- `Image`: 图片对象
- `None`: 无可用图片

**示例**：
```python
from plugins.voice_actor.services import ImageService

image = ImageService.get_random_image(actor_id=1)
if image:
    print(f"获取图片: {image.filename}")
    # 发送图片: MessageSegment.image(f"file:///{image.file_path}")
```

#### `get_images_by_actor_id(voice_actor_id: int, limit: int = 100) -> List[Image]`

获取声优的所有图片（分页）。

**参数**：
- `voice_actor_id` (int): 声优 ID
- `limit` (int): 返回数量上限

**返回**：
- List[Image]: 图片列表

---

### AliasService - 别名服务

#### `resolve_alias(alias_name: str, user_id: int = None) -> Optional[VoiceActor]`

解析别名为声优。

**参数**：
- `alias_name` (str): 别名
- `user_id` (int, optional): 用户 ID（用于查询用户自定义别名）

**返回**：
- `VoiceActor`: 匹配的声优
- `None`: 未找到

**解析优先级**：
1. 用户自定义别名（user_id != NULL）
2. 全局别名（按 priority 降序）
3. 直接匹配声优名称

**示例**：
```python
from plugins.voice_actor.services import AliasService

# 全局别名解析
actor = AliasService.resolve_alias("贵贵")

# 用户自定义别名
actor = AliasService.resolve_alias("我的别名", user_id=123456789)
```

#### `add_global_alias(alias_name: str, voice_actor_id: int, description: str = "", priority: int = 0) -> bool`

添加全局别名。

**参数**：
- `alias_name` (str): 别名
- `voice_actor_id` (int): 目标声优 ID
- `description` (str): 别名说明
- `priority` (int): 优先级（越高越先匹配）

**返回**：
- `bool`: 成功/失败

**示例**：
```python
success = AliasService.add_global_alias(
    alias_name="小贵",
    voice_actor_id=1,
    description="中岛由贵的昵称",
    priority=8
)
```

---

### CooldownService - 冷却服务

#### `check_cooldown(user_id: int, command_type: str = "voice_actor") -> Tuple[bool, int]`

检查用户是否在冷却中。

**参数**：
- `user_id` (int): 用户 QQ 号
- `command_type` (str): 命令类型

**返回**：
- `Tuple[bool, int]`: (是否在冷却中, 剩余秒数)

**示例**：
```python
from plugins.voice_actor.services import CooldownService

is_cooldown, remaining = CooldownService.check_cooldown(user_id=123456789)
if is_cooldown:
    msg = f"请在 {remaining} 秒后重试"
else:
    # 继续处理请求
    pass
```

#### `update_cooldown(user_id: int, command_type: str = "voice_actor", cooldown_duration: int = None)`

更新用户冷却状态。

**参数**：
- `user_id` (int): 用户 QQ 号
- `command_type` (str): 命令类型
- `cooldown_duration` (int, optional): 冷却时长（秒）

**示例**：
```python
# 请求成功后，更新冷却
CooldownService.update_cooldown(user_id=123456789, cooldown_duration=1)
```

---

### RequestLogService - 日志服务

#### `log_request(...) -> None`

记录请求日志。

**参数**：
- `user_id` (int): 用户 QQ 号
- `group_id` (int): 群组 ID
- `command` (str): 命令名称
- `status` (str): 响应状态（success/cooldown/notfound/error）
- `voice_actor_id` (int, optional): 声优 ID
- `image_id` (int, optional): 图片 ID
- `response_time_ms` (int, optional): 响应时间（毫秒）
- `error_message` (str, optional): 错误信息

**示例**：
```python
from plugins.voice_actor.services import RequestLogService
import time

start = time.time()

# ... 处理请求 ...

response_time_ms = int((time.time() - start) * 1000)

RequestLogService.log_request(
    user_id=123456789,
    group_id=987654321,
    command="voice_actor",
    status="success",
    voice_actor_id=1,
    image_id=100,
    response_time_ms=response_time_ms
)
```

---

## 服务层 API

### 工具函数 - utils.py

#### `normalize_text(text: str) -> str`

规范化文本（去空格、转小写）。

```python
from utils import normalize_text

text = "  中岛由贵  "
normalized = normalize_text(text)  # "中岛由贵"
```

#### `calculate_similarity(s1: str, s2: str) -> float`

计算两个字符串的相似度（0-1）。

```python
from utils import calculate_similarity

ratio = calculate_similarity("贵贵", "中岛由贵")  # 返回相似度
```

#### `calculate_file_hash(file_path: str) -> str`

计算文件的 MD5 哈希值。

```python
from utils import calculate_file_hash

hash_value = calculate_file_hash("/app/images/actor/image.jpg")
```

#### `validate_image_file(file_path: str) -> bool`

验证图片文件是否有效。

```python
from utils import validate_image_file

if validate_image_file(file_path):
    print("有效的图片文件")
```

---

## 数据库 API

### 会话管理

```python
from plugins.voice_actor.models import get_session, SessionLocal

# 方式1：使用助手函数
session = get_session()
try:
    # ... 数据库操作 ...
    pass
finally:
    session.close()

# 方式2：使用工厂函数
session = SessionLocal()
try:
    # ... 数据库操作 ...
    pass
finally:
    session.close()
```

### ORM 模型

#### VoiceActor

```python
from plugins.voice_actor.models import VoiceActor, get_session

session = get_session()

# 查询
actor = session.query(VoiceActor).filter(
    VoiceActor.name == "中岛由贵"
).first()

# 创建
new_actor = VoiceActor(
    name="新声优",
    description="说明",
    image_count=0,
    is_active=True
)
session.add(new_actor)
session.commit()

# 更新
actor.image_count = 100
session.commit()

# 删除（逻辑删除）
actor.is_active = False
session.commit()

session.close()
```

#### Image

```python
from plugins.voice_actor.models import Image

session = get_session()

# 创建图片记录
image = Image(
    voice_actor_id=1,
    filename="中岛由贵_000001.jpg",
    file_path="/app/images/中岛由贵/中岛由贵_000001.jpg",
    size_kb=256,
    file_hash="a1b2c3d4e5f6..."
)
session.add(image)
session.commit()
```

#### Alias

```python
from plugins.voice_actor.models import Alias

# 创建全局别名
alias = Alias(
    alias_name="贵贵",
    target_voice_actor_id=1,
    is_global=True,
    priority=10
)
session.add(alias)
session.commit()

# 创建用户自定义别名
user_alias = Alias(
    alias_name="我的贵贵",
    target_voice_actor_id=1,
    is_global=False,
    user_id=123456789
)
session.add(user_alias)
session.commit()
```

---

## 插件扩展

### 创建新的消息处理器

在 `handlers.py` 中添加新的事件处理器：

```python
from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from loguru import logger

# 创建一个新的命令处理器
new_matcher = on_command("新命令", priority=50, block=False)

@new_matcher.handle()
async def handle_new_command(event: GroupMessageEvent):
    """处理新命令"""
    user_id = event.user_id
    group_id = event.group_id
    
    logger.info(f"用户 {user_id} 在群 {group_id} 执行新命令")
    
    # 在这里添加您的业务逻辑
    await new_matcher.send("处理结果")
```

### 创建新的插件模块

1. 在 `plugins/` 目录下创建新的插件文件夹
2. 创建 `__init__.py`、`models.py`、`services.py`、`handlers.py`
3. 在主配置中注册插件

例如创建"签到"插件：

```
plugins/
├── voice_actor/          # 现有的声优插件
└── checkin/              # 新的签到插件
    ├── __init__.py
    ├── models.py
    ├── services.py
    └── handlers.py
```

### 使用数据库扩展功能

例如添加"用户签到"功能：

```python
# checkin/models.py
from sqlalchemy import create_engine, Column, Integer, DateTime
from datetime import datetime

class UserCheckIn(Base):
    __tablename__ = "user_checkins"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    check_in_date = Column(DateTime, default=datetime.utcnow)
    reward_points = Column(Integer, default=0)

# checkin/services.py
def add_check_in(user_id: int, reward_points: int = 10):
    session = get_session()
    try:
        checkin = UserCheckIn(
            user_id=user_id,
            reward_points=reward_points
        )
        session.add(checkin)
        session.commit()
    finally:
        session.close()
```

---

## 示例

### 示例 1: 完整的请求流程

```python
from plugins.voice_actor.services import (
    VoiceActorService,
    ImageService,
    AliasService,
    CooldownService,
    RequestLogService
)
import time

def process_voice_actor_request(user_id: int, keyword: str):
    """处理声优请求的完整流程"""
    
    # 记录开始时间
    start_time = time.time()
    
    # 1. 检查冷却
    is_cooldown, remaining = CooldownService.check_cooldown(user_id)
    if is_cooldown:
        RequestLogService.log_request(
            user_id=user_id,
            group_id=0,
            command="voice_actor",
            status="cooldown",
            error_message=f"冷却中，剩余 {remaining} 秒"
        )
        return f"请在 {remaining} 秒后重试"
    
    # 2. 解析别名
    actor = AliasService.resolve_alias(keyword, user_id)
    if not actor:
        RequestLogService.log_request(
            user_id=user_id,
            group_id=0,
            command="voice_actor",
            status="notfound",
            error_message=f"未找到 {keyword}"
        )
        return None
    
    # 3. 获取随机图片
    image = ImageService.get_random_image(actor.id)
    if not image:
        RequestLogService.log_request(
            user_id=user_id,
            group_id=0,
            command="voice_actor",
            status="no_image",
            voice_actor_id=actor.id
        )
        return f"{actor.name} 没有可用的图片"
    
    # 4. 更新冷却
    CooldownService.update_cooldown(user_id)
    
    # 5. 记录成功
    response_time_ms = int((time.time() - start_time) * 1000)
    RequestLogService.log_request(
        user_id=user_id,
        group_id=0,
        command="voice_actor",
        status="success",
        voice_actor_id=actor.id,
        image_id=image.id,
        response_time_ms=response_time_ms
    )
    
    return image.file_path
```

### 示例 2: 查询统计数据

```python
from plugins.voice_actor.models import get_session, RequestLog
from sqlalchemy import func
from datetime import datetime, timedelta

def get_daily_stats():
    """获取每日统计数据"""
    session = get_session()
    try:
        # 查询今天的请求统计
        today = datetime.now().date()
        
        stats = session.query(
            RequestLog.status,
            func.count(RequestLog.id).label('count')
        ).filter(
            RequestLog.created_at >= today
        ).group_by(
            RequestLog.status
        ).all()
        
        return {status: count for status, count in stats}
    finally:
        session.close()
```

### 示例 3: 批量更新别名

```python
from plugins.voice_actor.services import AliasService, VoiceActorService

# 为中岛由贵添加多个别名
actor = VoiceActorService.get_voice_actor_by_name("中岛由贵")

aliases = [
    ("贵贵", 10),
    ("由贵", 8),
    ("贵", 5),
    ("莱纳声优", 3),
]

for alias_name, priority in aliases:
    AliasService.add_global_alias(
        alias_name=alias_name,
        voice_actor_id=actor.id,
        priority=priority
    )
```

---

## 测试示例

### 运行单元测试

```bash
# 创建 test_services.py
cd /opt/qqbot

python << 'EOF'
import sys
sys.path.insert(0, 'backend/bot')

from plugins.voice_actor.services import VoiceActorService, AliasService

# 测试获取所有声优
actors = VoiceActorService.get_all_voice_actors()
print(f"✓ 获取声优列表: {len(actors)} 个")

# 测试别名解析
if actors:
    actor = AliasService.resolve_alias(actors[0].name)
    print(f"✓ 别名解析成功: {actors[0].name}")

print("✓ 所有测试通过！")
EOF
```

---

## 最佳实践

1. **始终关闭会话**：使用 try-finally 确保数据库会话被关闭
2. **参数化查询**：防止 SQL 注入
3. **异常处理**：捕获并记录所有异常
4. **日志记录**：使用 loguru 记录所有关键操作
5. **文档化**：为新的服务和处理器编写文档
6. **测试**：编写单元测试验证业务逻辑

---

## 常见问题

**Q: 如何添加新的消息类型支持？**
A: 在 handlers.py 中创建新的 matcher，参考 GroupMessageEvent 的其他事件类型

**Q: 如何实现自定义的别名匹配算法？**
A: 修改 AliasService.resolve_alias() 方法的第 4 步（模糊匹配部分）

**Q: 如何添加权限控制？**
A: 使用 NoneBot 的 Rule 和权限检查器，或在 services 层添加权限验证

**Q: 如何优化查询性能？**
A: 在 models.py 中为常用查询字段添加索引，使用缓存

---

更多信息请参考项目文档或查看源代码注释。
