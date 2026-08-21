---
name: rensheng-youji-deep-report
description: 根据姓名（可选）、出生年月日时、性别、出生地点、现实经历与当前困惑，使用人生有迹统一确定性排盘和 rensheng-youji-mingli-core 完整分析母稿，经过五条现实事实校准后，生成“人生有迹｜完整报告”Markdown或PDF。用于用户要求完整八字报告、人生主线、性格成长、恋爱伴侣、事业、财务、身体情绪、家庭成长环境、长期阶段或逐年分析时；报告 Skill 免费公开，不需要验证码或人生有迹云端接口。
---

# 人生有迹｜完整报告

## 原则

- 始终复用仓库根目录的确定性排盘与 `rensheng-youji-mingli-core`，不得维护第二套四柱、大运、流年或命理分析规则。
- Core 负责生成完整 `analysis_bundle`；本 Skill 只负责现实校准、报告取材、篇幅组织与渲染。
- 报告与免费卡片必须来自同一套 Core，人生主线可以扩写，不能得出相反结论。
- Skill 免费公开运行，不索要验证码，不调用人生有迹服务器。若当前AI不能运行Skill，可提示用户联系景行获得人工代生成、校准、排版与解释服务。
- 使用普通中文、条件式表达和可验证现实场景，不承诺事件，不用恐吓引导咨询。

## 收集输入

第一次集中询问：

- 姓名，可留空；
- 出生年月日和准确时间，24小时制；
- 出生城市、国家或地区；
- 性别，仅用于传统排运顺逆；
- 时间是普通钟表时间，还是已经校正的真太阳时；
- 当前城市、学历、职业或学习状态、关系与家庭阶段；不知道时明确写“不知道”；
- 最想理解的方向和一个具体问题；
- 根据关注方向补充最少现实资料：事业需问学历/专业、当前工作状态、主要经历和正在比较的选项；关系需问当前状态、反复出现的相处情况和具体困惑；财务需问收入来源、主要压力和责任；家庭需问具体关系和正在发生的矛盾。

普通钟表时间使用 `local_civil`。只有用户明确说明已经校正为真太阳时，才使用 `true_solar_adjusted`。中国出生地优先使用仓库内置地点库，重名时只补问省或地级市。

## 统一 Core 工作流

1. 从当前目录向上定位包含 `internal/core-manifest.json` 的仓库根目录。
2. 运行根目录 `scripts/check_env.py`。缺少依赖时由当前AI运行根目录 `scripts/setup_env.py`。
3. 创建临时工作目录，不覆盖仓库文件。
4. 运行根目录确定性排盘并生成 Core 输入：

```bash
python scripts/prepare_core_input.py \
  --birth "1990-05-04 13:49" \
  --gender female \
  --city "北京" \
  --country "中国" \
  --time-basis local_civil \
  --analysis-as-of "YYYY-MM-DD" \
  --output work/core-input.json \
  --profile-output work/profile.json
```

5. 将用户明确提供的现实资料写入 `core-input.json.reality_context`。只记录用户原话能够支持的事实，不把推测写成事实。
6. 在生成分析前运行边界预检：

```bash
python skills/rensheng-youji-growth-map/scripts/preflight_report.py \
  work/core-input.json --focus "事业发展" --output work/report-preflight.json
```

若结果为 `blocked`，先核对出生分钟和出生区县。仍无法消除可能改变月柱、日柱、时柱或起运的边界时，只能生成标题明确的“人生有迹｜初步分析”，不得继续生成正式完整PDF。

7. 运行 Core 输入校验：

```bash
python internal/rensheng-youji-mingli-core/scripts/validate_analysis_input.py work/core-input.json
```

8. 完整读取 `internal/rensheng-youji-mingli-core/SKILL.md` 及其要求的全部参考文件，生成一次完整的 `work/analysis-output-initial.json`。
9. 运行 Core 输出校验：

```bash
python internal/rensheng-youji-mingli-core/scripts/validate_analysis_output.py work/analysis-output-initial.json
```

不得再读取本目录旧版 `core-method.md` 重新推命；该文件仅说明统一 Core 的使用边界。

## 五条现实校准

1. 完整读取 [calibration.md](references/calibration.md)。
2. 从 Core 的 `reality_candidate_pool` 选择五组区分度最高的候选，写入同时包含 `display` 与 `audit` 的 `work/calibration-questions.json`；每题用A、B、C三个互斥的具体行为或经历候选加D“都不符合／不确定”，不再询问宽泛描述是否符合。至少覆盖三个生活领域，每条至少使用两个独立证据视角，不能只依赖日主旺衰。
3. 运行 `validate_calibration_questions.py`，只把它生成的 `work/calibration-visible.md` 发给用户：

```bash
python skills/rensheng-youji-growth-map/scripts/validate_calibration_questions.py \
  work/calibration-questions.json --visible-out work/calibration-visible.md
```

