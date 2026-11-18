"""HTTP mock used by the FastGPT tool-image regression (PR #7923).

Every endpoint returns JSON in the shape a FastGPT tool must produce for images to
reach the next model turn:

    {"content": [{"type": "text", ...}, {"type": "image_url", "image_url": {"url": ...}}]}

The marker image is rendered on demand, so one deployment can serve unique,
readable codes for parallel test runs.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response

from . import payloads
from .mcp_server import build_mcp
from .png import render_marker_png, render_marker_svg

PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").strip()

mcp = build_mcp()
mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="FastGPT tool image mock", lifespan=lifespan)


def base_url(request: Request) -> str:
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL.rstrip("/")
    return str(request.base_url).rstrip("/")


def normalize_code(code: str | None, fallback: str = "") -> str:
    if code:
        return code.strip().upper()
    return fallback or payloads.make_code()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/img/marker.png")
def marker_png(
    code: str = Query(default=""),
    scale: int = Query(default=18, ge=4, le=40),
) -> Response:
    return Response(
        content=render_marker_png(normalize_code(code), scale=scale),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/img/marker.svg")
def marker_svg(code: str = Query(default="")) -> Response:
    return Response(
        content=render_marker_svg(normalize_code(code)),
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/img/missing.png")
def marker_missing(code: str = Query(default="")) -> JSONResponse:
    _ = code
    return JSONResponse(status_code=404, content={"error": "image not found"})


@app.get("/tool/image")
def tool_image(request: Request, code: str = Query(default="")) -> dict:
    return payloads.image_payload(base_url(request), normalize_code(code, "IMG7"))


@app.get("/tool/image-a")
def tool_image_a(request: Request, code: str = Query(default="")) -> dict:
    return payloads.image_pair_payload(base_url(request), normalize_code(code, "PAA2"))


@app.get("/tool/image-b")
def tool_image_b(request: Request, code: str = Query(default="")) -> dict:
    return payloads.image_pair_payload(base_url(request), normalize_code(code, "PBB5"))


@app.get("/tool/multi-text")
def tool_multi_text(request: Request, code: str = Query(default="")) -> dict:
    return payloads.multi_text_payload(base_url(request), normalize_code(code, "MTX3"))


@app.get("/tool/text-only")
def tool_text_only(code: str = Query(default="")) -> dict:
    return payloads.text_only_payload(normalize_code(code, "TXT0"))


@app.get("/tool/bad-{kind}")
def tool_invalid(request: Request, kind: str, code: str = Query(default="")) -> dict:
    if kind not in {"empty-url", "bad-detail", "empty-text", "empty-array"}:
        raise HTTPException(status_code=404, detail="unknown invalid variant")
    return payloads.invalid_payload(kind, base_url(request), normalize_code(code, "BAD1"))


@app.get("/tool/many-images")
def tool_many_images(
    request: Request,
    n: int = Query(default=6, ge=1, le=12),
    code: str = Query(default=""),
) -> dict:
    if code:
        prefix = normalize_code(code)
        codes = [f"{prefix}{index + 1}" for index in range(n)]
    else:
        codes = [f"CAP{index + 1}" for index in range(n)]
    return payloads.many_images_payload(base_url(request), codes)


@app.get("/tool/broken-image")
def tool_broken_image(request: Request, code: str = Query(default="")) -> dict:
    return payloads.broken_image_payload(base_url(request), normalize_code(code, "BRK9"))


@app.get("/tool/data-uri")
def tool_data_uri(code: str = Query(default="")) -> dict:
    return payloads.data_uri_payload(normalize_code(code, "DUR1"))


@app.get("/tool/huge")
def tool_huge(
    request: Request,
    chars: int = Query(default=12000, ge=1000, le=60000),
    code: str = Query(default=""),
) -> dict:
    return payloads.huge_payload(base_url(request), normalize_code(code, "HUG4"), chars)


# 挂载在最后：REST 路由优先匹配，未命中的路径交给 MCP 的 /mcp 路由处理，
# 避免出现 /mcp -> /mcp/ 的 307 跳转（部分 MCP 客户端不跟随 POST 重定向）。
app.mount("/", mcp_app)
