---
name: rensheng-youji-mingli-core
description: 人生有迹内部八字分析核心。仅供人生有迹卡片、报告、网页或其他上游流程在已经取得确定性四柱、大运与流年数据后调用，用于让格局、气势意向、调候、十神、根苗花果、盲派、岁运等方法各自独立完成命理推演与现实候选，再生成可追溯的综合人物母稿。不直接面向终端用户，不负责排盘、视觉渲染、篇幅压缩或决定卡片与报告展示哪些内容。
---

# 人生有迹内置命理分析核心

## 定位

接收确定性排盘数据和可选现实资料，生成统一的 `analysis_bundle` 完整分析母稿。让卡片、免费报告、付费报告、网页和咨询流程从同一份分析中自行选择、压缩和改写，不允许各自重新推演出彼此矛盾的结论。

始终完整分析。不要根据调用方是免费卡片还是付费报告而省略推理，不要决定哪些内容展示、隐藏或收费。

不要向终端用户介绍本核心、文件结构、内部字段或调用方式。由下游产品负责用户交互。

## 输入前提

只在上游已经用确定性历法程序完成排盘后运行。禁止使用语言模型口算日柱、节气、起运或大运。

要求输入至少包含：

- `request`：分析基准日期、时间范围、历法和时区口径；
- `person`：姓名可选，出生年月日时、出生地、性别；
- `chart`：四柱、各柱十神、地支主气/中气/余气及对应十神；
- `solar_terms_and_boundaries`：节气、日界、时辰边界和真太阳时处理结果；
- `five_elements`：确定性权重结果可选；没有固定算法时必须为 `null`；
- `luck_cycles`：起运时间、顺逆、每步大运干支、藏干和时间范围；
- `annual_cycles`：目标年份的流年干支、藏干与年龄；
- `reality_context`：职业、学历、家庭、关系、城市、经历、困惑等可选事实；
- `calibration`：历史候选、用户反馈和已确认事实，可选。

若四柱、大运或目标流年缺失，返回缺失字段，不继续猜测。若出生时间、地点、节气、日界、时辰或起运存在边界问题，保留输入版本并标记不确定性；不要自行替上游改盘。

输入的机器可读契约见 [analysis-input.schema.json](schemas/analysis-input.schema.json)。开始分析前运行：

```bash
python scripts/run_in_env.py internal/rensheng-youji-mingli-core/scripts/validate_analysis_input.py <analysis-input.json>
```

校验失败时返回错误字段并停止推理。

若上游来自现有 `rensheng-youji-api` 的 `build_profile()`，先运行适配器补齐藏干层级、大运与流年的十神数据：

```bash
python scripts/run_in_env.py internal/rensheng-youji-mingli-core/scripts/adapter_from_api_profile.py <profile.json> \
  --analysis-as-of YYYY-MM-DD \
  --output analysis-input.json
```

适配器只转换并补全确定性结构，不继承旧免费卡片中的角色标签、文案判断或 K 线评分作为 Core 结论。

## 参考规则目录与阶段路由

下列文件是完整规则库，不是每个AI阶段都要重复读取的提示词。九方法阶段禁止完整加载本Skill、完整Core Schema和下列全部参考文件；应由 `build_method_prompt_packs.py` 为每种方法生成“共同短规则＋本方法专用提示＋唯一method-input”的隔离提示包。完整长文继续作为规则来源与维护依据。

