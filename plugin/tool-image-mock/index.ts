/**
 * Mock 系统工具插件：按 FastGPT PR #7923 的插件契约返回图片内容。
 *
 * outputSchema 用 `defineContentSchema()` 声明一个 model-content 字段，构建后的
 * manifest 会带上 `x-fastgpt-output-kind: model-content`；运行时返回
 * `{ value, images: [{ type: 'image_url', image_url: { url } }] }`。
 * FastGPT 会把 value 作为工具文本、images 作为下一轮视觉输入。
 *
 * 图片由 fastgpt-tool-image-mock 服务生成，需要在插件密钥里填它的公网地址。
 */
import {
  createToolHandler,
  defineContentSchema,
  defineInputSchema,
  defineOutputSchema,
  defineSecretSchema,
  defineTool
} from '@fastgpt-plugin/sdk-factory';
import z from 'zod';

const DEFAULT_BASE_URL = 'https://your-host';

const secretSchema = defineSecretSchema({
  baseUrl: {
    type: z.string(),
    title: { en: 'Mock image service base URL', 'zh-CN': 'Mock 图片服务地址' },
    description: {
      en: 'Public base URL of fastgpt-tool-image-mock, e.g. https://mock.example.com',
      'zh-CN': 'fastgpt-tool-image-mock 的公网地址，例如 https://mock.example.com'
    },
    isSecret: false
  }
});

const handler = createToolHandler({
  inputSchema: defineInputSchema({
    code: {
      type: z.string().min(2).max(8).optional(),
      title: { en: 'Marker code', 'zh-CN': '标记内容' },
      description: {
        en: 'Marker code rendered into the image, 2-8 uppercase letters or digits',
        'zh-CN': '渲染到图片里的标记，2-8 位大写字母或数字'
      },
      isToolParam: true
    }
  }),
  outputSchema: defineOutputSchema({
    marker: {
      type: defineContentSchema(z.string()),
      title: { en: 'Marker image', 'zh-CN': '标记图片' },
      description: {
        en: 'Marker text plus the generated image that carries it',
        'zh-CN': '标记文本以及承载该标记的图片'
      }
    },
    note: {
      type: z.string(),
      title: { en: 'Note', 'zh-CN': '说明' },
      description: {
        en: 'Plain text that must stay readable when images are dropped',
        'zh-CN': '纯文本说明，图片被丢弃时仍应可读'
      }
    }
  }),
  secretSchema,
  handler: async (input, ctx) => {
    const rawBaseUrl = ctx.secrets?.baseUrl || DEFAULT_BASE_URL;
    const baseUrl = rawBaseUrl.replace(/\/+$/, '');
    const code = (input.code || 'PLG7').trim().toUpperCase();

    return {
      marker: {
        value: `PLUGIN-${code}`,
        images: [
          {
            type: 'image_url' as const,
            image_url: { url: `${baseUrl}/img/marker.png?code=${code}` }
          }
        ]
      },
      note: `图片标记只存在于图片里，文本核对串 TEXT-${code}-ONLY`
    };
  }
});

export default defineTool({
  manifest: {
    pluginId: 'tool-image-mock',
    version: '1.0.0',
    name: {
      en: 'Tool Image Mock',
      'zh-CN': '工具图片 Mock'
    },
    description: {
      en: 'Returns a marker image through the tool content contract (FastGPT PR #7923)',
      'zh-CN': '通过工具内容契约返回标记图片（FastGPT PR #7923）'
    },
    versionDescription: {
      en: 'Initial version',
      'zh-CN': '初始版本'
    }
  },
  handler
});
