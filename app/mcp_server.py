"""Streamable-HTTP MCP server that returns protocol-native image blocks."""
from __future__ import annotations

import base64

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

from .payloads import make_code
from .png import render_marker_png


def build_mcp() -> FastMCP:
    mcp = FastMCP(
        name="fastgpt-tool-image-mock",
        instructions=(
            "Mock MCP tools for FastGPT PR #7923: return image blocks, unusable image "
            "blocks and text-only results."
        ),
        streamable_http_path="/mcp",
        stateless_http=True,
    )

    @mcp.tool(description="Return a PNG image block plus its text marker.")
    def image_block(code: str = "") -> list[TextContent | ImageContent]:
        marker = (code or make_code()).upper()
        png = render_marker_png(marker, scale=16)
        return [
            TextContent(
                type="text",
                text=f"图片标记只存在于图片中，文本核对串 TEXT-{marker}-ONLY",
            ),
            ImageContent(
                type="image",
                data=base64.b64encode(png).decode("ascii"),
                mimeType="image/png",
            ),
        ]

    @mcp.tool(description="Return an SVG image block, which providers cannot consume.")
    def svg_image_block(code: str = "") -> list[TextContent | ImageContent]:
        marker = (code or make_code()).upper()
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="120">'
            '<rect width="320" height="120" fill="#fff"/>'
            f'<text x="160" y="80" font-size="64" text-anchor="middle">{marker}</text></svg>'
        )
        return [
            TextContent(
                type="text",
                text=f"图片标记只存在于图片中，文本核对串 TEXT-{marker}-ONLY",
            ),
            ImageContent(
                type="image",
                data=base64.b64encode(svg.encode("utf-8")).decode("ascii"),
                mimeType="image/svg+xml",
            ),
        ]

    @mcp.tool(description="Return an image block with empty payload data.")
    def empty_image_block(code: str = "") -> list[TextContent | ImageContent]:
        marker = (code or make_code()).upper()
        return [
            TextContent(type="text", text=f"图片块数据为空，文本核对串 TEXT-{marker}-ONLY"),
            ImageContent(type="image", data="", mimeType="image/png"),
        ]

    @mcp.tool(description="Return text content only, for backward compatibility checks.")
    def text_only(code: str = "") -> str:
        marker = (code or make_code()).upper()
        return f"只有文本结果，核对串 TEXT-{marker}-ONLY"

    @mcp.tool(description="Return a raw base64 PNG string inside the text content.")
    def base64_text(code: str = "") -> str:
        marker = (code or make_code()).upper()
        payload = base64.b64encode(render_marker_png(marker, scale=12)).decode("ascii")
        return f"文本里带 base64 图片数据，核对串 TEXT-{marker}-ONLY data:image/png;base64,{payload[:64]}"

    return mcp
