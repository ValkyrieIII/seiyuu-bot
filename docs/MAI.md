# MaiBot (麦麦) 桥接

在现有声优机器人旁边接入 [MaiBot](https://github.com/Mai-with-u/MaiBot) 作为"外挂 LLM 大脑"：
麦麦以 headless 方式运行在独立容器中，**不直连 QQ**；所有群消息由 nonebot 经
maim_message 协议单向喂给它，它的自主回复经桥接投递回群。

## 架构

```
QQ ──NapCat──> nonebot
                ├─ p20 mention_command（签到/列表）
                ├─ p50 voice_actor（别名→发图）
                └─ p60 mai_bridge
                     ├─ 转发所有群文本（自身发言/功能命令除外）
                     │    └── maim_message ──> mai 容器（headless MaiBot）
                     └─ 收到麦麦回复 ──OneBot──> 发回群（白名单+观测）
```

为什么不是把 NapCat 直连给两套 bot：一个 QQ 号同一时刻只能有一个"意识所有者"，
双消费端会导致双回复与自循环。桥接让消息流只有一条链，裁决权收敛在 nonebot。

## 启用步骤

1. **准备配置**（部署机 `maibot/config/` 下）：

   ```bash
   cp maibot/config/bot_config.toml.example maibot/config/bot_config.toml
   cp maibot/config/model_config.toml.example maibot/config/model_config.toml
   # 编辑 model_config.toml 填入 DeepSeek API Key
   # 编辑 bot_config.toml 将 auth_token 与 env 中 MAI_AUTH_TOKEN 保持一致
   ```

   `*.toml` 含密钥已被 .gitignore 忽略，只提交 `.example` 模板。

   > 注意：`bot_config.toml` 的 `[bot] platform` 必须与桥接端 `MAI_PLATFORM_NAME`（默认
   > `qqbot`）一致、`qq_account` 填机器人 QQ——Platform IO 依据它注册发送路由，留空会导致
   > 麦麦能生成回复但报 "未命中任何发送路由" 发不出来。首启后麦麦会自动补全配置文件，
   > 升级镜像后注意核对该段是否被保留。

2. **开启环境开关**（`.env.dev` 或 `.env.prod`）：

   ```bash
   COMPOSE_PROFILES=qq,mai      # dev 默认无 profiles 变量时按需追加
   MAI_ENABLED=true             # 总闸：false 时插件零行为
   MAI_IMAGE=sengokucola/maibot:1.2.3   # prod 必须固定版本
   MAI_AUTH_TOKEN=<与 bot_config.toml 一致>
   ```

3. **启动**：

   ```bash
   docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml up -d
   ```

4. 首次启动后建议访问麦麦 WebUI 完成人设初始化与行为微调。生产环境将 8001 映射到
   宿主机 `127.0.0.1:${MAI_WEBUI_PORT:-18001}`（仅本机），远程访问走 SSH/VS Code 端口转发。

### 生产环境专项说明

deploy.sh 只更新 nonebot/frontend，**永远不会拉起或触碰 mai 容器**，因此生产首次
启用需在上面第 3 步的命令基础上手动执行一次；此后 mai 与 mysql/napcat 同类，
属常驻基础设施，业务发版不影响它。升级麦麦只需修改 `.env.prod` 中 pin 的
`MAI_IMAGE` tag 后重跑同一条命令。

> 内存前提：麦麦核心镜像（faiss/scipy/pandas 等）常驻约 1-2GB，启用前先
> `free -h` 确认服务器余量充足。

## 行为规则

| 规则 | 实现 |
|---|---|
| 机器人自己的消息永不外传 | `should_forward(is_self)` —— 切断自循环 |
| @机器人 "签到/声优列表" 不进麦麦语境 | 归 mention_command 车道 |
| 其他一切群文本（含命中别名的）都作为上下文外传 | 麦麦自主决定是否插话 |
| 发送节奏 | 由麦麦自身聊天频率控制，桥接层不拦截（历史内置限速器已移除，曾导致多段回复被静默吞掉） |
| 回复长度上限 | `MAI_MAX_REPLY_LENGTH`（默认 1500 字符截断） |
| 群范围 | `MAI_ALLOWED_GROUPS` 逗号分隔白名单，空=全部（同时约束出入站） |

## 观测

接入现有 request_logs 体系，`command="mai_chat"`：

- `success`：麦麦回复成功投递
- `error/MAI_DELIVER_FAILED`：OneBot 发送失败
- `error/GROUP_NOT_ALLOWED`：目标群不在白名单

可在 admin 后台概览页查看请求量与成功率。

## 升级与维护

- 麦麦核心走官方镜像，升级 = 改 `MAI_IMAGE` tag 后 `up -d`；
- SQLite 数据与表情包缓存在命名卷 `mai_data`；
- 配置变更改 `maibot/config/*.toml` 后重启 mai 服务即可，nonebot 不动；
- 插件开发见官方 [插件文档] 与仓库 `plugins/hello_world_plugin` 示例。

## 常见问题

**Q: 麦麦一直不说话？**
检查 `mai` 容器日志确认 maim_message server 已监听 8000 且 token 校验通过；
确认模型任务列表已正确指向可用 LLM（WebUI 内可看调用统计）。

**Q: 会重复加图片吗？**
麦麦自带表情包/图片工具（发送自己缓存的内容），与声优图库互不相干。
若不想让它发自带图，可在 WebUI 关闭对应工具或限制 expression 配置。

**Q: 成本怎么估？**
默认 deepseek-v4-flash 计价约 $0.14/$0.28 每百万 tokens（输入/输出），
日常群聊一天通常在几毛钱人民币量级；上下文越长成本越高，可调低记忆窗口。
