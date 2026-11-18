# FastGPT 工具图片 Mock 服务

给 FastGPT PR #7923「工具响应支持图片进入下一轮视觉输入」用的造数服务。一个容器同时提供：

- HTTP 接口，按 PR 约定的 `{"content": [{text}, {image_url}, ...]}` 返回工具结果；
- 即时生成的标记图片（白底黑字，可直接被视觉模型读出）；
- Streamable HTTP MCP 端点，返回协议原生 `image` 块。

## 部署

```bash
docker compose up -d --build
# 或
docker build -t fastgpt-tool-image-mock . && docker run -p 8000:8000 -e PUBLIC_BASE_URL=https://your-host fastgpt-tool-image-mock
```

**必须设置 `PUBLIC_BASE_URL`** 为部署后的公网地址（不带结尾斜杠）。FastGPT 服务端要按这个地址回下载图片；留空时会退回请求头里的 Host，反向代理后容易生成内网地址。

自检：

```bash
curl https://your-host/healthz
curl "https://your-host/tool/image?code=7K3Q"
curl -o /tmp/marker.png "https://your-host/img/marker.png?code=7K3Q"
python tests/smoke_test.py --base-url https://your-host
```

## HTTP 接口

| 路径 | 返回 | 证明什么 |
|---|---|---|
| `/tool/image` | 文本 + 1 张图 | 正例：图片进入下一轮视觉输入 |
| `/tool/image-a`、`/tool/image-b` | 各 1 张不同标记的图 | 同一轮多个工具调用的图片顺序 |
| `/tool/multi-text` | 3 段文本 + 1 张图 | 多段文本与图片的顺序保持 |
| `/tool/text-only` | `{"result": "..."}`，没有 content | 旧字符串响应行为不变 |
| `/tool/bad-empty-url` | content 里图片 URL 为空 | 非法 part 整体回退文本 |
| `/tool/bad-bad-detail` | `detail: "ultra"` | detail 非法时整体回退 |
| `/tool/bad-empty-text` | 文本 part 为空 | 空文本视为非法 |
| `/tool/bad-empty-array` | `content: []` | 空数组视为非法 |
| `/tool/huge` | 约 12000 字文本 + 1 张图 | 工具响应被压缩时丢图片 |
| `/tool/many-images?n=6` | 6 张图 + 全部地址 | 单次最多 4 张图的上限 |
| `/tool/broken-image` | 图片地址 404 + 文本 | 取图失败只丢图 |
| `/tool/data-uri` | base64 data URI 图片 | 不依赖外部下载的图片通道 |
| `/img/marker.png?code=7K3Q` | 白底黑字 PNG | 标记图，可直接肉眼核对 |
| `/img/marker.svg?code=7K3Q` | SVG | 非视觉白名单格式 |

所有工具接口都支持 `code` 查询参数（缺省值固定，便于比对）：响应文本里带 `TEXT-<code>-ONLY`，图片里就是同一个 `<code>`。断言时从响应文本取 code，再要求模型答出图片里的 code。

## MCP 端点

- URL：`https://your-host/mcp`（Streamable HTTP，不需要鉴权，没有 307 跳转）
- 工具：`image_block`（PNG 图片块）、`svg_image_block`（不可转换的 SVG 块）、`empty_image_block`（空数据块）、`text_only`（纯文本）、`base64_text`（文本里带 base64）

## FastGPT 侧配置

1. **HTTP 工具集**：工作台 → 工具 → 新建 → HTTP 工具集，Base URL 填 `https://your-host`，按 `fixtures/http-toolset-tools.json` 逐个添加工具（全部 `GET`，不需要入参）。
2. **MCP 工具集**：新建 → MCP 工具集，URL 填 `https://your-host/mcp`，协议 Streamable HTTP。
3. **对话应用**：新建简单 Agent，模型选视觉模型（QA 用 `qwen3.8-omni-flash`），挂上对应工具，提示词要求“必须先调用 XX 工具，再只用图片里的标记回答”。
4. **对照组**：同一工具再建一个模型换成不支持视觉的应用，验证图片被过滤成文本占位。

## 压缩场景怎么触发

工具响应压缩阈值由模型的「最大上下文」推导，源码在 `packages/service/core/ai/llm/compress`：

- 工具响应 ≤ 20% × maxContext：原样发送，图片保留；
- > 20% × maxContext：本地精简（截断 / JSON 结构摘要），这一步不调用模型，`isCompressed` 即为真，图片被丢弃；
- 精简后仍 > 50% × maxContext：再调用模型做 LLM 压缩。

阈值有 4096 token 下限。所以默认 maxContext=1,000,000 时要 20 万 token 才触发，不现实。做法是复制一个测试模型，把「最大上下文」改成 **20000**（此时 20% 被下限抬到 4096 token），再用 `/tool/huge` 返回约 12000 字文本 + 1 张图即可稳定触发，且不会产生压缩模型的调用费用。

长对话触发的「对话历史压缩」是另一条路径（80% 阈值），不是本场景。

## 已知边界

- 插件路径（输出字段 `x-fastgpt-output-kind: model-content`）由 labring/fastgpt-plugin#563 实现，本服务无法模拟，需要该插件版本部署后再验。
- 工作流工具（应用即工具）返回的是应用回答文本，不走 `content` 契约；要验证契约请用工具节点 / HTTP / MCP / 插件。
