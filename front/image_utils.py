from __future__ import annotations

import base64
import io
from typing import Optional

import requests as _requests
import streamlit as st
from PIL import Image

_IMG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0 ArtemisBot/1.0"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.metmuseum.org/",
}
_IMG_TIMEOUT  = 8
_IMG_CACHE_KEY = "_img_bytes_cache"


def pil_to_bytes(img: Image.Image, fmt: str = "JPEG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def image_to_base64(img_bytes: bytes) -> str:
    return base64.b64encode(img_bytes).decode()


def load_image_safe(uploaded_file) -> Optional[Image.Image]:
    try:
        return Image.open(uploaded_file).convert("RGB")
    except Exception:
        return None


def resize_image(img: Image.Image, max_size: int = 600) -> Image.Image:
    w, h = img.size
    if max(w, h) <= max_size:
        return img
    scale = max_size / max(w, h)
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


def fetch_image_bytes(url: str) -> Optional[bytes]:
    if not url:
        return None
    cache: dict = st.session_state.setdefault(_IMG_CACHE_KEY, {})
    if url in cache:
        return cache[url]
    try:
        resp = _requests.get(url, headers=_IMG_HEADERS, timeout=_IMG_TIMEOUT)
        resp.raise_for_status()
        cache[url] = resp.content
        return resp.content
    except Exception:
        cache[url] = None
        return None


def prefetch_images_parallel(urls: list[str], max_workers: int = 8) -> None:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    cache: dict = st.session_state.setdefault(_IMG_CACHE_KEY, {})
    missing = [u for u in urls if u and u not in cache]
    if not missing:
        return

    def _fetch(url: str) -> tuple[str, Optional[bytes]]:
        try:
            resp = _requests.get(url, headers=_IMG_HEADERS, timeout=_IMG_TIMEOUT)
            resp.raise_for_status()
            return url, resp.content
        except Exception:
            return url, None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for url, data in [f.result() for f in as_completed({executor.submit(_fetch, u): u for u in missing})]:
            cache[url] = data


def show_image_card(url: str, max_height: int = 300) -> None:
    data = fetch_image_bytes(url)
    if data:
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
            w, h = img.size
            side = min(w, h)
            img  = img.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
            img  = img.resize((400, 400), Image.LANCZOS)
            buf  = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            b64  = image_to_base64(buf.getvalue())
            st.markdown(
                f"<img src='data:image/jpeg;base64,{b64}' "
                f"style='width:100%;aspect-ratio:1/1;object-fit:cover;"
                f"display:block;border-radius:4px 4px 0 0;max-height:{max_height}px;'>",
                unsafe_allow_html=True,
            )
            return
        except Exception:
            pass
    st.markdown(
        f"<div style='width:100%;aspect-ratio:1/1;max-height:{max_height}px;"
        "background:linear-gradient(135deg,#1a1a1a,#2a2a2a);border-radius:4px 4px 0 0;'></div>",
        unsafe_allow_html=True,
    )


def show_image_detail(url: str) -> None:
    data = fetch_image_bytes(url)
    if data:
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
            w, h = img.size
            if w > 600:
                img = img.resize((600, int(h * 600 / w)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=88)
            st.image(buf.getvalue(), use_container_width=True)
            return
        except Exception:
            pass
    st.markdown(
        "<div style='width:100%;aspect-ratio:3/4;"
        "background:linear-gradient(135deg,#1a1a1a,#2a2a2a);border-radius:4px;'></div>",
        unsafe_allow_html=True,
    )
