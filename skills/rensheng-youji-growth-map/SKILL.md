---
name: rensheng-youji-deep-report
description: 根据姓名（可选）、出生年月日时、性别、出生地点、可选现实资料与当前困惑，使用人生有迹统一确定性排盘和 rensheng-youji-mingli-core 完整分析母稿，经过五条现实事实校准后，生成“人生有迹｜完整报告”Markdown或PDF。用于用户要求完整八字报告、人生主线、性格成长、恋爱伴侣、事业、财务、身体情绪、家庭成长环境、长期阶段或逐年分析时；报告 Skill 免费公开，不需要验证码或人生有迹云端接口。
---

# 人生有迹｜完整报告

## 原则

- 始终复用仓库根目录的确定性排盘与 `rensheng-youji-mingli-core`，不得维护第二套四柱、大运、流年或命理分析规则。
- Core 负责生成完整 `analysis_bundle`、开放现实候选、人物形成链和报告判断台账；本 Skill 依次完成现实校准、事实提纲、人物写作、中文编辑与渲染。
- 报告与免费卡片必须来自同一套 Core，人生主线可以扩写，不能得出相反结论。
- 用户选择的关注方向只决定第4页“当前阶段与问题回应”、对应逐年提醒与行动优先级，不得改写完整人生主线、能力资源、形成过程或六个领域的基础判断。
- Skill 免费公开运行，不索要验证码，不调用人生有迹服务器。若当前AI不能运行Skill，可提示用户联系景行获得人工代生成、校准、排版与解释服务。
- 使用普通中文、条件式表达和可验证现实场景，不承诺事件，不用恐吓引导咨询。

## 运行前预检与生产边界

在向用户收集出生资料前，先从当前目录向上定位仓库根目录。若仓库 `venv` 不存在，使用系统Python运行且只运行 `python scripts/setup_env.py`；安装完成后，当前会话所有Python命令都必须通过 `python scripts/run_in_env.py ...` 进入同一个仓库虚拟环境，不得再直接运行 `python <业务脚本>` 或 `python -m ...`。首先运行 `python scripts/run_in_env.py scripts/check_env.py`。预检必须确认排盘、正式Core、事实提纲、写作、编辑、新版重点判断渲染、稳定渲染、字体、Logo和二维码均可用；预检失败时先修复环境，不让用户先完成校准再发现无法交付。

完整读取 [production-failure-policy.md](references/production-failure-policy.md)。仓库本身必须位于当前会话持久工作区，不得克隆到 `/tmp`、`/var/tmp` 或 `/private/tmp`。探索性读文件错误不属于正式生产失败，只有该规范列出的正式阶段错误才能触发停止。

- `self_test_fixture`、`--self-test` 和 `tests/fixtures` 只允许由仓库测试命令使用，严禁作为真实用户Core、事实提纲或报告的数据来源。
- 不得现场创建 `fix_report_v*.py`、`rewrite_report*.py`、`patch_report*.py` 等临时脚本修改正式正文、来源编号或哈希；不得用全局字符串替换清除命理术语。
- Core单方法和语义综合分别遵循各自最多三轮的局部修复规则；其他正式阶段校验失败时只允许重新运行出错阶段一次。仍失败则按“交付容错”降级，不得伪造字段让校验器放行。

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
2. 确认本次会话已经通过 `python scripts/run_in_env.py scripts/check_env.py`；缺少仓库虚拟环境时，由当前AI先运行一次 `python scripts/setup_env.py`，然后通过统一入口重新预检。`setup_env.py` 输出的 `READY` 解释器与 `run_in_env.py` 必须指向同一仓库 `venv`。
3. 创建仓库内持久运行目录，不使用系统临时目录：

```bash
python scripts/run_in_env.py scripts/create_report_run.py
```

保存命令返回的绝对 `work_dir`。下文命令中的 `work/` 是该绝对目录的简写，实际执行时必须替换为返回的 `work_dir/`；不得创建仓库根目录下另一套散落文件。每次跨轮继续前运行：

