# 运行统计与可观测性

## 部署前迁移

生产数据库不会在应用启动时自动执行 `ALTER TABLE`，`database/init.sql` 也只用于全新数据卷。升级存量环境前：

1. 停止投递新版本，先对 MySQL 做完整备份并验证备份可恢复。
2. 使用当前生产环境的数据库连接配置运行显式迁移：

   ```bash
   cd /app
   python -m bot.manage migrate-observability
   ```

   非交互式维护窗口可在已确认备份后追加 `--yes`。命令会检查当前列和索引，只执行缺失的 DDL；重复运行会显示无需修改。

3. 确认 `request_logs.user_id/group_id` 为 `BIGINT`、`error_code` 已存在，并存在 `(created_at, status)`、`(created_at, command)` 复合索引。
4. 再构建并重启 NoneBot 与前端。不要把重新执行 `init.sql` 当作存量升级方式。

## 运行参数

所有参数都有适合单实例机器人的默认值：

- `OBSERVABILITY_QUEUE_CAPACITY=2048`
- `OBSERVABILITY_BATCH_SIZE=50`
- `OBSERVABILITY_FLUSH_INTERVAL_SECONDS=0.5`
- `OBSERVABILITY_SHUTDOWN_TIMEOUT_SECONDS=10`
- `OBSERVABILITY_RETENTION_DAYS=30`
- `OBSERVABILITY_RETENTION_INTERVAL_HOURS=24`
- `OBSERVABILITY_SYSTEM_SAMPLE_SECONDS=5`

队列满时事件会被丢弃；批量写入和留存清理失败只增加计数并写服务日志，不会向消息处理器抛错。停机时会在超时范围内尝试排空队列。

## 接口

- `GET /health`：只表示进程存活，不访问外部依赖。
- `GET /admin/api/readiness`：分别报告数据库和 OneBot 连接状态。
- `GET /admin/api/metrics?range=24h|7d|30d`：返回请求量、成功率、耗时百分位、活跃用户/群、状态分布、趋势、热门声优、错误码、队列和系统资源。

新事件不写 `error_message`，只写稳定的 `error_code`。普通未匹配群消息不会产生记录；只有明确 @机器人的无结果查询会记录 `notfound`。
