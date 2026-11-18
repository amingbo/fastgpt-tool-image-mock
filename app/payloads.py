"""Tool response payloads that follow the PR #7923 tool-content contract."""
from __future__ import annotations

import base64
import random
import string
from typing import Any

from .png import render_marker_png

ALPHABET = "".join(ch for ch in string.ascii_uppercase + string.digits if ch not in "0O1I")


def make_code(length: int = 4, rng: random.Random | None = None) -> str:
    generator = rng or random.SystemRandom()
    return "".join(generator.choice(ALPHABET) for _ in range(length))


def marker_url(base_url: str, code: str, *, scale: int = 18) -> str:
    return f"{base_url.rstrip('/')}/img/marker.png?code={code}&scale={scale}"


def text_part(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def image_part(url: str, *, detail: str | None = None) -> dict[str, Any]:
    image_url: dict[str, Any] = {"url": url}
    if detail is not None:
        image_url["detail"] = detail
    return {"type": "image_url", "image_url": image_url}


def data_uri(code: str) -> str:
    payload = base64.b64encode(render_marker_png(code, scale=12)).decode("ascii")
    return f"data:image/png;base64,{payload}"


def image_payload(base_url: str, code: str) -> dict[str, Any]:
    return {
        "content": [
            text_part(
                f"工具执行完成。图片标记只存在于图片中，文本里没有标记。"
                f"文本核对串：TEXT-{code}-ONLY"
            ),
            image_part(marker_url(base_url, code)),
        ]
    }


def image_pair_payload(base_url: str, code: str) -> dict[str, Any]:
    return image_payload(base_url, code)


def multi_text_payload(base_url: str, code: str) -> dict[str, Any]:
    return {
        "content": [
            text_part(f"第一段核对串：FIRST-{code}"),
            text_part(f"第二段核对串：SECOND-{code}"),
            image_part(marker_url(base_url, code)),
            text_part(f"第三段核对串：THIRD-{code}"),
        ]
    }


def text_only_payload(code: str) -> dict[str, Any]:
    return {"result": f"工具只返回文本，核对串 TEXT-{code}-ONLY"}


def invalid_payload(kind: str, base_url: str, code: str) -> dict[str, Any]:
    base_text = text_part(f"非法内容变体 {kind}，文本核对串 TEXT-{code}-ONLY")
    if kind == "empty-url":
        return {"content": [base_text, image_part("")]}
    if kind == "bad-detail":
        return {"content": [base_text, image_part(marker_url(base_url, code), detail="ultra")]}
    if kind == "empty-text":
        return {"content": [base_text, text_part(""), image_part(marker_url(base_url, code))]}
    if kind == "empty-array":
        return {"content": []}
    raise ValueError(f"unknown invalid kind: {kind}")


def many_images_payload(base_url: str, codes: list[str]) -> dict[str, Any]:
    listing = "，".join(f"{code} -> {marker_url(base_url, code)}" for code in codes)
    return {
        "content": [
            text_part(f"共 {len(codes)} 张图片，全部图片地址：{listing}"),
            *[image_part(marker_url(base_url, code)) for code in codes],
        ]
    }


def broken_image_payload(base_url: str, code: str) -> dict[str, Any]:
    return {
        "content": [
            text_part(f"图片地址不可达，文本核对串 TEXT-{code}-ONLY"),
            image_part(f"{base_url.rstrip('/')}/img/missing.png?code={code}"),
        ]
    }


def data_uri_payload(code: str) -> dict[str, Any]:
    return {
        "content": [
            text_part(f"图片以 data URI 返回，文本核对串 TEXT-{code}-ONLY"),
            image_part(data_uri(code)),
        ]
    }


def huge_payload(base_url: str, code: str, chars: int) -> dict[str, Any]:
    head = f"长响应开头核对串 HEAD-{code}"
    tail = f"长响应结尾核对串 TAIL-{code}"
    filler = "工具返回的长文本内容，用于触发工具响应压缩逻辑。"
    body_length = max(0, chars - len(head) - len(tail))
    body = (filler * (body_length // len(filler) + 1))[:body_length]
    return {
        "content": [
            text_part(f"{head}{body}{tail}"),
            image_part(marker_url(base_url, code)),
        ]
    }