```bash
python scripts/run_in_env.py scripts/report_pipeline.py status --run-dir <work_dir>
```
4. 运行根目录确定性排盘并生成 Core 输入：

```bash
python scripts/run_in_env.py scripts/prepare_core_input.py \
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
python scripts/run_in_env.py skills/rensheng-youji-growth-map/scripts/preflight_report.py \
  work/core-input.json --focus "事业发展" --output work/report-preflight.json
```

若结果为 `blocked`，先核对出生分钟和出生区县。仍无法消除可能改变月柱、日柱、时柱或起运的边界时，只能生成标题明确的“人生有迹｜初步分析”，不得继续生成正式完整PDF。

7. 运行 Core 输入校验：

```bash
python scripts/run_in_env.py internal/rensheng-youji-mingli-core/scripts/validate_analysis_input.py work/core-input.json
```

8. 生成九方法唯一允许读取的主题隔离输入：

```bash
python scripts/run_in_env.py scripts/prepare_method_input.py work/core-input.json \
  --output work/method-input.json
```

该脚本保留排盘、原局、大运和流年，清空现实资料、当前问题与校准信息。九个方法不得读取 `work/core-input.json`、`work/report-preflight.json`、用户关注方向或对话中的现实答案；每个方法包必须登记命令返回的 `method_input_sha256` 和 `input_scope=chart_only_topic_isolated`。

随后确定性生成九个方法包草稿：

```bash
python scripts/run_in_env.py scripts/initialize_method_packets.py \
  work/method-input.json --output-dir work/method-packet-drafts
```

方法包唯一正式结构入口为 `internal/rensheng-youji-mingli-core/schemas/method-packet.schema.json`。不得寻找或假设存在其他方法Schema。草稿只负责固定方法身份、独立家族、输入范围、输入哈希和八领域；AI完成独立分析后必须删除 `_draft_notice`、替换全部 `__AI_FILL__`，并另存到 `work/method-packets/<method_id>.json`。

9. 完整读取 `internal/rensheng-youji-mingli-core/SKILL.md` 及其要求的全部参考文件。只读取 `work/method-input.json`、当前方法草稿和正式 `method-packet.schema.json`，依次生成九个独立方法包，保存到 `work/method-packets/<method_id>.json`。不得读取其他方法的草稿或成品。每个完整方法必须逐项检查 `self_growth`、`love_partner`、`career`、`finance_resources`、`body_emotion`、`family_growth`、`learning`、`mobility`，分别登记 `supported`、`insufficient_evidence` 或 `not_applicable`；不能为了覆盖而硬造候选。每个方法包生成后立即运行：

```bash
python scripts/run_in_env.py internal/rensheng-youji-mingli-core/scripts/validate_method_packet.py \
  work/method-packets/<method_id>.json --expected-method <method_id>
```

单个方法失败只修复该方法，最多三轮；仍失败则清空半成品并记录失败状态。单方法通过只是暂时合格，方法集合要到步骤10汇总成功后才冻结。当前固定方法为七个主要方法与两个部分独立方法，不生成或分析神煞、纳音。

10. 九个方法包全部完成或被合法归类后，运行确定性汇总：

```bash
python scripts/run_in_env.py scripts/prepare_core_synthesis.py work/core-input.json \
  --method-packet-dir work/method-packets \
  --output work/core-synthesis-input.json
```

该脚本必须实际生成 `core-synthesis-input.json`；不得让模型手工复制方法、证据或方法执行审计。若汇总器报告非法领域、无效引用或跨方法重复编号，只返修错误点名的方法包并重新校验、汇总。若只报告 `source_coverage_audit.status=ready_with_gaps`，不得停止；没有来源的领域进入证据缺口并在报告中降级。

11. AI只读取 `work/core-synthesis-input.json`，生成 `work/core-semantic-analysis.json`。只允许生成其中 `semantic_output_contract.required_sections` 列出的语义区块；不得输出或改写排盘事实、方法包、证据、方法状态、校准状态或报告来源。

12. 运行语义综合校验：

