---
name: rensheng-youji-deep-report
description: 根据姓名（可选）、出生年月日时、性别、出生地点、可选现实资料与当前困惑，使用人生有迹统一确定性排盘和 rensheng-youji-mingli-core 完整分析母稿，经过五条现实事实校准后，生成“人生有迹｜完整报告”Markdown或PDF。用于用户要求完整八字报告、人生主线、性格成长、恋爱伴侣、事业、财务、身体情绪、家庭成长环境、长期阶段或逐年分析时；报告 Skill 免费公开，不需要验证码或人生有迹云端接口。
---

# 人生有迹｜完整报告

## 原则

- 始终复用仓库根目录的确定性排盘与 `rensheng-youji-mingli-core`，不得维护第二套四柱、大运、流年或命理分析规则。
- Core 负责生成完整 `analysis_bundle`；本 Skill 只负责现实校准、报告取材、篇幅组织与渲染。
- 报告与免费卡片必须来自同一套 Core，人生主线可以扩写，不能得出相反结论。
- 用户选择的关注方向只决定第4页“当前阶段与问题回应”、对应逐年提醒与行动优先级，不得改写完整人生主线、能力资源、形成过程或六个领域的基础判断。
- Skill 免费公开运行，不索要验证码，不调用人生有迹服务器。若当前AI不能运行Skill，可提示用户联系景行获得人工代生成、校准、排版与解释服务。
- 使用普通中文、条件式表达和可验证现实场景，不承诺事件，不用恐吓引导咨询。

## 两轮收集输入

### 第一轮：出生资料与关注问题

只要求三项排盘必填资料：

- 出生年月日和准确时间，24小时制；
- 出生城市、国家或地区；
- 性别，仅用于传统排运顺逆。

姓名可选，用户没有主动提供时不要追问。时间口径默认按普通钟表时间 `local_civil` 处理，不要额外增加一道问题；只有用户明确说明输入时间已经是真太阳时，才使用 `true_solar_adjusted`。中国出生地优先使用仓库内置地点库，重名时只补问省或地级市。

同时邀请用户提供一个关注方向或具体问题，二者有一个即可。具体问题已经能表明方向时，不要再让用户重复选择。用户只给“事业、学习、感情、家庭、财务”等方向而没有具体问题时，不得阻塞流程；在完成初始Core分析与五题校准后，根据当前阶段候选和已确认事实概括一个待回应问题，并明确它是系统概括，不冒充用户原话。

不要在第一轮集中索取当前城市、学历、专业、职业、关系状态、家庭阶段、收入、完整经历或正在比较的所有选项，也不要要求用户逐项回复“不知道”。

### 第二轮：五题校准与可选补充

生成五条校准题后，让用户一次回复五个题号和字母。根据关注方向，可以在校准题前附带一行“可选补充（可直接跳过）”，但不得把它设置为正式报告的前置条件：

- 事业或学习问题：可询问学历、专业、当前职业或学习状态；每项都非必答；
- 感情问题：可询问当前关系状态、反复出现的相处情况；每项都非必答；
- 家庭问题：可询问相关家庭关系、正在发生的矛盾或责任；每项都非必答；
- 财务问题：可询问收入来源、主要压力或现实责任；每项都非必答；
- 迁移或城市问题：可询问当前城市和正在比较的地点；每项都非必答。

用户可以只回复五个字母，忽略全部可选补充。此时继续生成正式报告，不得再次追问、降低交付规格或把空白当作负面事实。只把用户主动确认的资料写入 `reality_context`；未提供的学历、职业、关系、家庭、收入和经历必须保持未知，不能根据常见人群路径补造。

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
2. 从 Core 的 `reality_candidate_pool` 选择五组区分度最高的候选，写入同时包含 `display` 与 `audit` 的 `work/calibration-questions.json`；每题用A、B、C三个互斥的具体行为或经历候选加D“都不符合／不确定”，不再询问宽泛描述是否符合。五题至少覆盖四个生活领域，同一领域最多两题，用户关注方向最多两题；每条至少使用两个独立证据视角，不能只依赖日主旺衰。
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
   - [reality-anchor-language.md](references/reality-anchor-language.md)：事实型断语、现实名词精度与年度载体；
   - [prosperity-guide.md](references/prosperity-guide.md)：现实行动建议；
   - [brand-and-conversion.md](references/brand-and-conversion.md)：免费使用与人工服务入口；
   - [safety-language.md](references/safety-language.md)：健康、财务、关系和隐私边界。
