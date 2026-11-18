"""Persist a browser conversation in the configured SQLite/PostgreSQL database."""
import uuid

import db


def _phien_id(st):
    raw = st.query_params.get("chat_id", "")
    try:
        # 32 hex characters; random IDs keep separate browser sessions isolated by default.
        phien_id = uuid.UUID(hex=str(raw)).hex
    except (ValueError, TypeError, AttributeError):
        phien_id = uuid.uuid4().hex
        st.query_params["chat_id"] = phien_id
    return phien_id


def nap_phien(st, khoa_tin_nhan, khoa_lich_su):
    """Load the current URL's chat once into Streamlit state and return its ID."""
    db.khoi_tao()
    phien_id = _phien_id(st)
    if st.session_state.get("_chat_da_nap_id") != phien_id:
        saved = db.doc_phien(phien_id) or {}
        if isinstance(saved, dict):
            st.session_state[khoa_tin_nhan] = saved.get("tin_nhan", [])
            st.session_state[khoa_lich_su] = saved.get("lich_su_gemini", [])
        else:
            st.session_state[khoa_tin_nhan] = []
            st.session_state[khoa_lich_su] = []
        st.session_state["_chat_da_nap_id"] = phien_id
    st.session_state.setdefault(khoa_tin_nhan, [])
    st.session_state.setdefault(khoa_lich_su, [])
    return phien_id


def luu_phien(st, khoa_tin_nhan, khoa_lich_su):
    phien_id = st.session_state.get("_chat_da_nap_id") or _phien_id(st)
    db.luu_phien(phien_id, {
        "tin_nhan": st.session_state.get(khoa_tin_nhan, []),
        "lich_su_gemini": st.session_state.get(khoa_lich_su, []),
    })


def xoa_phien(st, khoa_tin_nhan, khoa_lich_su):
    phien_id = st.session_state.get("_chat_da_nap_id") or _phien_id(st)
    db.xoa_phien(phien_id)
    st.session_state[khoa_tin_nhan] = []
    st.session_state[khoa_lich_su] = []
    st.session_state["_chat_da_nap_id"] = phien_id