1. [analysis-workflow.md](references/analysis-workflow.md)：执行完整二十四步流程和最终质检。
2. [natal-structure.md](references/natal-structure.md)：分析月令、全局势、格局、调候、十神网络和刑冲合化。
3. [branch-qi-and-roots.md](references/branch-qi-and-roots.md)：逐支分析主气、中气、余气、全部十神、透干和根气。
4. [root-seed-flower-fruit.md](references/root-seed-flower-fruit.md)：建立根苗花果的时间顺序与同时共存映射。
5. [social-reality.md](references/social-reality.md)：建立年龄、性别、城市、家庭与职业阶段的现实人物模型。
6. [resource-and-domain-links.md](references/resource-and-domain-links.md)：分析人与资源的关系和事业、财富、关系、家庭等领域传导。
7. [complete-person-and-relationship-portrait.md](references/complete-person-and-relationship-portrait.md)：生成完整自身画像、家庭系统、人际与亲密关系、对象特质候选、互动模式、不可推断清单和画像均衡审计。
8. [luck-cycle-theme.md](references/luck-cycle-theme.md)：确定每步大运的阶段主题、激活键和前后承接。
9. [annual-activation.md](references/annual-activation.md)：按大运主题分析流年执行、相邻年份连续性和伏笔。
10. [blind-school-cross-method.md](references/blind-school-cross-method.md)：用宾主、体用、做功和多层象法生成组织、行业、岗位、工作对象与成果形式候选，并保留不同作者口径与禁断边界。
11. [independent-method-analysis.md](references/independent-method-analysis.md)：强制九种方法隔离推演、分别生成技术结论和现实候选，再按方法家族独立性综合；规定单方法补充和冲突处理。
12. [method-failure-and-recovery.md](references/method-failure-and-recovery.md)：规定逐方法校验、三轮局部修复、失败状态、最低方法覆盖和降级交付。
13. [core-production-bridge.md](references/core-production-bridge.md)：把已校验方法包确定性汇总为综合输入，约束AI语义综合，再由程序组装完整Core与报告来源。
14. [calibration-confidence.md](references/calibration-confidence.md)：生成现实候选，吸收用户反馈并标注置信度。
15. [candidate-relations-and-calibrated-synthesis.md](references/candidate-relations-and-calibrated-synthesis.md)：校准前建立候选关系并冻结完整人物，校准后只以增量调整现实候选状态。
16. [domain-independent-analysis.md](references/domain-independent-analysis.md)：先完成六个领域各自的判断、机制与覆盖，再限制共享主线比例和跨章复用。
17. [report-grade-reality-mapping.md](references/report-grade-reality-mapping.md)：建立开放现实候选、人物形成链、领域联动链和报告级判断台账。
18. [safety-boundaries.md](references/safety-boundaries.md)：执行非宿命表达、高风险边界和不确定性披露。
19. [post-calibration-report-selection.md](references/post-calibration-report-selection.md)：冻结报告候选池，并在校准后确定性生成最终选材与单章降级状态。

阶段读取规则：

- 九方法AI：只读取 `method-prompt-packs/<method_id>.prompt.md`，不得另读上述完整规则库；
- Core综合AI：在METHOD GATE通过后读取生产桥、人物画像、社会现实、领域独立、现实映射与安全边界等综合规则；
- 校准与报告阶段：只在各自阶段读取校准、候选关系和报告选材规则；
- Schema、哈希、重试次数、方法身份、六领域编号映射和证据编号由确定性程序处理，不作为AI提示内容。

## 执行规则

### 1. 先事实，后解释

先冻结确定性排盘事实，再开始推理。将事实、命理推断、社会先验、用户事实和待验证候选分开记录。较低层证据不得改写较高层事实。

### 2. 采用双轨建模

先生成不读取现实经历的“命盘结构轨”，并在这一轨内完成每个方法的技术结论、现实候选和方法综合冻结；再生成只基于用户事实和保守社会常识的“现实人物轨”，最后交叉合并。两轨冲突时保留冲突和替代解释，不要强行圆盘。不得因为输入中已经带有现实经历，就在独立方法阶段提前吸收这些答案。

### 3. 完整展开地支

原局、大运和流年的每个地支都分析主气、中气、余气及其相对日主的十神。继续检查透干、通根、得令、受制、被合冲和时运激活。不得只看地支本气。

### 4. 先看全局势，再看局部作用

刑冲合害破必须放回月令、根透、制化、调候和全局气势判断。不得见冲即凶、见合即吉，不得在条件不足时认定合化、从格或成局。

