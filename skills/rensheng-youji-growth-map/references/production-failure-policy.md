# 正式生产失败与探索性错误

## 正式运行目录

仓库、`venv`、本次Core、方法包、校准文件和报告文件不得放在 `/tmp`、`/var/tmp`、`/private/tmp` 或其他会在对话轮次间清理的目录。先运行 `create_report_run.py`，后续只使用其返回的绝对 `work_dir`。每次跨轮继续前运行 `report_pipeline.py status`；仓库或运行目录不存在时重新安装，但不要把新的安装再次放进临时目录。

## 什么情况必须停止

只有以下情况属于正式生产失败：

- 主Skill明确列出的正式脚本或校验器返回非零状态；
- 主Skill或其必读清单明确声明的文件缺失；
- 正式Schema、输入哈希、Baseline锁或报告来源一致性失败；
- 达到该阶段规定的局部修复次数上限；
- `delivery_decision=preliminary_only` 却被要求继续正式报告。

停止时报告阶段、正式命令和原始错误。不得用旧文件、测试夹具或占位内容绕过。

## 什么情况不得停止

以下属于探索性错误，AI应纠正自己的读取方式后继续，不得宣告生产失败：

- 自行猜测的文件名不存在；
- `rg`、`find`或查看可选文件没有结果；
- 非Skill声明的Schema、示例或辅助文件不存在；
- 为理解代码而执行的只读命令参数写错。

不得把多条探索命令用 `&&`、管道或其他组合方式包装成一个正式阶段。每条正式生产命令单独执行。方法包唯一正式结构入口为 `internal/rensheng-youji-mingli-core/schemas/method-packet.schema.json`；不得自行寻找或假设存在 `method-analysis.schema.json`、`method_packet.schema.json` 等其他名称。
