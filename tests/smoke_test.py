"""Smoke test for the deployed mock service.

    python tests/smoke_test.py --base-url http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.request


def get(url: str, timeout: float = 20.0) -> tuple[int, bytes, str]:
    request = urllib.request.Request(url, headers={"accept": "*/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), response.headers.get("content-type", "")
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers.get("content-type", "")


def get_json(url: str) -> dict:
    status, body, _ = get(url)
    assert status == 200, f"{url} -> {status}"
    return json.loads(body)


def assert_content_shape(payload: dict, *, expect_image: bool) -> list[dict]:
    parts = payload.get("content")
    assert isinstance(parts, list) and parts, f"missing content array: {payload}"
    images = [part for part in parts if part.get("type") == "image_url"]
    texts = [part for part in parts if part.get("type") == "text"]
    if expect_image:
        assert images, f"expected image part: {payload}"
        assert images[0]["image_url"]["url"], "image url must not be empty"
    return texts + images


def run(base_url: str) -> None:
    base = base_url.rstrip("/")

    status, body, _ = get(f"{base}/healthz")
    assert status == 200 and json.loads(body)["status"] == "ok", "healthz failed"

    status, body, content_type = get(f"{base}/img/marker.png?code=7K3Q")
    assert status == 200 and content_type.startswith("image/png"), "marker png failed"
    assert body.startswith(b"\x89PNG\r\n\x1a\n"), "marker png is not a PNG"

    status, _, _ = get(f"{base}/img/missing.png")
    assert status == 404, "missing image must return 404"

    image_payload = get_json(f"{base}/tool/image?code=7K3Q")
    parts = assert_content_shape(image_payload, expect_image=True)
    image_url = [p for p in parts if p["type"] == "image_url"][0]["image_url"]["url"]
    status, body, content_type = get(image_url)
    assert status == 200 and content_type.startswith("image/png"), f"tool image unreachable: {image_url}"

    for path in ("/tool/image-a", "/tool/image-b", "/tool/multi-text", "/tool/data-uri"):
        assert_content_shape(get_json(f"{base}{path}"), expect_image=True)

    text_payload = get_json(f"{base}/tool/text-only")
    assert "content" not in text_payload and "result" in text_payload, "text-only shape changed"

    for path in (
        "/tool/bad-empty-url",
        "/tool/bad-bad-detail",
        "/tool/bad-empty-text",
        "/tool/bad-empty-array",
    ):
        payload = get_json(f"{base}{path}")
        assert "content" in payload, f"{path} should still return a content field"

    assert get_json(f"{base}/tool/bad-empty-array")["content"] == []

    huge = get_json(f"{base}/tool/huge?chars=12000")
    text = [p for p in huge["content"] if p["type"] == "text"][0]["text"]
    assert len(text) > 11000, "huge payload is too small to trigger compression"
    assert "HEAD-HUG4" in text and "TAIL-HUG4" in text

    many = get_json(f"{base}/tool/many-images?n=6")
    images = [p for p in many["content"] if p["type"] == "image_url"]
    assert len(images) == 6, "many-images should return 6 images"

    broken = get_json(f"{base}/tool/broken-image")
    broken_url = [p for p in broken["content"] if p["type"] == "image_url"][0]["image_url"]["url"]
    status, _, _ = get(broken_url)
    assert status == 404, "broken image endpoint must 404"

    data_uri = get_json(f"{base}/tool/data-uri")
    uri = [p for p in data_uri["content"] if p["type"] == "image_url"][0]["image_url"]["url"]
    assert uri.startswith("data:image/png;base64,"), "data uri malformed"
    assert base64.b64decode(uri.split(",", 1)[1]).startswith(b"\x89PNG"), "data uri is not a PNG"

    print("REST smoke ok")


async def run_mcp(base_url: str) -> None:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    url = f"{base_url.rstrip('/')}/mcp"
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {tool.name for tool in (await session.list_tools()).tools}
            assert {"image_block", "svg_image_block", "empty_image_block", "text_only"} <= tools

            result = await session.call_tool("image_block", {"code": "M4PT"})
            kinds = [item.type for item in result.content]
            assert "image" in kinds, f"no image block: {kinds}"
            image = [item for item in result.content if item.type == "image"][0]
            assert image.mimeType == "image/png"
            assert base64.b64decode(image.data).startswith(b"\x89PNG")

            svg = await session.call_tool("svg_image_block", {"code": "M4PT"})
            svg_image = [item for item in svg.content if item.type == "image"][0]
            assert svg_image.mimeType == "image/svg+xml"

    print("MCP smoke ok")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--skip-mcp", action="store_true")
    args = parser.parse_args()

    run(args.base_url)
    if not args.skip_mcp:
        import anyio

        anyio.run(run_mcp, args.base_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
