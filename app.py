import html
import streamlit as st
from dotenv import load_dotenv
from rag import SchemeRetriever
from eligibility import build_profile_from_text, assess_scheme, infer_category_from_query, is_service_query
from llm import explain_results

load_dotenv()

st.set_page_config(
    page_title="Punjab Scheme Finder",
    page_icon="🇵🇰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Visual theme ----------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #f7fbf8 0%, #ffffff 42%, #f8f7ff 100%);
    }
    .hero {
        padding: 28px 30px;
        border-radius: 24px;
        background: linear-gradient(135deg, #075e54 0%, #087f6d 48%, #6b4fd3 100%);
        color: white;
        box-shadow: 0 14px 35px rgba(20, 55, 70, .14);
        margin-bottom: 24px;
    }
    .hero h1 { margin: 0 0 8px 0; font-size: 2.35rem; }
    .hero p { margin: 0; opacity: .94; font-size: 1.02rem; }
    .mini-card {
        padding: 17px 18px;
        border-radius: 18px;
        background: rgba(255,255,255,.88);
        border: 1px solid #e7e8ef;
        box-shadow: 0 7px 20px rgba(35, 45, 60, .06);
        min-height: 108px;
    }
    .mini-icon { font-size: 1.55rem; }
    .mini-title { font-weight: 700; margin-top: 6px; }
    .mini-text { color: #667085; font-size: .88rem; margin-top: 3px; }
    .scheme-card {
        border: 1px solid #e6e8ef;
        border-radius: 20px;
        padding: 21px 22px;
        background: #ffffff;
        box-shadow: 0 9px 25px rgba(31, 41, 55, .07);
        margin-bottom: 18px;
        min-height: 350px;
    }
    .scheme-top { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }
    .scheme-name { font-size: 1.12rem; font-weight: 750; line-height: 1.3; color:#172033; }
    .badge { display:inline-block; padding:5px 10px; border-radius:999px; font-size:.75rem; font-weight:700; white-space:nowrap; }
    .education { background:#eee9ff; color:#5a3eb7; }
    .agriculture { background:#e4f7eb; color:#177245; }
    .business { background:#fff0dc; color:#a45a00; }
    .energy { background:#fff8cf; color:#806500; }
    .youth { background:#e5f3ff; color:#17649a; }
    .social { background:#ffe7ee; color:#a33c5a; }
    .neutral { background:#eef1f5; color:#556070; }
    .scheme-desc { color:#4b5565; margin:13px 0 16px; line-height:1.55; }
    .scheme-section-title { font-weight:700; color:#273142; margin-bottom:5px; }
    .scheme-body { color:#596273; font-size:.9rem; line-height:1.5; }
    .why { padding:10px 12px; background:#f7f8fb; border-radius:12px; color:#4b5563; font-size:.88rem; margin-top:12px; }
    .status-likely { background:#e9f8ef; border-left:4px solid #2e9d63; }
    .status-verify { background:#fff7df; border-left:4px solid #d59b24; }
    .status-no { background:#fff0f0; border-left:4px solid #d95353; }
    .official-link { display:inline-block; margin-top:15px; padding:9px 14px; border-radius:10px; background:#075e54; color:white !important; text-decoration:none !important; font-weight:700; font-size:.86rem; }
    .section-label { font-size:1.45rem; font-weight:750; color:#172033; margin: 8px 0 14px; }
    .field-card {
        border:1px solid #e1e5ec; border-radius:14px; padding:13px 14px 11px;
        background:#ffffff; min-height:105px; margin-bottom:8px;
        box-shadow:0 2px 8px rgba(23,32,51,.05);
    }
    .field-card-title { font-weight:750; color:#172033; font-size:1rem; margin-bottom:4px; }
    .field-card-text { color:#667085; font-size:.79rem; line-height:1.35; }
    .field-selected { border:2px solid #ff5a5f; background:#fff7f7; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #f0faf6 0%, #f8f6ff 100%); }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color:#17483f; }
    div.stButton > button[kind="primary"] { border-radius:12px; font-weight:700; }
    div.stButton > button { border-radius:12px; }

    /* FORCE LIGHT UI: do not let browser/Streamlit dark preference create mixed themes. */
    :root, html, body {
        color-scheme: light !important;
    }
    html, body, .stApp, [data-testid="stAppViewContainer"],
    [data-testid="stMainViewContainer"], [data-testid="stMain"],
    [data-testid="stSidebar"], [data-testid="stHeader"] {
        background-color: #ffffff !important;
        color: #172033 !important;
    }
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #f7fbf8 0%, #ffffff 42%, #f8f7ff 100%) !important;
    }
    [data-testid="stHeader"] {
        background: #ffffff !important;
        border-bottom: 1px solid #eef0f4 !important;
    }
    [data-testid="stToolbar"], [data-testid="stDecoration"] {
        background: #ffffff !important;
    }

    /* Sidebar text and controls */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f0faf6 0%, #f8f6ff 100%) !important;
    }
    [data-testid="stSidebar"] * {
        color: #172033 !important;
    }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] button, [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #172033 !important;
        border-color: #d9dee8 !important;
    }
    [data-testid="stSidebar"] svg {
        fill: #667085 !important;
        color: #667085 !important;
    }

    /* Main inputs */
    /* Remove the small clear (×) affordance from the age number field. */
    [data-testid="stNumberInput"] [data-baseweb="input"] button {
        display: none !important;
    }

    .stTextInput input, .stNumberInput input, .stTextArea textarea,
    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] input {
        color: #172033 !important;
        -webkit-text-fill-color: #172033 !important;
        background-color: #ffffff !important;
        border-color: #d9dee8 !important;
        color-scheme: light !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder,
    .stNumberInput input::placeholder {
        color: #7b8494 !important;
        -webkit-text-fill-color: #7b8494 !important;
        opacity: 1 !important;
    }
    [data-testid="stWidgetLabel"] * {
        color: #344054 !important;
    }

    /* Select/dropdown text and popup */
    [data-baseweb="select"] *, [role="listbox"] *,
    [data-baseweb="popover"] *, [data-baseweb="menu"] * {
        color: #172033 !important;
        background-color: #ffffff !important;
    }
    [data-baseweb="select"] svg {
        color: #667085 !important;
        fill: #667085 !important;
    }

    /* Buttons: always readable in both browser themes. */
    div.stButton > button {
        background: #ffffff !important;
        color: #172033 !important;
        -webkit-text-fill-color: #172033 !important;
        border: 1px solid #d9dee8 !important;
        box-shadow: 0 2px 8px rgba(31, 41, 55, .05) !important;
    }
    div.stButton > button:hover {
        background: #f7f9fc !important;
        color: #172033 !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #ff5a5f, #ff4b55) !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        border: none !important;
    }
    div.stButton > button[kind="primary"] * {
        color: #ffffff !important;
    }

    /* Native dark-mode media preference: keep the whole app light. */
    @media (prefers-color-scheme: dark) {
        html, body, .stApp, [data-testid="stAppViewContainer"],
        [data-testid="stMain"], [data-testid="stHeader"], [data-testid="stSidebar"] {
            background-color: #ffffff !important;
            color: #172033 !important;
        }
        .stTextInput input, .stNumberInput input, .stTextArea textarea,
        div[data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #172033 !important;
            -webkit-text-fill-color: #172033 !important;
        }
    }

</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_retriever():
    return SchemeRetriever("data/schemes.json")

retriever = get_retriever()

st.markdown("""
<div class="hero">
  <h1>🇵🇰 Punjab Government Scheme Finder</h1>
  <p>Tell us what you need in simple words. We’ll help you discover relevant Punjab Government schemes.</p>
</div>
""", unsafe_allow_html=True)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 👤 Your profile")
    st.caption("* Required for personalized search")

    # Text input is used intentionally instead of number_input so the browser/
    # Streamlit number-field clear (×) affordance never appears.
    age_raw = st.text_input("Age *", placeholder="e.g. 24", max_chars=3)
    district = st.text_input("District *", placeholder="e.g. Lahore")
    occupation = st.selectbox(
        "Occupation *",
        ["Not specified", "Student", "Farmer", "Business owner", "Self-employed", "Employed", "Unemployed", "Other"],
    )

# Optional fields intentionally removed from the MVP UI. The app relies on the
# three basic profile fields plus the user's natural-language need.
age = None
if age_raw.strip().isdigit():
    parsed_age = int(age_raw.strip())
    if 1 <= parsed_age <= 100:
        age = parsed_age

student = False
farmer = False
business_owner = False
income = None
marks = None

# ---------- How it works ----------
c1, c2, c3 = st.columns(3)
for col, icon, title, text in [
    (c1, "💬", "Tell us your need", "Write naturally — no special keywords required."),
    (c2, "🧠", "We find matches", "Semantic search looks through the scheme knowledge base."),
    (c3, "🔗", "Verify & apply", "Open the official Government of Punjab source."),
]:
    with col:
        st.markdown(f'<div class="mini-card"><div class="mini-icon">{icon}</div><div class="mini-title">{title}</div><div class="mini-text">{text}</div></div>', unsafe_allow_html=True)

profile_ready = age is not None and bool(district.strip()) and occupation != "Not specified"
if profile_ready:
    st.caption(f"👤 Profile: **{int(age)} years · {district.strip()} · {occupation}**  →  now tell us the problem or support you need.")
else:
    st.caption("👤 First enter your basic profile in the sidebar, then tell us what you need. Your need will drive the search.")

st.markdown('<div class="section-label">💬 What do you need?</div>', unsafe_allow_html=True)
st.caption("Choose a field for a quicker search, or let AI decide from your need.")

# Six easy-to-understand field shortcuts. They are optional: the user's
# natural-language need remains the primary search signal.
field_options = [
    ("🎓", "Education", "Scholarships, fees, laptops & student support", "Education"),
    ("🌾", "Agriculture", "Farming, tractors, Kissan Card & subsidies", "Agriculture"),
    ("💼", "Business", "Business loans, financing & entrepreneurship", "Business"),
    ("☀️", "Energy", "Solar panels & electricity support", "Energy"),
    ("🤝", "Social Welfare", "Financial assistance & welfare support", "Social Welfare"),
    ("🐄", "Livestock", "Cattle, dairy & livestock support", "Livestock"),
]

if "selected_field" not in st.session_state:
    st.session_state.selected_field = None

st.markdown("**Quickly choose a field (optional)**")
for row_start in range(0, len(field_options), 3):
    cols = st.columns(3)
    for col, (icon, title, desc, category) in zip(cols, field_options[row_start:row_start+3]):
        with col:
            selected = st.session_state.selected_field == category
            card_class = "field-card field-selected" if selected else "field-card"
            st.markdown(
                f'<div class="{card_class}"><div class="field-card-title">{icon} {title}</div>'
                f'<div class="field-card-text">{desc}</div></div>',
                unsafe_allow_html=True,
            )
            if st.button("Selected ✓" if selected else "Choose", key=f"field_{category}", use_container_width=True):
                st.session_state.selected_field = None if selected else category
                st.rerun()

selected_category = st.session_state.selected_field
if selected_category:
    st.caption(f"Selected field: **{selected_category}** · You can still describe your need in your own words below.")
else:
    st.caption("No field selected — AI will understand the field from your need.")

query = st.text_area(
    "Describe your situation in your own words *",
    height=125,
    placeholder=(
        "Example: I need help paying my university fees."
    ),
    label_visibility="collapsed",
)

b1, b2 = st.columns([1, 1])
with b1:
    find = st.button("🔎 Find schemes for me", type="primary", use_container_width=True)
with b2:
    browse = st.button("📋 Browse all schemes", use_container_width=True)

if find or browse:
    if find:
        missing = []
        if age is None: missing.append("Age")
        if not district.strip(): missing.append("District")
        if occupation == "Not specified": missing.append("Occupation")
        if not query.strip(): missing.append("What you need")
        if missing:
            st.error("Please enter the required field(s): " + ", ".join(missing) + ".")
            st.stop()

    profile = build_profile_from_text(
        query=query, age=age, district=district, occupation=occupation,
        student=student, farmer=farmer, business_owner=business_owner,
        income=income, marks=marks,
    )

    if browse:
        results = retriever.browse(category=None, top_k=100)
        explanation = None
    else:
        # IMPORTANT: the user's stated need is the primary retrieval signal.
        # Profile facts are used mainly for preliminary eligibility, not to force a category.
        inferred_category = infer_category_from_query(query, {})
        # A user-selected field is an optional search constraint. If no field is
        # selected, the system infers intent from the natural-language need.
        active_category = selected_category or inferred_category
        retrieval_query = query.strip()

        results = retriever.search(
            retrieval_query,
            top_k=5,
            category=active_category,
        )

        # Maryam Ki Dastak is a government-service platform, not a generic scheme.
        # It should only be surfaced when the user explicitly asks for a service/document/license.
        if not is_service_query(query):
            results = [(item, score) for item, score in results if item.get("name") != "Maryam Ki Dastak"]

        explanation = explain_results(query.strip(), profile, results)

    if not results:
        if find and is_service_query(query):
            st.info("This sounds like a Punjab government service request rather than a financial/support scheme. You can use Maryam Ki Dastak to find the relevant service.")
            st.markdown(
                '<a class="official-link" href="https://dastak.punjab.gov.pk/citizen/services" target="_blank">🔗 Open official Dastak services</a>',
                unsafe_allow_html=True,
            )
        else:
            st.warning("No strong match was found in the current dataset. Try describing your need in a little more detail.")
    else:
        st.markdown('<div class="section-label">🎯 Recommended schemes</div>', unsafe_allow_html=True)
        if explanation:
            st.info(explanation)
        if find:
            inferred = infer_category_from_query(query, profile)
            if inferred:
                st.caption(f"We detected your main need as **{inferred}** and prioritized schemes in that area.")
        st.caption(f"Showing {len(results)} result(s). These are preliminary matches, not official eligibility decisions.")

        # Two-column card grid
        for start in range(0, len(results), 2):
            cols = st.columns(2)
            for offset, col in enumerate(cols):
                idx = start + offset
                if idx >= len(results):
                    continue
                item, score = results[idx]
                assessment = assess_scheme(item, profile)

                cat = item.get("category", "Other")
                cat_class = {
                    "Education":"education", "Agriculture":"agriculture", "Business":"business",
                    "Energy":"energy", "Youth":"youth", "Social Welfare":"social"
                }.get(cat, "neutral")
                status_class = {
                    "likely":"status-likely", "needs_verification":"status-verify", "not_eligible":"status-no"
                }[assessment["status"]]
                status_text = {
                    "likely":"🟢 Likely match", "needs_verification":"🟡 Needs verification", "not_eligible":"🔴 Basic requirement mismatch"
                }[assessment["status"]]

                name = html.escape(item["name"])
                desc = html.escape(item.get("description", ""))
                benefits = html.escape(item.get("benefits", ""))
                eligibility_text = "<br>".join("• " + html.escape(x) for x in item.get("eligibility", []))
                why = html.escape(" ".join(assessment.get("reasons", [])))
                url = html.escape(item.get("official_url", ""), quote=True)

                card = f"""
                <div class="scheme-card">
                  <div class="scheme-top">
                    <div class="scheme-name">{name}</div>
                    <span class="badge {cat_class}">{html.escape(cat)}</span>
                  </div>
                  <div class="scheme-desc">{desc}</div>
                  <div class="scheme-section-title">What you get</div>
                  <div class="scheme-body">{benefits}</div>
                  <div style="height:12px"></div>
                  <div class="scheme-section-title">Who it is for</div>
                  <div class="scheme-body">{eligibility_text}</div>
                  <div class="why {status_class}"><b>{status_text}</b><br>{why}</div>
                  <a class="official-link" href="{url}" target="_blank">🔗 Open official source</a>
                </div>
                """
                with col:
                    st.markdown(card, unsafe_allow_html=True)

st.divider()
st.caption("This is an information and discovery assistant. Matches and eligibility labels are preliminary. Always verify the latest eligibility, deadlines and application instructions on the linked official Government of Punjab source.")
