import streamlit as st
import os
import sys
import time
import tempfile
import yaml
import shutil

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Medical Docs Agent",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paths ─────────────────────────────────────────────────────────────────────
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(AGENT_DIR, "modules")
YAML_PATH = os.path.join(MODULES_DIR, "configs", "document_classes.yaml")

# ── Lazy-load the heavy OCR module so the UI renders fast ─────────────────────
@st.cache_resource(show_spinner="🔄 Loading OCR and classification models…")
def load_ocr_agent():
    sys.path.insert(0, MODULES_DIR)
    from medical_docs_ocr import MedicalDocsOCR  # noqa: E402  (heavy import)
    return MedicalDocsOCR(data_yaml_path=YAML_PATH)


# ── YAML helpers ──────────────────────────────────────────────────────────────
def read_yaml_classes() -> list[dict]:
    """Return the list of class dicts from the YAML file."""
    with open(YAML_PATH, "r") as f:
        data = yaml.safe_load(f)
    return data.get("document_classes", [])


def write_yaml_classes(classes: list[dict]) -> None:
    """Persist the class list back to the YAML file."""
    with open(YAML_PATH, "w") as f:
        yaml.dump({"document_classes": classes}, f,
                  allow_unicode=True, sort_keys=False)


# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Gradient header bar */
.hero-banner {
    background: linear-gradient(135deg, #0f2942 0%, #1a4a7a 50%, #0d3060 100%);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    color: white;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.hero-banner h1 { font-size: 2.2rem; font-weight: 700; margin: 0 0 0.4rem 0; }
.hero-banner p  { font-size: 1.05rem; opacity: 0.85; margin: 0; }

/* Section cards */
.section-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 16px rgba(0,0,0,0.2);
}
.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #60a5fa;
    margin-bottom: 1rem;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}

/* Classification badge */
.class-badge {
    display: inline-flex;
    align-items: center;
    background: #1e3a5f;
    border: 1px solid #3b82f6;
    border-radius: 20px;
    padding: 0.25rem 0.85rem;
    margin: 0.25rem;
    font-size: 0.88rem;
    color: #93c5fd;
    font-weight: 500;
}

