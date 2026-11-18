# 工具图片 Mock 插件

给 FastGPT PR #7923 的插件路径造数：一个系统工具插件，按 `x-fastgpt-output-kind: model-content` 契约返回 `{ value, images }`。

## 产物

- `tool-image-mock.pkg`：可直接在 FastGPT 管理员页安装的插件包（用 fastgpt-plugin#563 分支的 SDK 构建）。
- `tool-image-mock/`：插件源码（`index.ts` 里是契约实现）。

## 安装前提

被测环境的 fastgpt-plugin 服务必须包含 [labring/fastgpt-plugin#563](https://github.com/labring/fastgpt-plugin/pull/563)。旧版插件服务不认识 `x-fastgpt-output-kind`，装上也只会按普通对象返回，图片不会进模型。

## 安装与配置

1. 管理员 → 系统工具 → 上传插件，选择 `tool-image-mock.pkg`。
2. 团队/系统里启用该插件；插件有一个密钥项「Mock 图片服务地址」，填 fastgpt-tool-image-mock 的公网地址（例如 `https://mock.example.com`），不要带结尾斜杠。
3. 在工作流工具节点或对话 Agent 里挂载该工具；调用时 `code` 可留空（默认 `PLG7`）。

## 期望返回

```json
{
  "marker": {
    "value": "PLUGIN-PLG7",
    "images": [
      { "type": "image_url", "image_url": { "url": "https://mock.example.com/img/marker.png?code=PLG7" } }
    ]
  },
  "note": "图片标记只存在于图片里，文本核对串 TEXT-PLG7-ONLY"
}
```

FastGPT 侧应把它投影成：工作流引用 `marker` 得到 `PLUGIN-PLG7`；模型本轮拿到该文本与图片；下一轮模型能读出图片里的 `PLG7`。

## 本地重建

仓库里只放构建产物。需要改源码时，在 [fastgpt-plugin](https://github.com/labring/fastgpt-plugin) 的 `fix/plugin-tool-content-parts` 分支里：

```bash
pnpm install
pnpm build:sdk-factory && pnpm build:cli
node apps/cli/dist/index.js build --entry <plugin-dir> --output <plugin-dir>/dist
node apps/cli/dist/index.js pack --entry <plugin-dir> --dist <plugin-dir>/dist --output <out> --name tool-image-mock
```
