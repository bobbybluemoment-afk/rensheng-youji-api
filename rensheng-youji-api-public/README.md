# 人生有迹 API / MCP

> 让支持 MCP 或 OpenAPI 的模型，用它自己的能力生成一张“人生有迹”选手卡。

[![MCP](https://img.shields.io/badge/MCP-compatible-627B6B)](https://modelcontextprotocol.io/)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1-C96855)](openapi.yaml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-26312D)](pyproject.toml)
[![License](https://img.shields.io/badge/interface-MIT-F4F0E6)](LICENSE)

“人生有迹”把出生信息转化为一张适合保存与分享的 3:4 人生选手卡：确定性排出四柱，匹配日柱对应的选手类型与初始天赋，再由调用方自己的模型提炼核心配置、主线任务和人物小传。

这个仓库是品牌的**开放接入层**，不是核心算法的开源仓库。它只包含模型无关的 API 规范、MCP 适配器与客户端示例；排盘实现、六十日柱固定内容、插图、字体和卡片渲染均运行在私有服务中。

## 你可以用它做什么

- 在 Claude、Cursor、Codex 等支持 MCP 的客户端中调用。
- 把 `openapi.yaml` 导入支持 function calling 的模型或自动化平台。
- 使用 Python、TypeScript 或任意 HTTP 客户端接入。
- 让使用者自己的模型完成个性化文案，不把模型 token 成本转嫁给 API 服务。

## 工作方式

调用分为两步：

```mermaid
flowchart LR
    A[出生信息] --> B[prepare_birth_card]
    B --> C[四柱与写作约束]
    C --> D[调用方自己的模型]
    D --> E[render_birth_card]
    E --> F[3:4 PNG 卡片]
```

1. `prepare_birth_card`：提交出生信息，取得确定性四柱、当前日柱对应的选手类型与初始天赋，以及一次性 `draft_token`。
2. 调用方使用自己的模型，根据返回的 `writing_brief` 生成五个文案字段，再调用 `render_birth_card` 获取最终 1242×1660 PNG 卡片。

服务端不调用生成模型，因此模型 token 费用由调用方自己的模型账户承担。API key 仅用于访问排盘、固定内容匹配与渲染服务。

## 快速开始

### 直接调用 OpenAPI

接口定义见 [`openapi.yaml`](openapi.yaml)。支持 OpenAPI/function calling 的模型或自动化平台可以直接导入该文件。

设置环境变量：

```bash
export RENSHENG_API_BASE_URL="https://你的接口域名"
export RENSHENG_API_KEY="你的-api-key"
```

然后参考：

- `examples/python_client.py`
- `examples/typescript_client.ts`

### 作为 MCP 使用

需要 Python 3.11 或更高版本。

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
rensheng-youji-mcp
```

在支持 MCP 的客户端里，把命令配置为 `rensheng-youji-mcp`，并为进程配置 `RENSHENG_API_BASE_URL`、`RENSHENG_API_KEY`。工具返回的卡片会写入 `RENSHENG_OUTPUT_DIR`；未设置时写入当前目录。

## 两个公开工具

| 工具 | 输入 | 输出 |
|---|---|---|
| `prepare_birth_card` | 姓名（可选）、出生年月日时、性别、城市、国家、时间口径 | 四柱、单个日柱配置、写作约束、短期令牌 |
| `render_birth_card` | 短期令牌与调用方模型生成的卡片文案 | 1242×1660 PNG 卡片 |

API 不返回六十日柱全集、插图地址、模板文件或服务端实现。

## 时间口径

- 已经校正为真太阳时：传入 `time_basis=true_solar_adjusted`。
- 传入当地法定时间：使用 `time_basis=local_legal_time`。建议同时提供 IANA `timezone` 和出生地经度 `longitude`；缺省时，私有服务会尝试由城市解析。

城市自动解析依赖第三方地理数据，重要场景建议显式提供时区和经度并由用户核对。夏令时按出生日期对应的 IANA 时区规则计算。

## 隐私与限制

- `draft_token` 默认 15 分钟有效，成功渲染后立即失效。
- 出生信息只在短期草稿中保留；公开仓库不收集或保存用户数据。
- 请勿把 API key 写入提示词、前端源码或公开仓库。
- 古典引文由调用方模型生成并负责核验，接口只做字段与版式校验。

## 项目边界

本仓库开放的是“如何调用”，不是“全部产品资产”。MIT License 只覆盖本仓库中的接口代码与示例，不授权复制或再分发“人生有迹”品牌、固定文案、六十甲子插图、字体、分析方法或卡片模板。

## 许可证

本仓库的接口代码使用 MIT License。详见 [`LICENSE`](LICENSE)。