不得自行把 `audit`、候选编号、盘面支持、置信度、替代解释或任何命理证据附在问题后面。
4. 让用户只回复题号和字母；鼓励在最关心的一至两题后补充一个具体事实或年份，但不能要求用户先懂命理。
5. 将五个选择完整写入 Core 输入的 `calibration` 和报告的 `calibration.responses`；A/B/C记录对应候选编号，D记录为空候选。用户补充内容同时写入 `reality_context` 与 `responses.user_note`。保留未选择候选，不得为了迎合反馈修改四柱、原局结构或大运流年事实。
6. 在初始完整母稿上只更新校准状态、用户事实、受影响的现实映射与置信度，保留其余已完成章节；生成并校验 `work/analysis-output-calibrated.json`，避免把没有变化的32个章节整份重新写一遍。
7. 用户跳过任何一条时，`document_mode` 必须为 `preliminary_uncalibrated`，标题必须为“人生有迹｜初步分析”，只交付初步 Markdown 和新版卡片；不得生成或称为正式完整PDF。

## 报告提取与输出

1. 完整读取：
   - [full-report.md](references/full-report.md)：章节结构、Core字段来源和篇幅；
   - [report-schema.md](references/report-schema.md)：报告JSON契约；
   - [audience-continuity-language.md](references/audience-continuity-language.md)：白话和时间连续性；
   - [prosperity-guide.md](references/prosperity-guide.md)：现实行动建议；
   - [brand-and-conversion.md](references/brand-and-conversion.md)：免费使用与人工服务入口；
   - [safety-language.md](references/safety-language.md)：健康、财务、关系和隐私边界。
2. 从已校验的 Core 母稿提取 `report.json`。正式报告使用 `schema_version=2.2.0`、`document_mode=full_calibrated`；六个领域必须填写各自的 `specific_judgments`，让性格落到习惯和处理方式、事业落到行业/岗位/任务候选、财务落到收入来源、关系落到吸引与互动、家庭教育落到角色与路径。不得重新推命，不得从人口常见路径补造用户经历。
3. 报告开头依次写能力与可用资源、这些方式怎样形成、当前阶段怎样发展，再展开六个领域。
4. 时间分析使用“大运交代阶段主题，流年负责激活和执行”，说明上一阶段、近几年、当前年与未来两三年的连续关系；同时概括更长的大运阶段。
5. 从同一份校准后 Core 母稿依次运行 `rensheng-youji-free-card-output` 与 `rensheng-youji-free-card-renderer` 的现有新版流程，生成 `work/free-card-output.json`。不得复制旧卡片，也不得在报告目录另写卡片算法。
6. 运行统一交付命令：

```bash
python skills/rensheng-youji-growth-map/scripts/generate_full_report.py \
  --report work/report.json \
  --free-card work/free-card-output.json \
  --out-dir work/delivery \
  --keep-pages
```

7. 正式交付固定包含新版1242×1660卡片PNG、Markdown、恰好10页的PDF和 `report-delivery-manifest.json`。PDF第2页必须嵌入刚刚生成的同一张新版卡片；不得让用户模型自行决定版式、页数、换行、颜色或二维码位置。

## 用户可见进度

只使用以下短提示，不展示文件路径、Schema、候选编号、程序日志或内部推理：

1. “正在核对出生时间与排盘口径。”
2. “排盘已完成，正在准备五条现实校准。”
3. “已收到校准结果，正在整理人生主线与各领域分析。”
4. “正在生成新版人生卡片与10页完整报告。”
5. “文件已生成，正在检查页数、换行、二维码和内容完整性。”

## 报告固定结构

1. 基本信息与排盘口径；
2. 能力与可用资源；
3. 这些方式怎样形成；
4. 人生主线、当前阶段与用户问题；
5. 性格与内在成长；
6. 恋爱与伴侣；
7. 事业发展；
8. 财务与资源；
9. 身体与情绪；
10. 家庭与成长环境；
11. 阶段与逐年观察；
12. 现实行动、仍需验证、关于景行与阅读边界。

## 完成检查

- `source.analysis_id`、`source.core_version` 与 Core 母稿一致；
- 正式PDF前已经完成五条校准且时间边界预检通过；
- 四柱、时间口径和大运事实未被改写；
- 第2页为同一 Core 生成的新版人生卡片，卡片尺寸为1242×1660；
- PDF恰好10页，所有正文无截断，微信二维码实际嵌入，标题/重点/正文有稳定颜色层级；
- 用户可见校准题中没有候选编号、置信度、盘面支持或命理证据；
- 不包含“初始角色、核心配置、主线任务、人物小传”等旧卡片字段；
- 六个领域均有实质内容或明确写证据不足，不能把事业段落换词复制到其他领域；
- 六个领域的具体判断槽位全部通过语义验收；行业、岗位、财富来源和吸引类型不能只写宽泛类别；
- 校准答案选择了哪个现实候选，相关章节就引用哪个候选或用户补充事实，不得只提高置信度；
- 已确认事实、命理推断、社会先验和待验证候选没有混写；
- 当前问题在开篇和相关章节获得直接回应；
- 报告完整回答后再出现人工服务入口，不故意保留关键结论；
- 健康不诊断、财务不保证、关系不承诺、年份不写成必然事件。

## 输出边界

未经用户授权，不上传出生资料，不把真实报告改写成宣传内容。公开案例必须去除可识别信息并标明“示例”。