2. 从已校验的 Core 母稿提取 `report.json`。正式报告使用 `schema_version=2.4.0`、`document_mode=full_calibrated`；必须填写固定 `focus_scope`，并从当前问题提取1—4个具体 `topic_keywords`。这些关键词在完整人生主线、能力形成和六领域基础正文中合计不得反复出现，只能在第4页、逐年提醒与行动优先级中重点展开。六个领域统一填写一个 `main_verdict`、一个 `reality_anchor`、一段 `pattern_and_cost` 和一个 `verification_point`。先判断工作或互动机制，再在证据允许的精度内使用大型国企、成熟科技公司、项目管理、固定工资、见面频率、住房安排等现实名词；不得为了明确而随意点名行业、岗位、对象身份或家庭经历。
3. 完整人生主线先根据原局全局、根苗花果、资源关系、家庭教育、事业财富、亲密关系和长期时运综合生成，再在第4页单独回答用户选择的问题。不得先确定用户关注方向，再反向筛选整份报告的证据。
4. 时间分析使用“大运交代阶段主题，流年负责激活和执行”，说明上一阶段、近几年、当前年与未来两三年的连续关系；同时概括更长的大运阶段。
5. 从同一份校准后 Core 母稿依次运行 `rensheng-youji-free-card-output` 与 `rensheng-youji-free-card-renderer` 的现有新版流程，生成 `work/free-card-output.json`。将卡片中实际高亮的桃花年份原样写入 `report.json.cross_output_consistency.relationship_opportunity_years`；若卡片全部留白则填写空列表，报告不得把其他年份写成明显关系进入或发展机会。不得复制旧卡片，也不得在报告目录另写卡片算法。
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

1. 固定品牌封面与报告介绍；
2. 完整人生主线、能力与可用资源；
3. 这些方式怎样形成；
4. 当前阶段与用户问题；
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
- 六个领域各自只有一个主判断，后续内容用于证明和落地，不再堆叠多组候选描述；
- 每个现实名词都进入来源审计；大型国企、互联网大厂、事业单位、具体岗位、收入形式等名词只有在用户事实或至少两个独立Core视角支持时才能出现；
- 事业、财务、关系、家庭与压力节奏均落到各自可核对的名词，不能只写“能力、资源、平台、稳定、成长”等宽泛类别；
- 完整人生主线与能力形成部分至少覆盖六个现实领域，不能围绕用户关注方向集中取材；
- 用户关注方向只在第4页、逐年回应与行动优先级中加重，不改变其他领域篇幅与基础结论；
- 用户可见正文不得出现日主、十神、天干地支、透干、身强身弱等内部命理术语；这些只保留在Core与审计字段中；
- “现在最值得做的三件事”、当前重点与未来方向不得把过去年份写成尚待执行的建议；
- 报告明显关系机会年份与卡片桃花年份完全一致；百分号等常用符号渲染后不得出现缺字方框；
- 校准答案选择了哪个现实候选，相关章节就引用哪个候选或用户补充事实，不得只提高置信度；
- 逐年观察使用项目交付、岗位调整、考试证书、合同、搬家、见父母、回款等现实载体；普通年份不强行虚构事件，重点年才增加细节；
- 已确认事实、命理推断、社会先验和待验证候选没有混写；
- 当前问题在开篇和相关章节获得直接回应；
- 报告完整回答后再出现人工服务入口，不故意保留关键结论；
- 健康不诊断、财务不保证、关系不承诺、年份不写成必然事件。

## 输出边界

未经用户授权，不上传出生资料，不把真实报告改写成宣传内容。公开案例必须去除可识别信息并标明“示例”。