```bash
python scripts/run_in_env.py scripts/validate_core_synthesis.py \
  work/core-synthesis-input.json work/core-semantic-analysis.json
```

失败时最多三轮局部修复：依次处理结构与引用、方法独立性与判断角色、人物覆盖与领域映射。此时方法集合已经冻结，不得重新运行方法包。第三轮仍失败才停止完整Core综合，并报告真实错误。

13. 校验通过后，由程序确定性组装完整Core并自动生成报告来源：

```bash
python scripts/run_in_env.py scripts/finalize_core_analysis.py \
  work/core-synthesis-input.json work/core-semantic-analysis.json \
  --output work/analysis-output-initial.json
```

该命令成功后再运行一次独立完整校验：

```bash
python scripts/run_in_env.py internal/rensheng-youji-mingli-core/scripts/validate_analysis_output.py \
  work/analysis-output-initial.json
```

不得要求模型自行创建 `analysis-output-before-sources.json`；不得手工拼装 `report_source_bundle`。

14. 在冻结初始Core之前运行判断多样性与报告来源审计，并生成绑定当前Core哈希的通过凭证：

```bash
python scripts/run_in_env.py scripts/audit_claim_diversity.py \
  work/analysis-output-initial.json \
  --output work/core-quality-audit.json
```

审计失败、判断家族不足或六领域语义重复时，允许只返修 `core-semantic-analysis.json` 中被点名的语义区块一次，再重新执行语义校验、完整Core组装和本审计；方法包与确定性输入仍保持冻结。第二次仍失败才停止，不得用测试样例或宽泛套话补齐数量。

审计通过后才冻结初始Core。此后不得重新生成或改写完整母稿：

```bash
python scripts/run_in_env.py scripts/core_baseline.py freeze work/analysis-output-initial.json \
  --baseline work/analysis-baseline.json \
  --lock work/analysis-baseline-lock.json \
  --quality-audit work/core-quality-audit.json
```

没有与当前 `analysis-output-initial.json` 哈希一致的 `core-quality-audit.json` 时不得冻结，也不得进入五题校准。

不得再读取本目录旧版 `core-method.md` 重新推命；该文件仅说明统一 Core 的使用边界。

## 五条现实校准

1. 完整读取 [calibration.md](references/calibration.md)。
2. 从 Core 的 `reality_candidate_pool` 选择最有信息量的现实分歧，读取固定题型库 `references/calibration-question-templates.json`，只生成内部 `work/calibration-plan.json`。不得自行撰写题干和选项。五题至少覆盖四个生活领域，同一领域最多两题，用户关注方向最多两题；至少两题核对客观状态或已经发生的事件，至少一题使用带时间窗口的已发生事件校准大运流年执行。
3. 运行构建器，把题型、Core候选关系和影响范围转换为 `schema_version=2.2.0` 的正式问题：

```bash
python scripts/run_in_env.py skills/rensheng-youji-growth-map/scripts/build_calibration_questions.py \
  --plan work/calibration-plan.json \
  --analysis work/analysis-output-initial.json \
  --output work/calibration-questions.json
```

4. 运行 `validate_calibration_questions.py`，再次回查候选是否真实存在、领域是否一致、时间题是否绑定时运候选，并且只把生成的 `work/calibration-visible.md` 发给用户：

```bash
python scripts/run_in_env.py skills/rensheng-youji-growth-map/scripts/validate_calibration_questions.py \
  work/calibration-questions.json \
  --analysis work/analysis-output-initial.json \
  --visible-out work/calibration-visible.md
```

