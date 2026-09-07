# 五道现实校准规范 v3.0

## 核心边界

校准像给已经画好的地图确认路标：它能确认哪条现实表现更接近用户，也能降低或保留某个候选，但不能重画四柱、原局结构、大运流年、九方法技术结论或冻结Core。

题目固定为五道。程序从冻结Core选择五个个人待核对点，必须满足：

- 至少覆盖四个报告领域，同一领域最多两题；
- 至少两题属于客观状态或已发生事件；
- 至少一题是带时间范围的 `timed_event`；
- 五题不得重复同一个 `domain + reality_dimension`；
- 证据较弱候选不得为了凑够五题进入题单。

## 题目怎样产生

Core中的每个可校准候选已经包含个人化材料：

- `validation_question`：要核对的问题；
- `statement`：候选表现；
- `alternative_statement`：相反或替代路径；
- `time_scope`：观察范围；
- `related_claim_ids`：会影响哪些报告判断；
- `candidate_kind`、`domain`、`reality_dimension`：用于覆盖与去重。

`build_calibration_questions.py` 对候选确定性评分，优先顺序为待校准判断、条件判断、独立补充、阶段判断、主要判断，并对用户关注领域适度加分。程序枚举满足覆盖条件的五题组合，再选总分最高的一组；相同输入永远得到相同五题。

每题统一为：

- A：候选陈述，程序记为 `match`；
- B：替代陈述，程序记为 `reject`；
- C：两种情况按环境、关系或阶段出现，程序记为 `partial`；
- D：用户自己描述。

通用模板只规定这四种比较方式，不提供全局固定问题。用户可见文字来自当前冻结Core，因此程序了解的是本人的命理分析候选，不是拿一套人人相同的问卷来问。

## 确定性生成与校验

```bash
python scripts/run_in_env.py skills/rensheng-youji-growth-map/scripts/build_calibration_questions.py \
  --analysis work/analysis-baseline.json \
  --focus "事业发展" \
  --output work/calibration-questions.json

python scripts/run_in_env.py skills/rensheng-youji-growth-map/scripts/validate_calibration_questions.py \
  work/calibration-questions.json \
  --analysis work/analysis-baseline.json \
  --visible-out work/calibration-visible.md
```

问题文件使用 `schema_version=3.0.0`、`template_version=2.0.0`，并由程序写入 `source.analysis_id` 和 `source.baseline_sha256`。校验器会重新从同一个Core计算哈希、显示内容、候选绑定、答案影响、领域覆盖和时间题覆盖。内部候选编号、判断编号、命理证据和置信度不得进入 `calibration-visible.md`。

## 自由回答

A/B/C不调用AI。只有用户选择D并填写自己的文字时，才调用一次小型AI，输出 `calibration-free-text-patch.json`：

```json
{
  "schema_version": "1.0.0",
  "responses": [{
    "question_number": 2,
    "user_text": "用户原文，不改写",
    "facts": ["从原文提取的具体事实"],
    "candidate_updates": [{
      "candidate_id": "本题已经绑定的候选",
      "status": "match|partial|reject|uncertain",
      "reason": "只根据用户原文解释"
    }]
  }]
}
```

这个AI只做“听懂用户的话”，不负责抄写分析编号或Baseline哈希，不能新建候选，也不能修改其他题。每个D答案必须且只能更新本题已经绑定的一个候选；即使用户表达不确定，也应将它标为 `uncertain`，不能返回空更新。先运行：

```bash
python scripts/run_in_env.py scripts/validate_calibration_free_text.py \
  work/calibration-free-text-patch.json \
  --baseline work/analysis-baseline.json \
  --questions work/calibration-questions.json
```

## 编译校准增量

五个答案保存为 `calibration-answers.json`，每项只含 `question_number`、`choice` 和可选 `free_text`。然后运行：

```bash
python scripts/run_in_env.py scripts/compile_calibration_delta.py \
  --baseline work/analysis-baseline.json \
  --lock work/analysis-baseline-lock.json \
  --questions work/calibration-questions.json \
  --answers work/calibration-answers.json \
  --free-text-patch work/calibration-free-text-patch.json \
  --output work/calibration-delta.json
```

没有D答案时省略 `--free-text-patch`。编译器验证五题不缺不重、用户原文与补丁一致、自由补丁只覆盖D问题，并把用户事实只连接到对应候选和判断。之后再使用 `apply_calibration_delta.py` 合成校准后Core并用Baseline锁校验受保护字段。

校准结果只决定候选的现实确认状态和报告选材。没有被选中的兼容、互补、条件或阶段候选继续保留；只有用户事实明确否定且与当前候选真实互斥时才排除。