盲派象法与技法只作为交叉层，但必须在现实候选形成之前完成。先分别记录宾主、体用、做功路径、结果归属、成本、虚实与完整性，再从组织形态、行业生态、岗位职能、处理对象、发展方式、成果形式和工作环境七个维度生成取象候选，并与格局调候、根苗花果、资源关系和岁运连续性核对。作者特有规则不得冒充独立共识；高置信结论必须至少有一种非盲派方法支持。

### 5. 强制每种方法独立推演

格局成败、气势意向与形象方局、调候、十神网络、根苗花果、盲派和岁运连续性必须分别只读取由 `prepare_method_input.py` 生成的主题隔离输入，各自产生命理技术结论与现实候选；宫位六亲、干支根气另作部分独立分析。任何方法不得读取用户关注方向、现实答案或其他方法已经生成的结论后再改写成同一方向。全部方法冻结后，综合层才可以归并同向、互补、条件、阶段、上下位和真正冲突。

多方法一致必须按不同主要方法家族计算，不能把扶抑、病药、通关、旺衰、根透、刑冲合害等同源术语拆成多票。只有至少两个不同主要方法家族独立同向时，结构置信度才可为高。单一主要方法若新增实质信息、条件明确、可观察且没有事实冲突，可以保留为补充判断。

每个完整方法先逐项检查六个报告领域。现实候选的 `domain` 只允许 `self_growth`、`love_partner`、`career`、`finance_resources`、`body_emotion`、`family_growth`；学习、教育、迁移和地域变化作为这些领域中的现实问题轴处理。每个领域允许0—5条候选、不设最低数；完整方法通常保留8—14条真正不同的候选，证据少时可以更少，总数最多18条、技术结论最多12条。没有候选时登记 `insufficient_evidence` 或 `not_applicable`。十神动力、宫位六亲、干支动力、盲派和岁运连续性是关系锚点，必须实际检查 `love_partner`。输出错误最多进行三轮局部修复；第三轮仍失败则记录真实失败并排除计票。不得因单个部分方法失败或某个报告领域缺少候选而停止其他可靠内容，也不得让 `preliminary_only` 进入完整报告。

### 6. 把命盘当作现实中的人

结合年龄、性别、所处年代、城市、家庭、教育和职业阶段推断现实入口。年龄只限定候选范围，不能直接决定当前课题。社会常识只能作为先验，不能冒充命盘“算中”的事实。

### 7. 同时分析根苗花果

既分析年、月、日、时的时间顺序，也分析根、苗、花、果在一个人身上的同时共存、家族传承和各领域生命周期。根可以是家庭、地域、长期资源或事业扎根；苗与枝干可以是学历技能、组织训练和资源输送；花可以是关系吸引、传媒媒介、对外形象、作品和阶段展示；果可以是职位、资产、产品、声誉、子女与下一代沉淀。不得把四柱固定翻译成家庭、教育、表达和制度成果。

### 8. 分析人与资源的关系

分别分析物质、制度、人际、能力、时间精力和心理资源的获得、保存、交换、放大与损耗方式。说明十神链条如何转化为现实资源链。

### 9. 以大运为主题、流年为执行

先确定大运的十年主题，再检查流年天干、地支和藏干怎样重复、透出、引动或改变大运与原局。使用以下链条：

> 大运主题 → 流年触发 → 原局反应 → 人的选择与行为 → 社会反馈 → 阶段结果 → 下一年伏笔

不得脱离原局和大运单独评价流年。

### 10. 保持时间连续

每年说明从上一年带入什么、本年如何执行、本年沉淀什么、给下一年留下什么。人的技能、合同、关系、资产、责任和社会位置具有惯性，不得把相邻年份写成突然翻转的独立吉凶。

### 11. 连接现实领域

事业、财富、学习、关系、家庭、迁移、健康与成长不得割裂。记录来源领域、传导机制、目标领域、时间滞后、放大条件和缓冲条件。

### 12. 校准而不倒推

