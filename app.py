import html
import streamlit as st
from dotenv import load_dotenv
from rag import SchemeRetriever
from eligibility import (
    build_profile_from_text,
    assess_scheme,
    infer_category_from_query,
    is_service_query,
)
from llm import explain_results

load_dotenv()

st.set_page_config(
    page_title="SchemeSaathi - Punjab Government Scheme Finder",
    page_icon="🇵🇰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# CONSTANTS & UTILITIES
# ============================================================

PUNJAB_DISTRICTS = [
    "Attock",
    "Bahawalnagar",
    "Bahawalpur",
    "Bhakkar",
    "Chakwal",
    "Chiniot",
    "Dera Ghazi Khan",
    "Faisalabad",
    "Gujranwala",
    "Gujrat",
    "Hafizabad",
    "Jhang",
    "Jhelum",
    "Kasur",
    "Khanewal",
    "Khushab",
    "Lahore",
    "Layyah",
    "Lodhran",
    "Mandi Bahauddin",
    "Mianwali",
    "Multan",
    "Muzaffargarh",
    "Nankana Sahib",
    "Narowal",
    "Okara",
    "Pakpattan",
    "Rahim Yar Khan",
    "Rajanpur",
    "Rawalpindi",
    "Sahiwal",
    "Sargodha",
    "Sheikhupura",
    "Sialkot",
    "Toba Tek Singh",
    "Vehari",
]

def valid_need_query(text):
    text = text.strip()

    if not text:
        return False, "Please describe what you need."

    # Reject numbers / punctuation only
    if not any(char.isalpha() for char in text):
        return False, "Please describe your need using words, not only numbers or symbols."

    # Very short meaningless input
    letters = [c for c in text if c.isalpha()]

    if len(letters) < 3:
        return False, "Please provide a little more detail about what you need."

    return True, ""


# ============================================================
# VISUAL THEME
# ============================================================

st.markdown("""
<style>

.stApp {
    background: linear-gradient(
        180deg,
        #f7fbf8 0%,
        #ffffff 45%,
        #f8f7ff 100%
    );
}

/* ---------- BRANDING / LOGO HEADER ---------- */

.brand-header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 0 20px 0;
    margin-bottom: 8px;
}

.brand-logo {
    width: 52px;
    height: 52px;
    border-radius: 14px;
    background: linear-gradient(135deg, #075e54 0%, #087f6d 100%);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.6rem;
    font-weight: 800;
    box-shadow: 0 6px 16px rgba(7, 94, 84, 0.25);
    border: 2px solid #ffffff;
    position: relative;
}

.brand-logo::after {
    content: "•";
    position: absolute;
    top: 4px;
    right: 6px;
    font-size: 0.8rem;
    color: #ffd700;
}

.brand-title-group h1 {
    margin: 0;
    font-size: 1.85rem;
    font-weight: 800;
    color: #172033;
    line-height: 1.1;
}

.brand-title-group .sub-heading {
    margin: 3px 0 0 0;
    color: #075e54;
    font-size: 0.95rem;
    font-weight: 700;
    letter-spacing: 0.3px;
}

.brand-tagline {
    margin-top: 4px;
    color: #667085;
    font-size: 0.92rem;
}

/* ---------- PROFILE ---------- */

.profile-box {
    background: #ffffff;
    border: 1px solid #e3e7ee;
    border-radius: 20px;
    padding: 20px 22px;
    margin: 8px 0 18px 0;
    box-shadow: 0 7px 22px rgba(31, 41, 55, .06);
}

.profile-title {
    font-size: 1.05rem;
    font-weight: 750;
    color: #172033;
    margin-bottom: 4px;
}

.profile-subtitle {
    color: #667085;
    font-size: .88rem;
    margin-bottom: 14px;
}

/* Profile pill */

.profile-pill {
    display: inline-flex;
    align-items: center;
    gap: 9px;
    padding: 9px 16px;
    border: 1.5px solid #d8dee8;
    border-radius: 999px;
    background: #f9fafb;
    color: #172033;
    font-weight: 650;
    font-size: .9rem;
    margin-top: 4px;
}

.profile-pill-icon {
    width: 27px;
    height: 27px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #e7f5f0;
}

/* ---------- SECTION TITLES ---------- */

.section-label {
    font-size: 1.45rem;
    font-weight: 750;
    color: #172033;
    margin: 22px 0 8px;
}

/* ---------- NEED BOX ---------- */

.need-header {
    padding: 12px 0 8px 0;
}

.need-title {
    font-size: 1.4rem;
    font-weight: 800;
    color: #172033;
}

.need-subtitle {
    color: #667085;
    font-size: .92rem;
    margin-top: 3px;
}

/* ---------- FIELD CARDS ---------- */

.field-card {
    border: 1px solid #e1e5ec;
    border-radius: 16px;
    padding: 15px 15px 12px;
    background: #ffffff;
    min-height: 112px;
    margin-bottom: 8px;
    box-shadow: 0 3px 10px rgba(23,32,51,.05);
}

.field-card-title {
    font-weight: 750;
    color: #172033;
    font-size: 1rem;
    margin-bottom: 5px;
}

.field-card-text {
    color: #667085;
    font-size: .79rem;
    line-height: 1.35;
}

.field-selected {
    border: 2px solid #ff5a5f;
    background: #fff7f7;
    box-shadow: 0 5px 16px rgba(255,90,95,.10);
}

/* ---------- SCHEME CARDS ---------- */

.scheme-card {
    border: 1px solid #e6e8ef;
    border-radius: 20px;
    padding: 21px 22px;
    background: #ffffff;
    box-shadow: 0 9px 25px rgba(31, 41, 55, .07);
    margin-bottom: 18px;
    min-height: 350px;
}

.scheme-top {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: flex-start;
}

.scheme-name {
    font-size: 1.12rem;
    font-weight: 750;
    line-height: 1.3;
    color: #172033;
}

.badge {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: .75rem;
    font-weight: 700;
    white-space: nowrap;
}

.education { background:#eee9ff; color:#5a3eb7; }
.agriculture { background:#e4f7eb; color:#177245; }
.business { background:#fff0dc; color:#a45a00; }
.energy { background:#fff8cf; color:#806500; }
.youth { background:#e5f3ff; color:#17649a; }
.social { background:#ffe7ee; color:#a33c5a; }
.neutral { background:#eef1f5; color:#556070; }

.scheme-desc {
    color:#4b5565;
    margin:13px 0 16px;
    line-height:1.55;
}

.scheme-section-title {
    font-weight:700;
    color:#273142;
    margin-bottom:5px;
}

.scheme-body {
    color:#596273;
    font-size:.9rem;
    line-height:1.5;
}

.why {
    padding:10px 12px;
    background:#f7f8fb;
    border-radius:12px;
    color:#4b5563;
    font-size:.88rem;
    margin-top:12px;
}

.status-likely {
    background:#e9f8ef;
    border-left:4px solid #2e9d63;
}

.status-verify {
    background:#fff7df;
    border-left:4px solid #d59b24;
}

.status-no {
    background:#fff0f0;
    border-left:4px solid #d95353;
}

.official-link {
    display:inline-block;
    margin-top:15px;
    padding:9px 14px;
    border-radius:10px;
    background:#075e54;
    color:white !important;
    text-decoration:none !important;
    font-weight:700;
    font-size:.86rem;
}

/* ---------- INPUTS ---------- */

.stTextInput input,
.stTextArea textarea,
div[data-baseweb="select"] > div,
div[data-baseweb="select"] input {
    color: #172033 !important;
    -webkit-text-fill-color: #172033 !important;
    background-color: #ffffff !important;
    border-color: #d9dee8 !important;
    color-scheme: light !important;
}

.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #7b8494 !important;
    -webkit-text-fill-color: #7b8494 !important;
    opacity: 1 !important;
}

[data-testid="stWidgetLabel"] * {
    color: #344054 !important;
}

/* ---------- TEXT AREA HERO STYLE ---------- */

div[data-testid="stTextArea"] textarea {
    border: 2px solid #d9dee8 !important;
    border-radius: 16px !important;
    padding: 16px !important;
    font-size: 1rem !important;
    min-height: 135px !important;
    box-shadow: 0 5px 18px rgba(31,41,55,.05) !important;
}

div[data-testid="stTextArea"] textarea:focus {
    border-color: #087f6d !important;
    box-shadow: 0 0 0 2px rgba(8,127,109,.10) !important;
}

/* ---------- BUTTONS ---------- */

div.stButton > button {
    border-radius: 12px !important;
    font-weight: 700 !important;
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
    background: linear-gradient(
        135deg,
        #ff5a5f,
        #ff4b55
    ) !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border: none !important;
    box-shadow: 0 7px 18px rgba(255,90,95,.20) !important;
}

div.stButton > button[kind="primary"] * {
    color: #ffffff !important;
}

/* ---------- FORCE LIGHT UI ---------- */

:root, html, body {
    color-scheme: light !important;
}

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMainViewContainer"], [data-testid="stMain"], [data-testid="stHeader"] {
    background-color: #ffffff !important;
    color: #172033 !important;
}

[data-testid="stAppViewContainer"] {
    background: linear-gradient(
        180deg,
        #f7fbf8 0%,
        #ffffff 45%,
        #f8f7ff 100%
    ) !important;
}

[data-testid="stHeader"] {
    background: #ffffff !important;
    border-bottom: 1px solid #eef0f4 !important;
}

[data-testid="stSidebar"] {
    display: none !important;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# DATA / RETRIEVER
# ============================================================

@st.cache_resource
def get_retriever():
    return SchemeRetriever("data/schemes.json")


retriever = get_retriever()


# ============================================================
# LOGO / BRANDING HEADER
# ============================================================

st.markdown("""
<div class="brand-header">
    <div class="brand-logo">S</div>
    <div class="brand-title-group">
        <h1>SchemeSaathi</h1>
        <div class="sub-heading">PUNJAB GOVERNMENT SCHEME FINDER</div>
        <div class="brand-tagline">Find the government support you need in simple words.</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# PROFILE SECTION
# ============================================================

st.markdown("""
<div class="profile-box">
    <div class="profile-title">👤 Your Profile</div>
    <div class="profile-subtitle">
        Add a few basic details so we can personalize your results and check eligibility criteria.
    </div>
</div>
""", unsafe_allow_html=True)

p1, p2, p3 = st.columns([1, 1.5, 1.5])

with p1:
    age_raw = st.text_input(
        "Age *",
        placeholder="e.g. 24",
        max_chars=3,
    )

with p2:
    district = st.selectbox(
        "District *",
        ["Select your district"] + PUNJAB_DISTRICTS,
    )

with p3:
    occupation = st.selectbox(
        "Occupation *",
        [
            "Not specified",
            "Student",
            "Farmer",
            "Business owner",
            "Self-employed",
            "Employed",
            "Unemployed",
            "Other",
        ],
    )


# Parse age
age = None
if age_raw.strip().isdigit():
    parsed_age = int(age_raw.strip())
    if 1 <= parsed_age <= 100:
        age = parsed_age


# Profile pill display
profile_ready = (
    age is not None
    and district != "Select your district"
    and occupation != "Not specified"
)

if profile_ready:
    st.markdown(
        f"""
        <div class="profile-pill">
            <span class="profile-pill-icon">👤</span>
            <span>
                {int(age)} years&nbsp;&nbsp;·&nbsp;&nbsp;
                {html.escape(district)}&nbsp;&nbsp;·&nbsp;&nbsp;
                {html.escape(occupation)}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.caption("Complete your profile above to personalize eligibility guidance.")


# ============================================================
# NEED SECTION
# ============================================================

st.markdown("""
<div class="need-header">
    <div class="need-title">💬 What do you need help with?</div>
    <div class="need-subtitle">
        Describe your situation in your own words. You don't need to know official terminology or specific scheme names.
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# CATEGORY SHORTCUTS
# ============================================================

field_options = [
    (
        "🎓",
        "Education",
        "Scholarships, fees, laptops & student support",
        "Education",
    ),
    (
        "🌾",
        "Agriculture",
        "Farming, tractors, Kissan Card & subsidies",
        "Agriculture",
    ),
    (
        "💼",
        "Business",
        "Business loans, financing & entrepreneurship",
        "Business",
    ),
    (
        "☀️",
        "Energy",
        "Solar panels & electricity support",
        "Energy",
    ),
    (
        "🤝",
        "Social Welfare",
        "Financial assistance & welfare support",
        "Social Welfare",
    ),
    (
        "🐄",
        "Livestock",
        "Cattle, dairy & livestock support",
        "Livestock",
    ),
]


if "selected_field" not in st.session_state:
    st.session_state.selected_field = None


st.caption("Or choose a field (optional):")

for row_start in range(0, len(field_options), 3):
    cols = st.columns(3)
    for col, (icon, title, desc, category) in zip(
        cols,
        field_options[row_start:row_start + 3],
    ):
        with col:
            selected = (st.session_state.selected_field == category)
            card_class = (
                "field-card field-selected"
                if selected
                else "field-card"
            )

            st.markdown(
                f"""
                <div class="{card_class}">
                    <div class="field-card-title">
                        {icon} {title}
                    </div>
                    <div class="field-card-text">
                        {desc}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                "Selected ✓" if selected else "Choose",
                key=f"field_{category}",
                use_container_width=True,
            ):
                st.session_state.selected_field = (
                    None if selected else category
                )
                st.rerun()


selected_category = st.session_state.selected_field

if selected_category:
    st.caption(
        f"Selected field: **{selected_category}** · "
        "You can still describe your need in your own words."
    )
else:
    st.caption("No field selected — AI will infer the field directly from your request.")


# ============================================================
# MAIN NEED INPUT
# ============================================================

query = st.text_area(
    "What do you need?",
    height=140,
    placeholder=(
        "Example: I need financial support for my farm...\n\n"
        "Tell us your problem naturally."
    ),
    label_visibility="collapsed",
)


# ============================================================
# ACTION BUTTONS
# ============================================================

b1, b2 = st.columns([1.15, 1])

with b1:
    find = st.button(
        "🔎 Find schemes for me",
        type="primary",
        use_container_width=True,
    )

with b2:
    browse = st.button(
        "📋 Browse all schemes",
        use_container_width=True,
    )


# ============================================================
# SEARCH / BROWSE EXECUTION
# ============================================================

if find or browse:

    if find:
        missing = []

        if age is None:
            missing.append("Age")

        if district == "Select your district":
            missing.append("District")

        if occupation == "Not specified":
            missing.append("Occupation")

        if missing:
            st.error(
                "Please complete the required profile field(s): "
                + ", ".join(missing)
                + "."
            )
            st.stop()

        # Input validation for garbage/numeric-only queries
        query_valid, query_error = valid_need_query(query)
        if not query_valid:
            st.error(query_error)
            st.stop()

    # --------------------------------------------------------
    # Build user profile
    # --------------------------------------------------------
    profile_district = "" if district == "Select your district" else district

    profile = build_profile_from_text(
        query=query,
        age=age,
        district=profile_district,
        occupation=occupation,
        student=False,
        farmer=False,
        business_owner=False,
        income=None,
        marks=None,
    )

    # --------------------------------------------------------
    # Browse
    # --------------------------------------------------------
    if browse:
        results = retriever.browse(
            category=None,
            top_k=100,
        )
        explanation = None

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------
    else:
        inferred_category = infer_category_from_query(
            query,
            {},
        )

        active_category = (
            selected_category
            or inferred_category
        )

        retrieval_query = query.strip()

        results = retriever.search(
            retrieval_query,
            top_k=5,
            category=active_category,
        )

        if not is_service_query(query):
            results = [
                (item, score)
                for item, score in results
                if item.get("name") != "Maryam Ki Dastak"
            ]

        explanation = explain_results(
            query.strip(),
            profile,
            results,
        )

    # ========================================================
    # NO RESULTS
    # ========================================================
    if not results:
        if find and is_service_query(query):
            st.info(
                "This sounds like a Punjab government service request "
                "rather than a financial/support scheme. You can use "
                "Maryam Ki Dastak to find the relevant service."
            )
            st.markdown(
                """
                <a class="official-link"
                   href="https://dastak.punjab.gov.pk/citizen/services"
                   target="_blank">
                   🔗 Open official Dastak services
                </a>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.warning(
                "No strong match was found in the current dataset. "
                "Try describing your need in a little more detail."
            )

    # ========================================================
    # DISPLAY RESULTS
    # ========================================================
    else:
        st.markdown(
            '<div class="section-label">🎯 Schemes that may help you</div>',
            unsafe_allow_html=True,
        )

        if explanation:
            st.info(explanation)

        if find:
            inferred = infer_category_from_query(
                query,
                profile,
            )
            if inferred:
                st.caption(
                    f"We detected your main need as "
                    f"**{inferred}** and prioritized relevant schemes."
                )

        st.caption(
            f"Showing {len(results)} result(s). "
            "These are preliminary matches, not official eligibility decisions."
        )

        # Render Scheme Cards (2 per row)
        for start in range(0, len(results), 2):
            cols = st.columns(2)
            for offset, col in enumerate(cols):
                idx = start + offset
                if idx >= len(results):
                    continue

                item, score = results[idx]

                assessment = assess_scheme(
                    item,
                    profile,
                )

                cat = item.get("category", "Other")
                cat_class = {
                    "Education": "education",
                    "Agriculture": "agriculture",
                    "Business": "business",
                    "Energy": "energy",
                    "Youth": "youth",
                    "Social Welfare": "social",
                    "Livestock": "agriculture",
                }.get(cat, "neutral")

                status_class = {
                    "likely": "status-likely",
                    "needs_verification": "status-verify",
                    "not_eligible": "status-no",
                }[assessment["status"]]

                status_text = {
                    "likely": "🟢 Likely match",
                    "needs_verification": "🟡 Verify requirements",
                    "not_eligible": "🔴 Basic requirement mismatch",
                }[assessment["status"]]

                name = html.escape(item["name"])
                desc = html.escape(item.get("description", ""))
                benefits = html.escape(item.get("benefits", ""))
                eligibility_text = "<br>".join(
                    "• " + html.escape(x)
                    for x in item.get("eligibility", [])
                )
                why = html.escape(" ".join(assessment.get("reasons", [])))
                url = html.escape(item.get("official_url", ""), quote=True)

                card_html = f"""
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

                    <div class="why {status_class}">
                        <strong>{status_text}</strong><br>
                        {why}
                    </div>

                    <a class="official-link" href="{url}" target="_blank">
                        🔗 Official government source
                    </a>
                </div>
                """

                with col:
                    st.markdown(card_html, unsafe_allow_html=True)


# ============================================================
# COMPACT FOOTER / HOW IT WORKS
# ============================================================

st.markdown("<br><hr style='border: 0; border-top: 1px solid #e3e7ee;'><br>", unsafe_allow_html=True)

with st.expander("ℹ️ How SchemeSaathi works"):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**1. Tell us your need**\nWrite naturally — no official keywords or code required.")
    with c2:
        st.markdown("**2. We find matches**\nSemantic AI search checks the official scheme knowledge base.")
    with c3:
        st.markdown("**3. Verify & apply**\nCheck preliminary eligibility rules and proceed to official government portals.")
