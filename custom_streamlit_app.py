import json
import os
import uuid
from datetime import datetime

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

DB_FILE = "chats.json"
DEFAULT_SYSTEM = "You are a helpful assistant."

st.set_page_config(page_title="Custom ChatGPT", page_icon="💬", layout="wide")

# ---------- Theme + Claude-style layout ----------
st.markdown(
    """
    <style>
    /* hide only Deploy / menu, keep the sidebar open-close button */
    [data-testid="stAppDeployButton"], [data-testid="stMainMenu"],
    [data-testid="stDecoration"], footer { display: none !important; }
    header[data-testid="stHeader"] { background: transparent; }

    /* sidebar open / close buttons always visible, in gold */
    [data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    [data-testid="stExpandSidebarButton"] *, [data-testid="stSidebarCollapseButton"] *,
    [data-testid="collapsedControl"] *, [data-testid="stSidebarCollapsedControl"] * {
        color: #d4af37 !important;
    }

    /* keep the bottom input in the same centered column */
    [data-testid="stBottom"], [data-testid="stBottom"] > div {
        background: transparent !important;
    }
    [data-testid="stBottomBlockContainer"] {
        max-width: 780px;
        margin: 0 auto;
    }

    .stApp {
        background: radial-gradient(circle at top, #2a1458 0%, #120826 65%);
    }
    /* centered reading column like Claude */
    .block-container {
        max-width: 780px;
        padding-top: 2.5rem;
        padding-bottom: 6rem;
    }

    /* sidebar */
    [data-testid="stSidebar"] {
        background: #0e0620;
        border-right: 1px solid rgba(212,175,55,0.35);
    }
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        justify-content: flex-start;
        text-align: left;
        background: transparent;
        border: none;
        color: #f5ebd0;
        border-radius: 10px;
        padding: 0.45rem 0.7rem;
        box-shadow: none;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(212,175,55,0.14);
        color: #fff;
    }
    .st-key-active_chat_btn button {
        background: rgba(212,175,55,0.22) !important;
        color: #ffe9a6 !important;
        font-weight: 600;
    }
    .st-key-new_chat_btn button {
        background: linear-gradient(90deg, #d4af37, #b8902a) !important;
        color: #1b0d3a !important;
        font-weight: 700;
        justify-content: center !important;
    }
    .sb-label {
        color: #d4af37; font-size: 0.78rem; letter-spacing: 0.08em;
        text-transform: uppercase; margin: 1.1rem 0 0.3rem 0.4rem;
    }
    .sb-brand {
        color: #d4af37; font-family: Georgia, serif; font-size: 1.35rem;
        font-weight: 700; margin-bottom: 0.8rem;
    }

    /* greeting */
    .greeting {
        text-align: center; color: #f5ebd0; font-family: Georgia, serif;
        font-size: 2.5rem; margin: 18vh 0 1.8rem 0;
    }
    .greeting span { color: #d4af37; }

    /* messages */
    [data-testid="stChatMessage"] {
        background: transparent;
        border: none;
        padding: 0.4rem 0;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: rgba(212,175,55,0.08);
        border: 1px solid rgba(212,175,55,0.18);
        border-radius: 16px;
        padding: 0.6rem 0.9rem;
    }

    /* big rounded input */
    [data-testid="stChatInput"] {
        border-radius: 24px;
        border: 1px solid rgba(212,175,55,0.55);
        background: #1a0d38;
        box-shadow: 0 6px 24px rgba(0,0,0,0.35);
    }
    [data-testid="stChatInput"] textarea { color: #f5ebd0; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Storage (chats survive server restart) ----------
def load_chats():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_chats():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.chats, f, ensure_ascii=False, indent=2)


def new_chat():
    cid = str(uuid.uuid4())
    st.session_state.chats[cid] = {
        "title": "New chat",
        "system": DEFAULT_SYSTEM,
        "messages": [],
        "updated": datetime.now().isoformat(),
    }
    st.session_state.active = cid
    save_chats()
    return cid


def sorted_chat_ids():
    chats = st.session_state.chats
    return sorted(chats, key=lambda c: chats[c].get("updated", ""), reverse=True)


# ---------- Session state ----------
if "chats" not in st.session_state:
    st.session_state.chats = load_chats()
if "active" not in st.session_state:
    ids = sorted_chat_ids()
    st.session_state.active = ids[0] if ids else None
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

# ---------- Login gate: API key ke bina aage access nahi ----------
if not st.session_state.api_key:
    st.markdown("<div style='height:10vh'></div>", unsafe_allow_html=True)
    st.markdown(
        "<h1 style='text-align:center;color:#d4af37;font-family:Georgia,serif'>💬 Custom ChatGPT</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#f5ebd0'>Enter your OpenAI API key to continue</p>",
        unsafe_allow_html=True,
    )
    with st.form("login_form"):
        name_in = st.text_input("Your name (optional)", placeholder="e.g. kanwal")
        key_in = st.text_input("OpenAI API key", type="password", placeholder="sk-...")
        enter = st.form_submit_button("Enter 🔑", type="primary", use_container_width=True)
    if enter:
        key_in = key_in.strip()
        if not key_in:
            st.error("API key is empty.")
        else:
            try:
                from openai import OpenAI

                with st.spinner("Checking your key..."):
                    OpenAI(api_key=key_in).models.list()
                st.session_state.api_key = key_in
                st.session_state.user_name = name_in.strip()
                st.rerun()
            except Exception:
                st.error("This API key doesn't look valid. Please check it and try again.")
    st.caption("Your key is kept only for this session and is never saved to a file.")
    st.stop()

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("<div class='sb-brand'>💬 Custom ChatGPT</div>", unsafe_allow_html=True)

    if st.button("＋  New chat", key="new_chat_btn"):
        new_chat()
        st.rerun()

    search = st.text_input(
        "Search", placeholder="🔍 Search chats", label_visibility="collapsed"
    ).strip().lower()

    st.markdown("<div class='sb-label'>Recents</div>", unsafe_allow_html=True)
    shown = 0
    for cid in sorted_chat_ids():
        chat = st.session_state.chats[cid]
        if search and search not in chat["title"].lower():
            continue
        shown += 1
        is_active = cid == st.session_state.active
        c1, c2 = st.columns([6, 1])
        with c1:
            key = "active_chat_btn" if is_active else f"sel_{cid}"
            if st.button(chat["title"][:30], key=key):
                st.session_state.active = cid
                st.rerun()
        with c2:
            if st.button("✕", key=f"del_{cid}"):
                del st.session_state.chats[cid]
                ids = sorted_chat_ids()
                st.session_state.active = ids[0] if ids else None
                save_chats()
                st.rerun()
    if shown == 0:
        st.caption("No chats found.")

    st.markdown("<div class='sb-label'>Settings</div>", unsafe_allow_html=True)
    with st.expander("Model & system role"):
        model_name = st.text_input("Model", value="gpt-5.2")
        active_id = st.session_state.active
        if active_id and active_id in st.session_state.chats:
            sys_val = st.text_area(
                "System role",
                value=st.session_state.chats[active_id]["system"],
                key=f"sys_{active_id}",
                height=110,
            )
            if sys_val != st.session_state.chats[active_id]["system"]:
                st.session_state.chats[active_id]["system"] = sys_val
                save_chats()
        else:
            st.caption("Start a chat first, then you can set the system role.")

    if st.button("🔒  Logout", key="logout_btn"):
        st.session_state.api_key = ""
        st.session_state.user_name = ""
        st.rerun()

# ---------- Main area ----------
active_id = st.session_state.active
chat = st.session_state.chats.get(active_id) if active_id else None
has_messages = bool(chat and chat["messages"])

prompt = None
holder = st.empty()

if has_messages:
    with holder.container():
        for m in chat["messages"]:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
    prompt = st.chat_input("Reply...", key="input_bottom")
else:
    name = st.session_state.user_name
    greet = f"Hello, <span>{name}</span>" if name else "How can I <span>help</span> you today?"
    with holder.container():
        st.markdown(f"<div class='greeting'>{greet}</div>", unsafe_allow_html=True)
        prompt = st.chat_input("How can I help you today?", key="input_center")

if prompt:
    if not chat:
        active_id = new_chat()
        chat = st.session_state.chats[active_id]

    if not has_messages:
        holder.empty()  # remove the greeting

    chat["messages"].append({"role": "user", "content": prompt})
    if chat["title"] == "New chat":
        chat["title"] = prompt.strip().replace("\n", " ")[:40]

    with st.chat_message("user"):
        st.markdown(prompt)

    history = [SystemMessage(content=chat["system"] or DEFAULT_SYSTEM)]
    for m in chat["messages"]:
        if m["role"] == "user":
            history.append(HumanMessage(content=m["content"]))
        else:
            history.append(AIMessage(content=m["content"]))

    try:
        llm = ChatOpenAI(model=model_name, api_key=st.session_state.api_key)
        with st.chat_message("assistant"):
            reply = st.write_stream(
                c.content for c in llm.stream(history) if c.content
            )
        chat["messages"].append({"role": "assistant", "content": reply})
        chat["updated"] = datetime.now().isoformat()
        save_chats()
        st.rerun()  # refresh sidebar (title / order)
    except Exception as e:
        chat["messages"].pop()
        save_chats()
        st.error(f"Error: {e}")