不得自行把 `audit`、候选编号、盘面支持、置信度、替代解释或任何命理证据附在问题后面。
5. 让用户只回复题号和字母；鼓励在最关心的一至两题后补充一个具体事实或年份，但不能要求用户先懂命理。
6. 将五个选择完整写入 Core 输入的 `calibration` 和报告的 `calibration.responses`。A/B/C记录固定 `template_id`、`selected_value` 与该选项对应的 `candidate_updates`；D记录 `selected_value=uncertain` 和空更新列表。用户补充内容同时写入 `reality_context` 与 `responses.user_note`。不得为了迎合反馈修改四柱、原局结构或大运流年事实。
7. 只生成 `work/calibration-delta.json`，不得重新生成Core、`portrait_thesis`、报告判断正文、命理机制、证据登记或六领域素材。校准增量只包含候选状态、判断状态、理由、用户事实证据和五题响应，并绑定冻结Baseline的SHA-256。
8. 使用确定性程序合成校准后Core并验证冻结字段：

```bash
python scripts/run_in_env.py scripts/apply_calibration_delta.py \
  --baseline work/analysis-baseline.json \
  --lock work/analysis-baseline-lock.json \
  --delta work/calibration-delta.json \
  --output work/analysis-output-calibrated.json
python scripts/run_in_env.py scripts/core_baseline.py verify \
  --baseline work/analysis-baseline.json \
  --lock work/analysis-baseline-lock.json \
  --calibrated work/analysis-output-calibrated.json
```

每道已回答问题必须改变对应候选状态；字母答案只能调整原有候选主次，不能产生新职业、家庭、关系、身体或收入判断。未选候选继续按关系图保留；只有事实明确否定且真正互斥时才标记为 `reject`。
9. 用户跳过任何一条时，`document_mode` 必须为 `preliminary_uncalibrated`，标题必须为“人生有迹｜初步分析”，只交付初步 Markdown 和新版卡片；不得生成或称为正式完整PDF。

## 报告事实整理、写作与输出

1. 完整读取：
   - [full-report.md](references/full-report.md)：章节结构、Core字段来源和篇幅；
   - [report-schema.md](references/report-schema.md)：报告JSON契约；
   - [audience-continuity-language.md](references/audience-continuity-language.md)：白话和时间连续性；
   - [reality-anchor-language.md](references/reality-anchor-language.md)：事实型断语、现实名词精度与年度载体；
   - [chinese-editorial.md](references/chinese-editorial.md)：中文编辑、事实保留和生硬表达清理；
   - [prosperity-guide.md](references/prosperity-guide.md)：现实行动建议；
   - [brand-and-conversion.md](references/brand-and-conversion.md)：免费使用与人工服务入口；
   - [safety-language.md](references/safety-language.md)：健康、财务、关系和隐私边界。
2. 校准完成后先运行 `scripts/resolve_report_sources.py`，从冻结候选池排除 `reject`，按稳定优先级和覆盖备用映射生成 `work/resolved-report-sources.json`。不得手工编辑该文件，也不得直接沿用校准前的最终报告名单。
3. 完整读取 `internal/rensheng-youji-report-content-brief/SKILL.md`，从校准后Core、确定性选材和 `work/report-content-selection.json` 生成实体化 `work/report-content-brief.json`。事实提纲必须携带Core判断正文、机制、证据、限制、选材哈希和降级状态；不能只传判断编号。
4. 完整读取 `internal/rensheng-youji-report-writer/SKILL.md`，从实体化事实提纲生成 `work/report-draft.json`。每个内容区必须把 `mandatory_claim_ids` 对应的 `plain_claim` 原句放入正文，并登记 `claim_realization_map`；写作层只补充形成过程、条件、例子和限制，不能重新概括锁定判断。正常章节写500—700个汉字；判断不足时按确定性选材给出的 `shortened`、`minimal` 或 `evidence_gap` 缩短，不得用重复内容凑字。
5. 完整读取 `internal/rensheng-youji-chinese-editor/SKILL.md`，对初稿逐段执行第二遍中文编辑，生成 `work/editorial-review.json` 和正式 `work/report.json`。编辑记录必须保存初稿与终稿对应关系、降级状态和实际修改，不能再用几个布尔值代替编辑。
6. 正式报告使用 `schema_version=2.13.0`、`document_mode=full_calibrated`。Core使用0.14.0、事实提纲和初稿使用1.5.0、中文编辑使用2.4.0。Core先让九种方法读取主题隔离输入，独立完成技术推演、八领域检查和现实候选，再通过生产桥完成来源覆盖审计、受约束语义综合与确定性组装；单个方法最多独立重试3次，仍失败则退出综合投票。没有方法候选的领域只形成证据缺口并缩短章节，不停止其他可靠内容。只有方法覆盖度达到完整或降级交付门槛时才能冻结Baseline并继续正式报告，`preliminary_only` 必须停止正式链路。完整人生主线先根据全盘材料生成，再在第4页单独回应用户问题。六个领域先写各自的人物侧面，再用人生主线串联；用户关注方向只在当前阶段、问题回应、相关年度和行动建议中加重。
7. 时间分析继续使用“大运交代阶段主题，流年负责激活和执行”，说明上一阶段、近几年、当前年与未来两三年的连续关系，同时概括更长阶段。
8. 从同一份校准后 Core 母稿依次运行 `rensheng-youji-free-card-output` 与 `rensheng-youji-free-card-renderer` 的现有新版流程，生成 `work/free-card-output.json`。报告与卡片的分析编号、Core版本和明显关系机会年份必须一致。
9. 运行统一交付命令：

