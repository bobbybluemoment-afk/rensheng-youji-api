# 人生有迹 API / MCP

> 把一句出生信息，变成一张有迹可循的人生主线卡。

[![MCP](https://img.shields.io/badge/MCP-Streamable_HTTP-627B6B)](https://modelcontextprotocol.io/)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1-C96855)](openapi.yaml)
[![Server](https://img.shields.io/badge/Server-v0.6.0-26312D)](https://rensheng-youji-ap-454189475786.asia-east1.run.app/docs)

“人生有迹”根据姓名（可留空）、出生年月日时、出生城市和性别，校正时间、排出四柱，匹配日柱对应的选手类型与固定插图，再由私有服务生成核心配置、人生主线与3:4 PNG卡片。

调用方AI只负责收集信息、调用工具和展示结果，不推测或改写命盘文案。分析规则、60张固定插图、字体和模板均保留在私有云端。

## 一句话体验

把下面一句话发给支持读取网页和远程MCP的AI，并将最后的占位内容换成你收到的个人体验码：

```text
请读取并严格执行这份“人生有迹”接入说明，为我生成出生主线卡：https://raw.githubusercontent.com/bobbybluemoment-afk/rensheng-youji-api/main/AI-START.md；我的个人体验码是：这里填写体验码。
```

体验码一人一码，不要公开发布。AI第一次连接外部工具时，客户端可能要求用户确认授权；这是客户端的安全机制。

## 远程MCP

```text
https://rensheng-youji-ap-454189475786.asia-east1.run.app/mcp/
```

传输方式：`Streamable HTTP`

鉴权方式：

```text
Authorization: Bearer <个人体验码>
```

工具：

| 工具 | 用途 |
|---|---|
| `prepare_birth_card` | 校正时间、排出四柱并返回固定角色和服务器文案 |
| `render_birth_card` | 使用同一份出生信息直接返回1242×1660 PNG卡片 |

完整AI操作规则见 [`AI-START.md`](AI-START.md)，机器可读元数据见 [`server.json`](server.json)，通用Skill指令见 [`SKILL.md`](SKILL.md)。

## 调用流程

```mermaid
flowchart LR
    A[出生信息] --> B[prepare_birth_card]
    B --> C[四柱、固定角色与私有文案]
    C --> D[render_birth_card]
    D --> E[1242×1660 PNG]
```

## 时间口径

- 普通钟表时间：`time_basis=local_civil`，服务按出生城市进行真太阳时近似校正。
- 已经校正的真太阳时：`time_basis=true_solar_adjusted`，服务不重复校正。
- 接近时辰边界时，建议用更具体的出生地点复核经度。

## 如果AI不能直接连接

GitHub说明不能绕过客户端自身的权限限制。如果AI不能读取外部链接或不支持远程MCP，应明确告知用户，并只指导一次必要的连接器设置；不要要求普通体验者安装Python或打开命令行。

不支持MCP但支持OpenAPI的客户端，可读取 [`openapi.yaml`](openapi.yaml)。

## 开发者：本地适配器

普通体验者不需要执行本节。仅在客户端只能运行本地stdio MCP时使用：

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

运行：

```bash
rensheng-youji-mcp
```

示例：

- [`examples/python_client.py`](examples/python_client.py)
- [`examples/typescript_client.ts`](examples/typescript_client.ts)

## 隐私与边界

- 不要把个人体验码、所有者密钥或真实出生信息提交到公开仓库。
- 当前接口仅处理本次请求，不建立用户档案。
- 服务不会向调用方返回固定插图全集、字体、模板、私有规则或服务端代码。
- 免费卡片呈现原局的一条主要读法，不宣称唯一答案。
- 输出用于文化体验与自我观察，不构成医疗、法律或金融建议。
- MIT License仅覆盖本仓库的接口代码与示例，不授权复制“人生有迹”品牌、固定内容、插图、字体、分析方法或卡片模板。

