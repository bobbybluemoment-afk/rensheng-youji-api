---
name: rensheng-youji-free-card
description: 在用户本地，根据姓名（可选）、出生年月日时、性别和出生地点，确定性排出四柱、大运与流年，再调用仓库内置的人生有迹命理Core、免费卡片提取层和绘图层，生成含命局分析、人生主线、20年人生K线、事业步步高升、财运元宝堆、重点桃花年份和具体当前课题的3:4免费PNG卡片。用于用户要求生成“人生有迹”免费卡片、分析人生主线或查看阶段趋势时；不需要验证码、MCP或人生有迹云端接口。
---

# 人生有迹免费卡片

## 原则

- 按“确定性排盘 → Core完整分析 → 免费卡片提取 → 新版绘图”顺序执行，禁止跳过 Core 使用旧版固定文案。
- 四柱、大运和流年必须由本仓库程序计算；语言模型不得口算或改写排盘事实。
- Core 负责完整分析；免费卡片提取层决定展示内容；绘图层不得重新分析或修改趋势数值。
- 全部流程在用户当前运行环境完成，不调用人生有迹服务器，不索要验证码，不配置MCP。
- 结果用于传统文化体验与自我观察，不承诺现实事件发生。

## 收集输入

一次询问：

- 姓名，可留空；
- 出生年月日和准确时间，24小时制；
- 出生城市、国家或地区；
- 性别，仅用于传统排运顺逆；
- 时间是普通钟表时间，还是已经校正过的真太阳时。

中国出生地优先使用内置省、市、县区地点库，不让用户填写经纬度或时区。遇到重名地点时，只询问所属省或地级市。只有海外地点未收录时，才补充经度和IANA时区。

普通钟表时间传 `local_civil`；用户明确说明已经校正为真太阳时才传 `true_solar_adjusted`。`analysis-as-of` 必须使用实际运行当天的日期，下面日期仅为命令格式示例。

## 本地工作流

1. 定位本 Skill 根目录，运行 `scripts/check_env.py`。缺少依赖时由当前AI运行 `scripts/setup_env.py`，不要把安装命令交给普通用户。
2. 创建本次临时工作目录，不覆盖仓库文件。
3. 运行确定性排盘并生成 Core 输入：

```bash
python scripts/prepare_core_input.py \
  --birth "1990-05-04 13:49" \
  --gender male \
  --city "北京" \
  --country "中国" \
  --time-basis local_civil \
  --analysis-as-of "2026-08-20" \
  --output work/core-input.json \
  --profile-output work/profile.json
```

4. 完整读取 `internal/rensheng-youji-mingli-core/SKILL.md` 及其要求的参考文件，根据 `core-input.json` 生成 `analysis-output.json`。分析必须覆盖原局、主中余气与十神、根苗花果、家庭与资源、完整自身画像、人际与亲密关系、大运主题、流年执行、连续伏笔和领域传导；命理证据弱的方向明确标为弱，不得捏造。
5. 运行 Core 输出校验：

```bash
python internal/rensheng-youji-mingli-core/scripts/validate_analysis_output.py work/analysis-output.json
```

6. 完整读取 `internal/rensheng-youji-free-card-output/SKILL.md`、`references/content-selection.md` 和 `references/visual-algorithm.md`。根据 Core 母稿生成：
   - `work/card-content.json`：只含 `identity`、`mingju_analysis`、`current_issue`、`full_report_hint`、`disclaimers`；
   - `work/visual-signals.json`：含窗口起点与连续20年视觉信号，每项保留内部依据。
7. 运行确定性趋势计算：

```bash
python internal/rensheng-youji-free-card-output/scripts/validate_visual_signals.py work/visual-signals.json
python internal/rensheng-youji-free-card-output/scripts/build_visual_series.py \
  work/visual-signals.json --output work/visual-series.json
```

8. 组合并校验标准卡片数据：

```bash
python scripts/assemble_free_card.py \
  --analysis work/analysis-output.json \
  --content work/card-content.json \
  --series work/visual-series.json \
  --output work/free-card-output.json
```

9. 生成PNG：

```bash
python scripts/generate_card.py \
  --input work/free-card-output.json \
  --output work/rensheng-youji-card.png
```

## 卡片内容与检查

- PNG尺寸必须为1242×1660。
- 卡面依次为：命局分析 → 20年人生行情盘 → 当前课题。
- 命局分析列出四柱，保留必要命理机制并紧接白话解释；人生主线写在同一区域。
- 四项趋势均为20年：当前年前5年、当前年、未来14年。
- K线逐年连续、实体等宽、纵轴按数据缩放；不画五年背景色块。
- 事业使用逐年断开的空心台阶，名称为“步步高升”；当前年放简笔小人。
- 财运使用连续的小金元宝堆积，不画顶部线；元宝代表相对资源积累，不代表金额。
- 桃花只在明显关系机会年份画粉色桃花枝，无明显机会年份留白。
- 当前年只在年份和K线主体使用金色，桃花仍为粉色。
- 当前课题只能有一个具体领域，必须结合原局、大运、当前年及前后连续过程；年龄只能缩小场景，不能直接决定答案。
- 避免“换轨、抓手、赋能、内耗、能量场”等AI黑话。
- 页脚保留“人生有迹 by 景行”。

生成后只需告诉用户卡片已完成，并附带时间口径与出生地中心经度近似提醒；不要在聊天中展开20年逐年长文。

## 运行能力不足时

若当前AI不能安装自定义Skill、读取文件或运行Python，不要伪造卡片。请用户改用[人生有迹免费网页版](https://rensheng-youji-web.bobbybluemoment.workers.dev)。网页版不需要验证码。
