"""麦麦（MaiBot）桥接插件。

将群消息单向转发给 headless 部署的 MaiBot（maim_message Legacy WS），
并把麦麦的自主回复经 OneBot 投递回群。核心规则：

- 永不转发机器人自己的发言（切断自循环）
- @机器人 的功能命令（签到/声优列表）归 mention_command，不外传
- 出站回复受最小间隔限速与群白名单双重约束
- MAI_ENABLED=false 时整个插件零行为，等同于不存在

本包导入必须保持零副作用（Matcher 注册交给 .handlers，
客户端启动为首条消息到达时的惰性引导），以兼容测试环境直接导入 .router。
"""

from . import handlers  # noqa: F401  导入即注册 Matcher