生成10—24个可证伪现实候选，尽量覆盖六个报告领域，并逐条标注固定领域、现实维度、候选类型、时间范围、实体证据和受影响的报告判断。提出问题前必须先建立候选关系图，区分可共存、互补、主次、阶段、情境、上下位和真正互斥。程序只从中选择最有区分度的五个候选，用统一比较结构生成同一现实问题轴下的A/B/C/D，不让AI自由选题。

吸收用户选择、D“都不符合／不确定”和补充事实时，不能把“未选择”等同于“被否定”。得到校准的候选分别进入主要确认、未选但仍受支持、条件成立、降低优先、明确排除或仍不确定。只有在相同时间、相同口径和相同比较轴下真正互斥时，才排除未选候选。不得倒改四柱和结构事实，也不得因为用户只选A就把完整人物写成单一A类型。

每条现实候选至少引用两个独立证据视角，并至少包含根苗花果、资源关系、交叉方法、大运主题、流年执行或领域联动之一；日主旺衰只能作为组成证据，不能单独生成现实候选。校准题的用户可见文字与内部命理审计必须分离。

用户填写的关注方向和当前问题只用于排列“当前阶段回应、年度提醒与行动建议”的优先级，不是命理证据，也不得反向改写完整自身画像、家庭形成、能力资源、人生主线或六个生活领域的基础判断。必须先完成全盘母稿，再把关注方向放入当前阶段中回应。

校准只能确认、部分支持、排除或保留原有候选。不得把用户回答扩写成新的人格类型、职业标签、健康标签或新的报告判断。初始Core冻结后，校准不得重写 `portrait_thesis`、判断正文、机制、证据或报告候选池。最终报告名单必须在校准后由确定性选材程序生成，不属于Baseline中预先锁定的内容。

### 13. 先判断工作属性，再生成开放现实候选

不得把十神、旺衰或单一结构直接等同于职业。先判断规则密度、自主程度、专业门槛、风险承受、平台依赖、处理对象、工作节奏和发展方式，再从工作方式、组织属性、行业、职能、岗位、收入机制等不同维度生成候选。

现实候选体系必须开放。公务员、事业单位、国企、民企、外企、专业机构、初创公司、自由职业、个体经营、创业、主业加副业等只是一部分示例，不是封闭词库。新增候选必须说明所属维度、现实属性、支持证据、反证、置信度和禁止外推范围。

### 14. 为报告准备完整材料，不替报告写文章

除完整技术母稿外，还要生成：

- 校准前完成并冻结的完整人物总判断；
- 候选之间的共存、主次、阶段、条件和互斥关系图；
- 校准前后每条现实判断的变化记录；
- 具有固定编号的报告判断台账；
- 3—6条人物形成链；
- 3—6条跨领域联动链；
- 完整人生主线素材；
- 六个现实领域优先各4—6条真正不同的报告级判断；证据较少时允许2—3条或明确证据缺口；
- 可以使用的具体例子与禁止外推范围。

这些内容用于约束报告写作，不是用户可见文章。Core中的技术短语必须紧接现实解释；不得用“底色、表达窗口、输出、可见度、先扎根后显声”等抽象词代替事实。

每条报告判断必须登记可解析的证据编号。证据编号要指向真实的 `evidence_registry` 条目，写明方法、命盘位置、观察、解释、限制和置信度。不能只造两个看似不同的编号来满足数量。每条判断还要标注 `origin`：原局长期判断使用 `chart_baseline`，大运流年阶段判断使用 `timing_baseline`，用户校准只使用 `user_fact_refinement`。校准不能成为完整人生主线和六个领域的主要来源。

每条报告判断同时登记：

- `claim_family`：它回答的是该领域哪一类问题；
- `mechanism_family`：主要来自哪条结构或时运路径；
- `new_information`：相对同领域其他判断新增了什么；
- `plain_claim`：不含命理术语、可以原句进入报告的完整判断句。

