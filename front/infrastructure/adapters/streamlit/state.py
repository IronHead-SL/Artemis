from __future__ import annotations

from typing import Optional
import streamlit as st


def init_session_state() -> None:
    defaults = {
        "uploaded_image":        None,
        "recommendations":       None,
        "selected_artwork":      None,
        "artwork_history":       [],
        "artwork_details_cache": {},
        "artwork_data_cache":    {},
        "loading_states":        {},
        "_img_bytes_cache":      {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_state() -> None:
    for key in ["uploaded_image", "recommendations", "selected_artwork",
                 "artwork_history", "artwork_details_cache"]:
        st.session_state.pop(key, None)


def push_history(artwork_id: str, title: str) -> None:
    hist: list = st.session_state.get("artwork_history", [])
    if not hist or hist[-1].get("id") != artwork_id:
        hist.append({"id": artwork_id, "title": title})
    st.session_state["artwork_history"] = hist


def get_cached_details(artwork_id: str) -> Optional[dict]:
    return st.session_state.get("artwork_details_cache", {}).get(artwork_id)


def cache_details(artwork_id: str, details: dict) -> None:
    cache = st.session_state.get("artwork_details_cache", {})
    cache[artwork_id] = details
    st.session_state["artwork_details_cache"] = cache


def store_artwork(artwork: dict) -> None:
    st.session_state.setdefault("artwork_data_cache", {})[artwork["id"]] = artwork


def get_artwork(artwork_id: str) -> Optional[dict]:
    return st.session_state.get("artwork_data_cache", {}).get(artwork_id)
