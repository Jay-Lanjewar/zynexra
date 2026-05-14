import streamlit as st
import requests
import time
import uuid

# =========================
# API CONFIG
# =========================
API_BASE = "http://backend:8000"
API_ASK = f"{API_BASE}/ask"
API_ASK_FILE = f"{API_BASE}/ask_file"
API_MODE = f"{API_BASE}/set_mode"
API_GET_MODE = f"{API_BASE}/get_mode"
API_RESET = f"{API_BASE}/reset"
API_EXPORT_REPORT = f"{API_BASE}/export_report"

st.set_page_config(page_title="Zynexra", layout="centered")

# =========================
# SESSION STATE
# =========================
if "history" not in st.session_state:
    st.session_state.history = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "is_streaming" not in st.session_state:
    st.session_state.is_streaming = False

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown("## Zynexra Settings")

    try:
        mode_info = requests.get(
            API_GET_MODE,
            params={"session_id": st.session_state.session_id},
            timeout=2
        ).json()
        current_mode = mode_info.get("mode", "AUDIT")
    except:
        current_mode = "AUDIT"

    st.write(f"**Current Mode:** {current_mode}")

    modes = ["AUDIT", "REDACTION", "ADVISORY"]
    chosen_mode = st.selectbox(
        "Execution Mode",
        modes,
        index=modes.index(current_mode) if current_mode in modes else 0
    )

    if st.button("Apply Mode"):
        requests.post(
            API_MODE,
            json={
                "session_id": st.session_state.session_id,
                "mode": chosen_mode,
            },
            timeout=3
        )
        st.success("Mode updated")
        time.sleep(0.3)
        st.rerun()

    if st.button("Reset Chat"):
        try:
            requests.post(
            API_RESET,
            data={"session_id": st.session_state.session_id},
            timeout=3
            )
        except:
            pass

        st.session_state.history = []
        st.success("Chat cleared")
        time.sleep(0.3)
        st.rerun()

# =========================
# MAIN UI
# =========================
st.title("Zynexra")

# Show chat history
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        
# =========================
# REPORT DOWNLOAD
# =========================
if st.button("Download Last Report"):
    try:
        res = requests.post(
            API_EXPORT_REPORT,
            data={"session_id": st.session_state.session_id},
            timeout=5
        )

        if res.status_code == 200:
            st.download_button(
                label="Click to Save Report",
                data=res.content,
                file_name="zynexra_report.txt",
                mime="text/plain"
            )
        else:
            st.warning("No report available yet.")

    except Exception as e:
        st.error(f"Download failed: {e}")
    
# ---- FILE UPLOAD ----
uploaded_file = st.file_uploader(
    "Upload a .txt or .pdf file (optional)",
    type=["txt", "pdf"]
)

# ---- TEXT INPUT ----
user_msg = st.chat_input("Ask Zynexra...")

# =========================
# SEND REQUEST
# =========================
if user_msg or uploaded_file:
    # Display user message
    display_text = user_msg if user_msg else f"[Uploaded file: {uploaded_file.name}]"
    st.session_state.history.append({"role": "user", "content": display_text})

    with st.chat_message("user"):
        st.write(display_text)

    st.session_state.is_streaming = True

    with st.chat_message("assistant"):
        placeholder = st.empty()
        streamed = ""

        try:
            if uploaded_file:
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        "text/plain"
                    )
                }
                data = {
                    "session_id": st.session_state.session_id,
                    "mode": chosen_mode,
                }

                res = requests.post(
                    API_ASK_FILE,
                    files=files,
                    data=data,
                    stream=True,
                    timeout=300
                )
            else:
                payload = {
                    "question": user_msg,
                    "session_id": st.session_state.session_id,
                    "mode": chosen_mode,
                }

                res = requests.post(
                    API_ASK,
                    json=payload,
                    stream=True,
                    timeout=120
                )

            if res.status_code == 200:
                for chunk in res.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        streamed += chunk
                        placeholder.write(streamed)
            else:
                streamed = f"Error {res.status_code}: {res.text}"
                placeholder.write(streamed)

        except Exception as e:
            streamed = f"Error: {e}"
            placeholder.write(streamed)

        finally:
            st.session_state.is_streaming = False

    st.session_state.history.append({"role": "assistant", "content": streamed})