判断充足的领域优先覆盖三个判断家族、两个机制家族和三个现实问题轴；判断较少时按证据缩短。不同编号但语义高度相似的句子视为重复，不得用换词满足数量。`report_source_bundle` 必须由脚本根据判断台账生成稳定优先级、0—2条必进候选和实际覆盖映射；有可用判断时至少提供1条，稀疏的当前阶段来源允许只有1条。不得让模型手工复制ID，也不得在校准前锁定最终 `mandatory_claim_ids`。校准后由确定性程序按交付模式从仍有效的候选中选出0—2条必进判断；证据缺口模式允许0条。

六个领域优先覆盖 `feature`、`behavior`、`formation`、`challenge`、`current_change`、`response`，家庭和身体情绪还要覆盖各自专属项目。每个实际覆盖项至少绑定一个真实判断；缺少项目时写入 `evidence_gaps` 并降级章节，不得制造备用判断。

内部 `mechanism_chain`、`evidence_registry`、`domain_mechanisms` 和技术审计允许并应保留必要命理术语；禁止术语只适用于最终用户可见正文。不得为了通过正文术语检查而清洗或改写内部Core。

### 15. 输出完整语义，不直接画图

为每年输出主题、激活机制、变化强度、结果方向、领域影响和连续性语义。不要直接生成 K 线 OHLC、事业台阶高度、财富元宝数量或桃花朵数；这些数值和视觉映射由下游统一算法完成。

### 16. 生成人物画像，不制造人物

完整分析外在呈现、内在动力、认知决策、情绪安全感、行动执行、价值边界、压力恢复、环境适配和发展线。每项保留结构证据、现实候选、相反表现条件、置信度和验证问题。证据不足时写入不可推断清单，不用模糊形容词填空。

### 17. 区分关系中的自己、喜欢的人与适合的人

单人命盘分别分析命主的关系需求、容易被吸引的特质、适合长期相处的特质、强吸引但高摩擦的特质和命主一侧的互动模式。不得凭单人命盘描述具体对象或断定两个人是否适合；具体互动必须取得对方命盘与现实资料。

### 18. 强制执行画像均衡审计

自身、家庭、资源、人际、亲密关系、对象画像、互动关系、事业、财富、迁移、身心和连续性必须都有实质分析或明确的证据不足说明。不得把事业分析换词复制进其他领域。

六个报告领域必须先独立分析、再与人生主线联动。证据充足时每个领域优先形成4—6条领域专属候选和2个领域自身机制；证据不足时按实际内容降级。共享人生主线判断不得超过30%，同一判断最多进入两个领域。去掉共享主线后仍须形成独立人物侧面或明确证据缺口。家庭重点分析父母亲友、借力与受限、独立与回馈；身体与情绪重点分析基础信号、压力反应顺序和恢复方式。不得把事业中的协调与收尾直接移植到家庭章节。

## 完整输出契约

输出一个结构化 `analysis_bundle`。每个重要结论使用统一推理单元，并保留详细文字，不做卡片式压缩。

### 统一推理单元

```yaml
finding: 白话结论
mechanism_chain:
  - 从结构事实到现实表现的逐步因果链
evidence:
  natal: []
  luck_cycle: []
  annual: []
  user_facts: []
  social_priors: []
linked_domains: []
time_scope: 原局长期、某步大运、某年或某月
confidence: 高 | 中 | 待验证
alternatives: []
birth_time_dependency: 不依赖 | 部分依赖 | 高度依赖
validation: []
```

### `analysis_bundle` 顶层结构

按以下顺序完整输出：

1. `analysis_meta`
   - 分析版本、基准日期、目标时间范围、输入完整度、采用口径；
2. `chart_facts`
   - 四柱、十神、地支主中余气、大运、流年等确定事实；
3. `chart_audit`
   - 时区、节气、日界、时辰、起运和真太阳时等边界审计；
4. `social_context_model`
   - 用户事实、社会阶段、现实约束和先验候选；
5. `five_elements`
   - 季节、寒暖燥湿、分布、流通与阻塞；无固定算法时不输出伪百分比；
6. `day_master`
   - 得令、得地、得助、受制、受泄、受耗和成立条件；
7. `stems_branches_roots`
   - 逐柱透干、藏干、全部十神、根气、可见度和激活键；