```bash
python scripts/run_in_env.py skills/rensheng-youji-growth-map/scripts/generate_full_report.py \
  --report work/report.json \
  --content-brief work/report-content-brief.json \
  --report-draft work/report-draft.json \
  --editorial-review work/editorial-review.json \
  --analysis work/analysis-output-calibrated.json \
  --analysis-baseline work/analysis-baseline.json \
  --baseline-lock work/analysis-baseline-lock.json \
  --calibration-delta work/calibration-delta.json \
  --resolved-sources work/resolved-report-sources.json \
  --free-card work/free-card-output.json \
  --calibration-questions work/calibration-questions.json \
  --out-dir work/delivery \
  --keep-pages
```

10. 正式交付固定包含新版1242×1660卡片PNG、Markdown、恰好10页的PDF和 `report-delivery-manifest.json`。PDF第2页必须嵌入刚刚生成的同一张新版卡片；不得让用户模型自行决定版式、页数、换行、颜色或二维码位置。

## 交付容错

正式交付按以下顺序处理，不把普通视觉问题升级成用户失败：

1. 先生成少量重点判断的新版PDF；完整人生主线通常2条、当前问题通常1条、每个领域最多1条，没有合适句子时允许为空。
2. 重点样式、换行或单页空间检查失败时，交付程序自动关闭重点样式，使用同一份已校验正文生成统一字号和颜色的稳定版PDF；不得重新推命或改写正文。
3. 数组、对象、残句、内部命理术语或来源错误必须在写作/编辑阶段修复后重新校验，不能由PDF渲染器猜测或替换。
4. 单个领域判断不足不再临时返工冻结Core；确定性选材根据剩余判断自动进入 `shortened`、`minimal` 或 `evidence_gap`。写作层必须缩短该领域并明确证据边界，不用人生主线或校准答案填满，也不阻塞其余可靠内容交付。
5. 只有四柱/时运计算失败、Core没有真实生成、冻结Core被校准改写、报告与卡片来源不一致、主要判断无来源，或稳定版仍发生缺字截断时，才停止错误交付。

