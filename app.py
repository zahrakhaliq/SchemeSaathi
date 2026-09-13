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
    page_title="SchemeSaathi - AI-Powered Government Scheme Discovery",
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

    if not any(char.isalpha() for char in text):
        return False, "Please describe your need using words, not only numbers or symbols."

    letters = [c for c in text if c.isalpha()]

    if len(letters) < 3:
        return False, "Please provide a little more detail about what you need."

    return True, ""


# ============================================================
# HIGH CONTRAST THEME (SLIDE DECK PALETTE + HIGH VISIBILITY)
# ============================================================

st.markdown("""
<style>

/* Force light root for consistent rendering */
:root {
    color-scheme: light !important;
}

html, body, .stApp {
    background-color: #f4f6f5 !important;
    color: #0d2818 !important;
}

/* ---------- BRANDING / LOGO HEADER ---------- */

.brand-banner {
    background: linear-gradient(135deg, #0d2818 0%, #174229 100%);
    padding: 28px 32px;
    border-radius: 18px;
    color: #ffffff;
    box-shadow: 0 8px 24px rgba(13, 40, 24, 0.2);
    margin-bottom: 24px;
    border: 2px solid #e5a93c;
}

.brand-header {
    display: flex;
    align-items: center;
    gap: 18px;
}

.brand-logo {
    width: 60px;
    height: 60px;
    border-radius: 16px;
    background: #e5a93c;
    color: #0d2818;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2.2rem;
    font-weight: 900;
    box-shadow: 0 4px 15px rgba(229, 169, 60, 0.4);
}

.brand-title-group h1 {
    margin: 0;
    font-size: 2.3rem;
    font-weight: 800;
    color: #ffffff !important;
    line-height: 1.1;
}

.brand-title-group h1 span.highlight {
    color: #e5a93c !important;
}

.brand-title-group .sub-heading {
    margin: 4px 0 0 0;
    color: #e5a93c;
    font-size: 0.85rem;
    font-weight: 800;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}

.brand-tagline {
    margin-top: 8px;
    color: #e8f0eb;
    font-size: 1.05rem;
    font-weight: 500;
}

/* ---------- PROFILE BOX ---------- */

.profile-box {
    background: #ffffff;
    border: 2px solid #d4dfd8;
    border-radius: 16px;
    padding: 20px 22px;
    margin: 8px 0 20px 0;
    box-shadow: 0 4px 14px rgba(13, 40, 24, 0.05);
}

.profile-title {
    font-size: 1.15rem;
    font-weight: 800;
    color: #0d2818;
    margin-bottom: 4px;
}

.profile-subtitle {
    color: #3d5245;
    font-size: .92rem;
    margin-bottom: 14px;
}

/* Profile pill */

.profile-pill {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 8px 18px;
    border: 2px solid #e5a93c;
    border-radius: 999px;
    background: #fffdf5;
    color: #0d2818;
    font-weight: 800;
    font-size: .95rem;
    margin-top: 8px;
}

.profile-pill-icon {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #e5a93c;
    color: #0d2818;
}

/* ---------- NEED BOX ---------- */

.need-header {
    padding: 10px 0 6px 0;
}

.need-title {
    font-size: 1.4rem;
    font-weight: 800;
    color: #0d2818;
}

.need-subtitle {
    color: #3d5245;
    font-size: .95rem;
    margin-top: 3px;
}

/* ---------- FIELD CARDS ---------- */

.field-card {
    border: 2px solid #d4dfd8;
    border-radius: 16px;
    padding: 16px;
    background: #ffffff;
    min-height: 110px;
    margin-bottom: 8px;
    box-shadow: 0 3px 10px rgba(13, 40, 24, 0.04);
}

.field-card-title {
    font-weight: 800;
    color: #0d2818;
    font-size: 1.05rem;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.field-card-text {
    color: #4a5d52;
    font-size: .85rem;
    line-height: 1.4;
}

.field-selected {
    border: 2px solid #e5a93c;
    background: #fffdf5;
    box-shadow: 0 6px 18px rgba(229, 169, 60, 0.2);
}

/* ---------- SCHEME CARDS ---------- */

.scheme-card {
    border: 2px solid #d4dfd8;
    border-radius: 18px;
    padding: 22px;
    background: #ffffff;
    box-shadow: 0 6px 20px rgba(13, 40, 24, 0.06);
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
    font-size: 1.2rem;
    font-weight: 800;
    line-height: 1.3;
    color: #0d2818;
}

.badge {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 999px;
    font-size: .8rem;
    font-weight: 800;
    white-space: nowrap;
}

.education { background:#fff5e5; color:#966400; }
.agriculture { background:#e8f5e9; color:#1b5e20; }
.business { background:#e0f2f1; color:#004d40; }
.energy { background:#fffde7; color:#8c6d00; }
.youth { background:#e1f5fe; color:#01579b; }
.social { background:#f3e5f5; color:#4a148c; }
.neutral { background:#eceff1; color:#37474f; }

.scheme-desc {
    color: #2c3e35;
    margin: 14px 0 16px;
    line-height: 1.55;
    font-size: 0.95rem;
}

.scheme-section-title {
    font-weight: 800;
    color: #0d2818;
    margin-bottom: 5px;
    font-size: 0.92rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.scheme-body {
    color: #2c3e35;
    font-size: .92rem;
    line-height: 1.5;
}

.why {
    padding: 12px 14px;
    border-radius: 12px;
    font-size: .9rem;
    margin-top: 14px;
    font-weight: 600;
}

.status-likely {
    background: #e8f5e9;
    border-left: 5px solid #2e7d56;
    color: #1b5e20;
}

.status-verify {
    background: #fff8e1;
    border-left: 5px solid #e5a93c;
    color: #7a5405;
}

.status-no {
    background: #ffebee;
    border-left: 5px solid #c62828;
    color: #b71c1c;
}

.official-link {
    display: inline-block;
    margin-top: 16px;
    padding: 10px 16px;
    border-radius: 10px;
    background: #0d2818;
    color: #e5a93c !important;
    text-decoration: none !important;
    font-weight: 800;
    font-size: .9rem;
}

/* ---------- EXPLICIT FORM INPUT FIXES (HIGH VISIBILITY) ---------- */

[data-testid="stWidgetLabel"] * {
    color: #0d2818 !important;
    font-weight: 800 !important;
    font-size: 0.95rem !important;
}

.stTextInput input {
    color: #0d2818 !important;
    background-color: #ffffff !important;
    border: 2px solid #a8baa9 !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}

.stTextInput input::placeholder {
    color: #617568 !important;
    opacity: 1 !important;
}

/* Text Area Override */
div[data-testid="stTextArea"] textarea {
    color: #0d2818 !important;
    background-color: #ffffff !important;
    border: 2px solid #a8baa9 !important;
    border-radius: 14px !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    padding: 16px !important;
}

div[data-testid="stTextArea"] textarea::placeholder {
    color: #617568 !important;
    opacity: 1 !important;
}

/* Select Box Overrides */
div[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border: 2px solid #a8baa9 !important;
    border-radius: 12px !important;
    color: #0d2818 !important;
}

div[data-baseweb="select"] * {
    color: #0d2818 !important;
    font-weight: 600 !important;
}

/* Expander Fix */
.stExpander {
    background: #ffffff !important;
    border: 2px solid #d4dfd8 !important;
    border-radius: 14px !important;
}

.stExpander summary * {
    color: #0d2818 !important;
    font-weight: 800 !important;
}

/* ---------- BUTTONS ---------- */

div.stButton > button {
    border-radius: 12px !important;
    font-weight: 800 !important;
    background: #ffffff !important;
    color: #0d2818 !important;
    border: 2px solid #0d2818 !important;
    padding: 12px 20px !important;
    font-size: 1rem !important;
}

div.stButton > button:hover {
    background: #0d2818 !important;
    color: #ffffff !important;
}

div.stButton > button[kind="primary"] {
    background: #e5a93c !important;
    color: #0d2818 !important;
    border: 2px solid #b88120 !important;
    box-shadow: 0 6px 18px rgba(229, 169, 60, 0.35) !important;
}

div.stButton > button[kind="primary"] * {
    color: #0d2818 !important;
    font-weight: 800 !important;
}

div.stButton > button[kind="primary"]:hover {
    background: #d4972c !important;
}

/* Hide Sidebar */
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
# BRANDING HEADER
# ============================================================

st.markdown("""
<div class="brand-banner">
    <div class="brand-header">
        <div class="brand-logo">S</div>
        <div class="brand-title-group">
            <div class="sub-heading">AI GOVERNMENT SCHEME ASSISTANT • PUNJAB</div>
            <h1>Scheme<span class="highlight">Saathi</span></h1>
            <div class="brand-tagline">Find the government support you need in your own words.</div>
        </div>
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
        Provide basic details so we can evaluate preliminary scheme eligibility criteria.
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
            <span class="profile-pill-icon">✓</span>
            <span>
                {int(age)} years old&nbsp;&nbsp;•&nbsp;&nbsp;
                {html.escape(district)}&nbsp;&nbsp;•&nbsp;&nbsp;
                {html.escape(occupation)}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.caption("Fill in your profile details above for personalized eligibility checks.")


# ============================================================
# NEED SECTION
# ============================================================

st.markdown("""
<div class="need-header">
    <div class="need-title">💬 What do you need help with?</div>
    <div class="need-subtitle">
        Describe your situation naturally. No technical or official government terms required.
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# CATEGORY SHORTCUTS
# ============================================================

field_options = [
    (
        "🌾",
        "Agriculture",
        "Farming, tractors, Kissan Card & subsidies",
        "Agriculture",
    ),
    (
        "🎓",
        "Education",
        "Scholarships, fees, laptops & student support",
        "Education",
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


st.caption("Or select a category (optional):")

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
                        <span>{icon}</span> <span>{title}</span>
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
        f"Filtered sector: **{selected_category}** · "
        "You can still describe your request in detail below."
    )
else:
    st.caption("No sector filter selected — AI will infer it from your text input.")


# ============================================================
# MAIN NEED INPUT
# ============================================================

query = st.text_area(
    "What do you need?",
    height=130,
    placeholder=(
        "Example: I need financial support to purchase solar panels for my farm..."
    ),
    label_visibility="collapsed",
)


# ============================================================
# ACTION BUTTONS
# ============================================================

b1, b2 = st.columns([1.2, 1])

with b1:
    find = st.button(
        "🔎 Find Schemes For Me",
        type="primary",
        use_container_width=True,
    )

with b2:
    browse = st.button(
        "📋 Browse All Schemes",
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
                "Please complete the missing profile field(s): "
                + ", ".join(missing)
                + "."
            )
            st.stop()

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
                "This request appears to be for a general civic service "
                "rather than a support scheme. You can check Maryam Ki Dastak for official civic services."
            )
            st.markdown(
                """
                <a class="official-link"
                   href="https://dastak.punjab.gov.pk/citizen/services"
                   target="_blank">
                   🔗 Open Official Dastak Portal
                </a>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.warning(
                "No matching schemes were found in our database. "
                "Try clarifying or elaborating on your situation."
            )

    # ========================================================
    # DISPLAY RESULTS
    # ========================================================
    else:
        st.markdown(
            '<div class="need-title" style="margin-top:20px;">🎯 Relevant Government Schemes</div>',
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
                    f"Identified core category as **{inferred}**."
                )

        st.caption(
            f"Displaying {len(results)} matching result(s)."
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
                    "likely": "🟢 Likely Match",
                    "needs_verification": "🟡 Verify Eligibility",
                    "not_eligible": "🔴 Basic Requirement Mismatch",
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

                    <div class="scheme-section-title">Benefits</div>
                    <div class="scheme-body">{benefits}</div>

                    <div style="height:12px"></div>

                    <div class="scheme-section-title">Eligibility Criteria</div>
                    <div class="scheme-body">{eligibility_text}</div>

                    <div class="why {status_class}">
                        <strong>{status_text}</strong><br>
                        {why}
                    </div>

                    <a class="official-link" href="{url}" target="_blank">
                        🔗 Official Government Link
                    </a>
                </div>
                """

                with col:
                    st.markdown(card_html, unsafe_allow_html=True)


# ============================================================
# FOOTER / HOW IT WORKS
# ============================================================

st.markdown("<br><hr style='border: 0; border-top: 2px solid #d4dfd8;'><br>", unsafe_allow_html=True)

with st.expander("ℹ️ How SchemeSaathi Works"):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**1. Citizen Input**\nEnter your request naturally in simple terms.")
    with c2:
        st.markdown("**2. RAG & Semantic Match**\nMatches query against verified government databases.")
    with c3:
        st.markdown("**3. Official Direct Access**\nReview basic requirements and visit direct official links.")