8. `interaction_network`
   - 生克、制化、刑冲合害破、合化条件和全局作用；
9. `independent_method_analyses`
   - 九个方法家族各自独立生成的技术结论、现实候选、成立条件、反证和边界；
10. `method_execution_audit`
    - 每个方法的完成、失败、重试和降级结果，以及完整、降级或仅初步分析的交付决定；
11. `method_synthesis`
   - 现实候选的同向、互补、条件、阶段、上下位与冲突综合，以及结构置信度和报告角色；
12. `cross_method_analysis`
   - 方法综合的文字摘要，不得替代独立方法结构；
13. `root_seed_flower_fruit_map`
    - 时间顺序与同时共存的多维现实映射；
14. `natal_portrait`
    - 原局人物主轴的简要总结；
15. `complete_self_portrait`
    - 外在呈现、内在动力、认知决策、情绪安全感、行动执行、价值边界、压力恢复、内部矛盾、环境适配和发展线；
16. `family_system`
    - 早年资源、期待与代价、家庭角色、独立边界、伴侣与家庭接口、模式重复与修正；
17. `resource_relationship`
    - 六类资源的获得、保存、交换、放大与损耗；
18. `social_relationship_style`
    - 一般人际中的接近、信任、群体位置、利益交换、竞争合作和边界；
19. `relationship_system`
    - 亲密关系中的自己：需要、表达、冲突、修复、承诺和现实条件；
20. `partner_profiles`
    - 容易被吸引、适合长期、强吸引高摩擦三类对象特质候选及证据限制；
21. `interaction_dynamics`
    - 相识、建立信任、升温、冲突、修复、承诺和跨领域影响；
22. `environment_and_mobility`
    - 城市、平台、规则密度、迁移和生活节奏的适配条件；
23. `reality_domains`
    - 事业、财富、学习、关系、家庭、迁移、健康与成长的完整分析；
24. `domain_connections`
    - 各领域之间的因果和时间传导；
25. `luck_cycle_themes`
    - 每步大运主题、机会、成本、激活键、前后承接；
26. `annual_theme_activation`
    - 每年执行机制、变化强度、方向、领域影响、承接和伏笔；
27. `monthly_theme_activation`
    - 仅在有可靠月度数据时输出，否则为 `null`；
28. `life_stages`
    - 主要人生阶段的主线与社会现实背景；
29. `turning_points`
    - 准备、发生、落地、消化四类转折点；
30. `report_claim_ledger`
    - 可进入报告的判断台账；每条包含现实结论、来源、支持方法、置信度、可用例子、反证和禁止外推；
31. `formation_chains`
    - 3—6条从家庭、教育或早期条件到习惯、能力、限制与成年表现的人物形成链；
32. `domain_linkage_chains`
    - 3—6条事业、财富、关系、家庭、迁移与身心之间的传导链；
33. `report_source_bundle`
    - 完整人生主线和六个现实领域的报告级素材，只提供事实与候选，不直接写最终文章；
34. `reality_candidate_pool`
    - 10—24条可验证现实候选；从工作方式、组织属性、行业、职能岗位、财富机制、家庭生态、伴侣特征等开放维度生成。每条包含所属维度、现实标签、属性、固定 `domain`、`candidate_kind`、`time_scope`、`calibration_targets`、2—3个可观察例子、替代解释、反证和禁止外推；候选尽量覆盖六个报告领域；
35. `candidate_relation_map`
    - 校准候选之间的共存、互补、条件、阶段、上下位与互斥关系；
36. `calibration_state`
    - 历史反馈、被支持和被否定的候选及更新结果；
37. `calibration_delta`
    - 校准只改变候选与报告判断的状态，并记录用户事实证据；不得改写独立方法推演与综合结构；
38. `not_inferable_register`
    - 本次证据不足、禁止下结论的项目及需要补充的资料；
39. `portrait_balance_audit`
    - 画像覆盖、薄弱领域、被删除的无证据判断和跨领域路径审计；