交付清单必须记录 `render_mode=primary|stable`、`visual_fallback_used`、实际 `overflow` 和 `text_render_completed`。不得把 `overflow=false` 作为固定值写入。

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
3. 完整人生主线继续展开，不显示校准答案或内部现实线索；
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
- `analysis-baseline.json` 已在五题前冻结，校准后受保护字段哈希完全一致；
- 六个领域各至少包含三个判断家族、两个机制家族和三个现实问题轴；
- 每个内容区锁定的1—2条 `plain_claim` 均以原句进入初稿和终稿，中文编辑没有改变其落地映射；
- 第2页为同一 Core 生成的新版人生卡片，卡片尺寸为1242×1660；
- PDF恰好10页，所有正文无截断，微信二维码实际嵌入；重点判断使用独立深青色行，稳定模式允许取消重点样式；
- 用户可见校准题中没有候选编号、置信度、盘面支持或命理证据；
- 用户可见题干和A/B/C来自固定题型库，模型没有自行改写；每题只比较一个轴，三个答案对应不同的候选更新结果；
- 五题至少包含两道客观状态或事件题、一道带时间窗口的事件题，并且时间题实际绑定带大运或流年证据的 `timed_event` 候选；
- 不包含“初始角色、核心配置、主线任务、人物小传”等旧卡片字段；
- 六个领域均有实质内容或明确写证据不足，不能把事业段落换词复制到其他领域；
- 正常领域写成2—4个连贯自然段并完整覆盖行为模式、形成经历、现实条件、重复挑战、阶段变化与应对；降级领域严格按照选材状态缩短并记录缺失覆盖项；
- 正常领域和完整人生主线为500—700个汉字；`shortened` 为320—500字，`minimal` 为180—320字，`evidence_gap` 为60—180字；不得为了统一篇幅重复判断；
- 最终正文没有“现实落点、核对点、判断等级、校准后的现实线索”等内部栏目，也没有固定“好处—代价”句式；
- 已执行事实提纲、人物初稿和可追溯中文编辑，初稿与终稿真实存在，编辑没有新增判断；
- 每个自然段至少映射两个实体化Core判断，完整人生主线和六领域至少八成来源为命盘或时运基线；
- 盲派象法与技法只作交叉验证，高置信判断同时有非盲派方法支持，不向用户显示内部盲派术语；
- “经营”只在用户确有经商、创业、利润责任或业务经营语境时使用；
- 每个现实名词都进入来源审计；大型国企、互联网大厂、事业单位、具体岗位、收入形式等名词只有在用户事实或至少两个独立Core视角支持时才能出现；
- 事业、财务、关系、家庭与压力节奏均落到各自可核对的名词，不能只写“能力、资源、平台、稳定、成长”等宽泛类别；
- 完整人生主线与能力形成部分至少覆盖六个现实领域，不能围绕用户关注方向集中取材；
- 用户关注方向只在第4页、逐年回应与行动优先级中加重，不改变其他领域篇幅与基础结论；
- 用户可见正文不得出现命盘、命局、原局、四柱名称、日主、十神、天干地支、透干、身强身弱、大运流年等内部命理术语，也不得出现“组织化过劳型、先扎根后显声、表达窗口、物质与经营底色”等生造或压缩表达；发现术语必须整句退回中文编辑，不得词语级替换；
- 逐年字段 `theme`、`carry_in`、`real_world_signal`、`seed_for_next` 必须是字符串；用户可见正文不得出现Python数组、JSON对象、孤立残字或未完成连接语；
- “现在最值得做的三件事”、当前重点与未来方向不得把过去年份写成尚待执行的建议；
- 报告明显关系机会年份与卡片桃花年份完全一致；百分号等常用符号渲染后不得出现缺字方框；
- 校准答案选择了哪个现实候选，相关章节就引用哪个候选或用户补充事实，不得只提高置信度；
- 校准没有选中的候选，不得自动删除；兼容、互补、阶段性或情境性候选应作为次要侧面或条件侧面参与人物刻画，真正互斥且已被现实答案否定时才排除；
- 校准后的完整人生主线与六领域必须引用冻结Core的 `portrait_thesis` 和 `candidate_relation_map`；`calibration_delta`只决定候选主次，不得成为六领域正文的主要材料；
- 逐年观察使用项目交付、岗位调整、考试证书、合同、搬家、见父母、回款等现实载体；普通年份不强行虚构事件，重点年才增加细节；
- 已确认事实、命理推断、社会先验和待验证候选没有混写；
- 当前问题在开篇和相关章节获得直接回应；
- 报告完整回答后再出现人工服务入口，不故意保留关键结论；
- 健康不诊断、财务不保证、关系不承诺、年份不写成必然事件。

## 输出边界

未经用户授权，不上传出生资料，不把真实报告改写成宣传内容。公开案例必须去除可识别信息并标明“示例”。
