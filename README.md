# 人生有迹 API / MCP

> 让 ChatGPT、Claude、Gemini 或其他支持 MCP / OpenAPI 的模型，使用它自己的模型能力生成“人生有迹”选手卡。

[![MCP](https://img.shields.io/badge/MCP-compatible-627B6B)](https://modelcontextprotocol.io/)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1-C96855)](openapi.yaml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-26312D)](pyproject.toml)
[![API](https://img.shields.io/badge/API-v0.3.0-627B6B)](https://rensheng-youji-ap-454189475786.asia-east1.run.app/docs)

“人生有迹”把出生信息转化为一张适合保存与分享的3:4人生选手卡：私有服务确定性排出四柱，匹配日柱对应的选手类型与初始天赋；调用方自己的模型根据事实层生成核心配置、主线任务和人物小传；私有服务再用固定Logo、字体与插图生成PNG。

本仓库是品牌的**开放接入层**，不是核心资产仓库。它只包含API规范、MCP适配器和客户端示例；排盘实现、60张固定插图、字体与卡片模板均保留在私有服务中。

## 调用流程

```mermaid
flowchart LR
    A[姓名与出生信息] --> B[prepare_birth_card]
    B --> C[四柱、固定角色与事实层]
    C --> D[调用方自己的模型生成文案]
    D --> E[render_birth_card]
    E --> F[1242×1660 PNG]
```

1. `prepare_birth_card` 调用私有服务的 `/generate`，返回四柱、日柱固定角色、初始天赋、十神、藏干、地势和地支关系。
2. 调用方自己的模型按 `writing_brief` 生成核心配置、主线任务和已核对出处的人物小传。
3. `render_birth_card` 调用 `/render-card`，返回并保存最终PNG。

服务端不调用生成模型，因此模型费用由调用方自己的模型账户承担。

## 快速开始

需要Python 3.11或更高版本。

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

Windows激活命令：

```powershell
.venv\Scripts\activate
```

设置环境变量：

```bash
export RENSHENG_API_KEY="由人生有迹提供的API Key"
export RENSHENG_API_BASE_URL="https://rensheng-youji-ap-454189475786.asia-east1.run.app"
```

`RENSHENG_API_BASE_URL` 已有默认值，可以不设置；API Key必须通过环境变量提供，不得写进公开仓库或提示词。

运行MCP：

```bash
rensheng-youji-mcp
```

## 两个MCP工具

| 工具 | 用途 |
|---|---|
| `prepare_birth_card` | 校正时间、排出四柱并返回固定角色与写作事实层 |
| `render_birth_card` | 校验调用方模型生成的文案并保存3:4 PNG |

## 时间口径

- 输入出生地当时的当地法定时间：`time_basis=local_civil`。已收录城市可自动使用城市中心经度；未收录城市还需提供 `longitude` 和IANA `timezone`。
- 输入已经校正的真太阳时：`time_basis=true_solar_adjusted`，服务不会重复校正。
- 真太阳时为城市中心近似值；接近时辰边界时，建议用具体出生地址复核。

## 直接调用OpenAPI

接口定义见 [`openapi.yaml`](openapi.yaml)，服务文档见 [Cloud Run `/docs`](https://rensheng-youji-ap-454189475786.asia-east1.run.app/docs)。示例：

- [`examples/python_client.py`](examples/python_client.py)
- [`examples/typescript_client.ts`](examples/typescript_client.ts)

## 隐私与边界

- API不返回60张插图全集、字体、模板或服务端代码。
- 出生信息只用于本次请求和卡片生成，当前接口不建立用户档案。
- 古典引文由调用方模型负责联网核对，服务只做字段和版式校验。
- 输出用于文化体验与自我观察，不构成医疗、法律或金融建议。
- MIT License只覆盖本仓库的接口代码与示例，不授权复制“人生有迹”品牌、固定内容、插图、字体、分析方法或卡片模板。