40. `uncertainty_register`
    - 边界、流派差异、时柱依赖与替代解释；
41. `safety_boundaries`
    - 健康、财富、关系及高风险事项的表达边界。

不要省略没有明显结论的栏目。使用空数组、`null` 或“证据不足”保留结构，不得补造内容。

完整输出契约见 [analysis-output.schema.json](schemas/analysis-output.schema.json)。当前 `core_version` 使用 `0.15.0`。正式方法包仍符合 [method-packet.schema.json](schemas/method-packet.schema.json)，但九方法AI不再直接填写这份生产结构。AI只生成 [method-semantic-patch.schema.json](schemas/method-semantic-patch.schema.json) 约束的语义答卷，再由程序编译为正式方法包。

先生成一份完整主题隔离输入和九份按方法需要裁剪的短提示包。完整输入只作为统一哈希源；AI实际只读取各自提示包中的 `method-input-view.json`：

```bash
python scripts/run_in_env.py scripts/prepare_method_input.py analysis-input.json \
  --output method-input.json
python scripts/run_in_env.py scripts/build_method_prompt_packs.py method-input.json \
  --output-dir method-prompt-packs
```

九个方法彼此独立，提示清单提供三个可并行批次；宿主支持并发时同批3个任务同时运行，不能并发时才依次运行。每个方法只读取自己的 `.prompt.md`，输出 `method-semantic-patches/<method_id>.json`，并立即校验语义答卷：

```bash
python scripts/run_in_env.py internal/rensheng-youji-mingli-core/scripts/validate_method_semantic_patch.py \
  method-semantic-patches/<method_id>.json --expected-method <method_id>
```

九份语义答卷完成或被合法归类后，由程序批量补齐方法身份、哈希、稳定编号、证据登记和六领域映射，并生成METHOD GATE：

```bash
python scripts/run_in_env.py scripts/compile_method_packets.py \
  --method-input method-input.json \
  --semantic-dir method-semantic-patches \
  --output-dir method-packets \
  --gate-output method-gate.json
```

九个方法完成或被合法归类后，按生产桥生成受约束综合输入。AI只读取六领域判断矩阵、精简技术索引、精简证据索引与方法限制；完整方法包只留给确定性编译器和审计。AI只生成规定的语义综合区块，随后由程序组装完整Core并自动生成报告来源：

```bash
python scripts/run_in_env.py scripts/prepare_core_synthesis.py analysis-input.json \
  --method-packet-dir method-packets \
  --method-gate method-gate.json \
  --output core-synthesis-input.json
python scripts/run_in_env.py scripts/validate_core_synthesis.py \
  core-synthesis-input.json core-semantic-analysis.json
python scripts/run_in_env.py scripts/finalize_core_analysis.py \
  core-synthesis-input.json core-semantic-analysis.json \
  --output analysis-output-initial.json
python scripts/run_in_env.py internal/rensheng-youji-mingli-core/scripts/validate_analysis_output.py analysis-output-initial.json
python scripts/run_in_env.py scripts/audit_claim_diversity.py analysis-output-initial.json \
  --output core-quality-audit.json
```

只有输出校验和质量审计都通过后，才冻结Core并把 `analysis_bundle` 交给下游卡片、报告或网页流程。

## 输出语言

- 内部结构字段保持稳定，详细分析使用普通本科读者能理解的中文。
- 可保留必要命理术语，但紧接现实解释，不堆砌术语。
- 避免“换轨、能量场、人生副本、显化”等 AI 黑话。
- 使用概率与条件语言，不写绝对吉凶和事件保证。
- 分析变化程度与结果方向，不把变化大等同于坏，也不把稳定等同于好。
- 明确区分用户事实、社会先验、命理推测和待验证候选。

## 完成前检查

逐项执行 [analysis-workflow.md](references/analysis-workflow.md) 的最终质检。只有在四柱藏干齐全、大运与流年链条完整、年度连续、领域联动、现实来源标注和安全边界全部通过后，才返回 `analysis_bundle`。