/* Result card */
.result-card {
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-top: 0.8rem;
    border-left: 4px solid #3b82f6;
    background: #0f172a;
}
.result-card .doc-name  { font-weight: 600; color: #e2e8f0; font-size: 0.95rem; }
.result-card .doc-class {
    font-size: 1.05rem;
    font-weight: 700;
    color: #34d399;
    margin-top: 0.2rem;
}
.result-card .doc-class.unknown { color: #f87171; }

/* Status pill */
.status-pill {
    display: inline-block;
    padding: 0.3rem 1rem;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.9rem;
}
.status-idle      { background:#1e293b; color:#94a3b8; border:1px solid #475569; }
.status-running   { background:#1c3345; color:#60a5fa; border:1px solid #3b82f6; }
.status-completed { background:#14432a; color:#34d399; border:1px solid #10b981; }
.status-failed    { background:#3b1919; color:#f87171; border:1px solid #ef4444; }
</style>
""", unsafe_allow_html=True)


# ── Session state defaults ─────────────────────────────────────────────────────
if "classes"          not in st.session_state:
    st.session_state.classes = read_yaml_classes()
if "new_class_name"   not in st.session_state:
    st.session_state.new_class_name = ""
if "new_class_desc"   not in st.session_state:
    st.session_state.new_class_desc = ""
if "uploaded_path"    not in st.session_state:
    st.session_state.uploaded_path = None
if "process_status"   not in st.session_state:
    st.session_state.process_status = "idle"
if "process_results"  not in st.session_state:
    st.session_state.process_results = {}
if "output_folder"    not in st.session_state:
    st.session_state.output_folder = os.path.join(
        os.path.expanduser("~"), "Desktop", "classified_docs")


# ══════════════════════════════════════════════════════════════════════════════
# Hero banner
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero-banner">
    <h1>🏥 Medical Docs Agent</h1>
    <p>OCR-powered document classification for medical records</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Greeting
# ══════════════════════════════════════════════════════════════════════════════
with st.container():
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">👋 Welcome</p>', unsafe_allow_html=True)
    greeting = st.text_input(
        "Your name",
        placeholder="Enter your name for a personalised greeting…",
        label_visibility="collapsed",
        key="user_name",
    )
    if greeting:
        st.markdown(
            f"<h4 style='color:#93c5fd;margin:0'>Hello, <strong>{greeting}</strong>! "
            "Configure your document classes below and upload a document to classify.</h4>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Classification management
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<p class="section-title">🗂️ Document Classifications</p>', unsafe_allow_html=True)

# Display current classes as badges
classes = st.session_state.classes
if classes:
    badges_html = " ".join(
        f'<span class="class-badge">📋 {c["name"]}</span>' for c in classes
    )
    st.markdown(badges_html, unsafe_allow_html=True)
else:
    st.info("No document classifications defined yet.")

st.divider()

# ── Add a new classification ──────────────────────────────────────────────────
st.markdown("**Add a classification**")
col_name, col_desc, col_add = st.columns([2, 4, 1])
with col_name:
    new_name = st.text_input("Name", key="input_new_class_name",
                             placeholder="e.g. neurologia")
with col_desc:
    new_desc = st.text_input("Description", key="input_new_class_desc",
                             placeholder="Brief description…")
with col_add:
    st.write("")   # vertical alignment spacer
    st.write("")
    if st.button("➕ Add", use_container_width=True, key="btn_add_class"):
        if new_name.strip():
            new_entry = {"name": new_name.strip().lower(),
                         "description": new_desc.strip()}
            existing_names = [c["name"] for c in st.session_state.classes]
            if new_entry["name"] in existing_names:
                st.warning(f"'{new_entry['name']}' already exists.")
            else:
                st.session_state.classes.append(new_entry)
                st.success(f"Added '{new_entry['name']}'.")
                st.rerun()
        else:
            st.warning("Please enter a class name.")

# ── Remove a classification ────────────────────────────────────────────────────
if classes:
    st.markdown("**Remove a classification**")
    col_sel, col_rem = st.columns([5, 1])
    with col_sel:
        names_list = [c["name"] for c in st.session_state.classes]
        remove_target = st.selectbox(
            "Select class to remove", names_list,
            label_visibility="collapsed", key="remove_target"
        )
    with col_rem:
        st.write("")
        st.write("")
        if st.button("🗑️ Remove", use_container_width=True, key="btn_remove_class"):
            st.session_state.classes = [
                c for c in st.session_state.classes if c["name"] != remove_target
            ]
            st.success(f"Removed '{remove_target}'.")
            st.rerun()

st.divider()

# ── Save to YAML ──────────────────────────────────────────────────────────────
if st.button("💾 Save classification list to YAML", key="btn_save_yaml",
             type="primary", use_container_width=False):
    write_yaml_classes(st.session_state.classes)
    # Invalidate the cached agent so it reloads with the new classes
    load_ocr_agent.clear()
    st.success(f"Saved {len(st.session_state.classes)} classes to `{YAML_PATH}`.")

st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Document upload & output settings
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<p class="section-title">📄 Document Upload</p>', unsafe_allow_html=True)

col_upload, col_output = st.columns([3, 3])

with col_upload:
    uploaded_file = st.file_uploader(
        "Upload a PDF document", type=["pdf"], key="file_uploader"
    )
    if uploaded_file is not None:
        # Save to a temp file so the OCR module can read it from disk
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, uploaded_file.name)
        with open(tmp_path, "wb") as f:
            f.write(uploaded_file.read())
        st.session_state.uploaded_path = tmp_path
        st.success(f"✅ Uploaded: **{uploaded_file.name}**")

with col_output:
    out_folder = st.text_input(
        "Output folder for classified documents",
        value=st.session_state.output_folder,
        key="output_folder_input",
    )
    st.session_state.output_folder = out_folder

st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# OCR options
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<p class="section-title">⚙️ OCR Options</p>', unsafe_allow_html=True)

ocr_method = st.radio(
    "OCR Engine",
    options=["paddle", "llm"],
    index=0,
    horizontal=True,
    key="ocr_method",
    help="'paddle' uses PaddleOCR (fast, CPU). 'llm' uses the GLM vision model (slower, more accurate).",
)

st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Process button
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<p class="section-title">🚀 Run Classification</p>', unsafe_allow_html=True)

can_run = st.session_state.uploaded_path is not None
if not can_run:
    st.info("Upload a PDF document above to enable processing.")

if st.button("▶️ Start Processing", key="btn_run",
             disabled=not can_run, type="primary", use_container_width=False):
    # Reset state
    st.session_state.process_status = "starting"
    st.session_state.process_results = {}

    ocr = load_ocr_agent()
    ocr.set_ocr_method(ocr_method)
    ocr.set_documents_to_process([st.session_state.uploaded_path])
    ocr.set_output_folder(st.session_state.output_folder)

    # Launch background worker
    ocr.classify_documents()
    st.session_state.process_status = "running"
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Live status & results
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<p class="section-title">📊 Pipeline Status & Results</p>',
            unsafe_allow_html=True)

status = st.session_state.process_status

# Status badge
status_html_map = {
    "idle":      ('<span class="status-pill status-idle">⏸ Idle</span>', None),
    "starting":  ('<span class="status-pill status-running">⏳ Starting…</span>', True),
    "running":   ('<span class="status-pill status-running">🔄 Running…</span>', True),
    "completed": ('<span class="status-pill status-completed">✅ Completed</span>', False),
    "failed":    ('<span class="status-pill status-failed">❌ Failed</span>', False),
}
pill_html, is_polling = status_html_map.get(
    status, ('<span class="status-pill status-idle">⏸ Idle</span>', None)
)
st.markdown(pill_html, unsafe_allow_html=True)

# Poll the OCR agent while running
if is_polling:
    try:
        ocr = load_ocr_agent()
        agent_status = ocr.get_status()
        if agent_status == "completed":
            st.session_state.process_status = "completed"
            st.session_state.process_results = ocr.get_results()
            # Organise documents into folders
            ocr.organize_documents(st.session_state.process_results)
        elif agent_status == "failed":
            st.session_state.process_status = "failed"
        # Auto-refresh every 2 s while still running
        with st.spinner("Processing document…"):
            time.sleep(2)
        st.rerun()
    except Exception as e:
        st.error(f"Error polling status: {e}")
        st.session_state.process_status = "failed"

# Results display
results = st.session_state.process_results
if results:
    st.markdown("---")
    st.markdown("**Results**")
    for doc_name, info in results.items():
        classification = info.get("classification", "unknown")
        cls_class = "unknown" if classification == "unknown" else ""
        st.markdown(f"""
        <div class="result-card">
            <div class="doc-name">📄 {doc_name}</div>
            <div class="doc-class {cls_class}">
                Classification: {classification.upper()}
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"📝 Extracted text — {doc_name}"):
            extracted = info.get("extracted_text", "")
            st.text_area(
                label="",
                value=extracted if extracted else "(no text extracted)",
                height=250,
                disabled=True,
                key=f"text_{doc_name}",
            )

    st.markdown(
        f"<small style='color:#64748b;'>Output folder: <code>{st.session_state.output_folder}</code></small>",
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)
