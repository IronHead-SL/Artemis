from __future__ import annotations

from PIL import Image
import streamlit as st

from state import init_session_state
from styles import inject_css
from view_upload import view_upload
from view_results import view_results
from view_detail import view_detail

img = Image.open("artemis-logo.png")
st.set_page_config(
    page_title="Artemis · Art Discovery",
    page_icon=img,
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()


def main() -> None:
    uploaded = st.session_state.get("uploaded_image")
    recs     = st.session_state.get("recommendations")
    selected = st.session_state.get("selected_artwork")

    if uploaded is None or recs is None:
        view_upload()
    elif selected is not None:
        view_detail()
    else:
        view_results()


if __name__ == "__main__":
    main()
