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
    page_title="Punjab Scheme Finder",
    page_icon="🇵🇰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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

/* ---------- HERO ---------- */

.hero {
    padding: 30px 32px;
    border-radius: 24px;
    background: linear-gradient(
        135deg,
        #075e54 0%,
        #087f6d 48%,
        #6b4fd3 100%
    );
    color: white;
    box-shadow: 0 14px 35px rgba(20, 55, 70, .14);
    margin-bottom: 24px;
}

.hero h1 {
    margin: 0 0 8px 0;
    font-size: 2.35rem;
}

.hero p {
    margin: 0;
    opacity: .94;
    font-size: 1.02rem;
}

/* ---------- PROFILE ---------- */

.profile-box {
    background: #ffffff;
    border: 1px solid #e3e7ee;
    border-radius: 20px;
    padding: 20px 22px;
    margin: 8px 0 22px 0;
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

/* ---------- MINI HOW-IT-WORK CARDS ---------- */

.mini-card {
    padding: 17px 18px;
    border-radius: 18px;
    background: rgba(255,255,255,.92);
    border: 1px solid #e7e8ef;
    box-shadow: 0 7px 20px rgba(35, 45, 60, .06);
    min-height: 108px;
}

.mini-icon {
    font-size: 1.55rem;
}

.mini-title {
    font-weight: 700;
    margin-top: 6px;
}

.mini-text {
    color: #667085;
    font-size: .88rem;
    margin-top: 3px;
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
    padding: 2px 0 8px 0;
}

.need-title {
    font-size: 1.65rem;
    font-weight: 800;
    color: #172033;
}

.need-subtitle {
    color: #667085;
    font-size: .95rem;
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

.education {
    background:#eee9ff;
    color:#5a3eb7;
}

.agriculture {
    background:#e4f7eb;
    color:#177245;
}

.business {
    background:#fff0dc;
    color:#a45a00;
}

.energy {
    background:#fff8cf;
    color:#806500;
}

.youth {
    background:#e5f3ff;
    color:#17649a;
}

.social {
    background:#ffe7ee;
    color:#a33c5a;
}

.neutral {
    background:#eef1f5;
    color:#556070;
}

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

:root,
html,
body {
    color-scheme: light !important;
}

html,
body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMainViewContainer"],
[data-testid="stMain"],
[data-testid="stHeader"] {
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

/* Hide sidebar completely from the user-facing layout */
[data-testid="stSidebar"] {
    display: none !important;
}

@media (prefers-color-scheme: dark) {

    html,
    body,
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stHeader"] {
        background-color: #ffffff !important;
        color: #172033 !important;
    }

    .stTextInput input,
    .stTextArea textarea,
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #172033 !important;
        -webkit-text-fill-color: #172033 !important;
    }
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
# HERO
# ============================================================

st.markdown("""
<div class="hero">
    <h1>🇵🇰 Punjab Government Scheme Finder</h1>
    <p>
        Tell us what you need in simple words.
        We’ll help you discover relevant Punjab Government schemes.
    </p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# PROFILE SECTION
# ============================================================

st.markdown("""
<div class="profile-box">
    <div class="profile-title">👤 Your profile</div>
    <div class="profile-subtitle">
        Add a few basic details so we can personalize your results.
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
    district = st.text_input(
        "District *",
        placeholder="e.g. Lahore",
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


# Profile pill
profile_ready = (
    age is not None
    and bool(district.strip())
    and occupation != "Not specified"
)

if profile_ready:

    st.markdown(
        f"""
        <div class="profile-pill">
            <span class="profile-pill-icon">👤</span>
            <span>
                {int(age)} years&nbsp;&nbsp;·&nbsp;&nbsp;
                {html.escape(district.strip())}&nbsp;&nbsp;·&nbsp;&nbsp;
                {html.escape(occupation)}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

else:

    st.caption(
        "Complete your profile above to personalize eligibility guidance."
    )


# ============================================================
# HOW IT WORKS
# ============================================================

st.markdown(
    '<div class="section-label">✨ How SchemeSaathi works</div>',
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)

for col, icon, title, text in [
    (
        c1,
        "💬",
        "Tell us your need",
        "Write naturally — no special keywords required.",
    ),
    (
        c2,
        "🧠",
        "We find matches",
        "Semantic search looks through the scheme knowledge base.",
    ),
    (
        c3,
        "🔗",
        "Verify & apply",
        "Open the official Government of Punjab source.",
    ),
]:

    with col:

        st.markdown(
            f"""
            <div class="mini-card">
                <div class="mini-icon">{icon}</div>
                <div class="mini-title">{title}</div>
                <div class="mini-text">{text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# NEED SECTION
# ============================================================

st.markdown("""
<div class="need-header">
    <div class="need-title">💬 What do you need help with?</div>
    <div class="need-subtitle">
        Describe your situation in your own words. You don't need to know
        the name or category of a government scheme.
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


st.caption("Optional: choose a field, or let AI understand it from your need.")

for row_start in range(0, len(field_options), 3):

    cols = st.columns(3)

    for col, (icon, title, desc, category) in zip(
        cols,
        field_options[row_start:row_start + 3],
    ):

        with col:

            selected = (
                st.session_state.selected_field == category
            )

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

    st.caption(
        "No field selected — AI will understand the field from your need."
    )


# ============================================================
# MAIN NEED INPUT
# ============================================================

query = st.text_area(
    "What do you need?",
    height=150,
    placeholder=(
        "Example: I need financial support for my farm.\n\n"
        "You can explain your situation naturally — no special keywords required."
    ),
    label_visibility="visible",
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
# SEARCH / BROWSE
# ============================================================

if find or browse:

    if find:

        missing = []

        if age is None:
            missing.append("Age")

        if not district.strip():
            missing.append("District")

        if occupation == "Not specified":
            missing.append("Occupation")

        if not query.strip():
            missing.append("What you need")

        if missing:

            st.error(
                "Please enter the required field(s): "
                + ", ".join(missing)
                + "."
            )

            st.stop()


    # --------------------------------------------------------
    # Build user profile
    # --------------------------------------------------------

    student = False
    farmer = False
    business_owner = False
    income = None
    marks = None

    profile = build_profile_from_text(
        query=query,
        age=age,
        district=district,
        occupation=occupation,
        student=student,
        farmer=farmer,
        business_owner=business_owner,
        income=income,
        marks=marks,
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

        # IMPORTANT:
        # The user's stated need remains the primary retrieval signal.
        # Profile facts are mainly used for preliminary eligibility.

        inferred_category = infer_category_from_query(
            query,
            {},
        )

        # Optional category constraint.
        # If user selected a field, use it.
        # Otherwise AI infers the field from the need.

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

        # Dastak is only for explicit service/document/license requests.

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
    # RESULTS
    # ========================================================

    else:

        st.markdown(
            '<div class="section-label">🎯 Recommended schemes</div>',
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
                    f"**{inferred}** and prioritized schemes in that area."
                )

        st.caption(
            f"Showing {len(results)} result(s). "
            "These are preliminary matches, not official eligibility decisions."
        )


        # ----------------------------------------------------
        # Scheme cards
        # ----------------------------------------------------

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

                cat = item.get(
                    "category",
                    "Other",
                )

                cat_class = {
                    "Education": "education",
                    "Agriculture": "agriculture",
                    "Business": "business",
                    "Energy": "energy",
                    "Youth": "youth",
                    "Social Welfare": "social",
                    "Livestock": "agriculture",
                }.get(
                    cat,
                    "neutral",
                )

                status_class = {
                    "likely": "status-likely",
                    "needs_verification": "status-verify",
                    "not_eligible": "status-no",
                }[
                    assessment["status"]
                ]

                status_text = {
                    "likely": "🟢 Likely match",
                    "needs_verification": "🟡 Needs verification",
                    "not_eligible": "🔴 Basic requirement mismatch",
                }[
                    assessment["status"]
                ]

                name = html.escape(
                    item["name"]
                )

                desc = html.escape(
                    item.get("description", "")
                )

                benefits = html.escape(
                    item.get("benefits", "")
                )

                eligibility_text = "<br>".join(
                    "• " + html.escape(x)
                    for x in item.get(
                        "eligibility",
                        [],
                    )
                )

                why = html.escape(
                    " ".join(
                        assessment.get(
                            "reasons",
                            [],
                        )
                    )
                )

                url = html.escape(
                    item.get(
                        "official_url",
                        "",
                    ),
                    quote=True,
                )

                card = f"""
                <div class="scheme-card">

                    <div class="scheme-top">

                        <div class="scheme-name">
                            {name}
                        </div>

                        <span class="badge {cat_class}">
                            {html.escape(cat)}
                        </span>

                    </div>

                    <div class="scheme-desc">
                        {desc}
                    </div>

                    <div class="scheme-section-title">
                        What you get
                    </div>

                    <div class="scheme-body">
                        {benefits}
                    </div>

                    <div style="height:12px"></div>

                    <div class="scheme-section-title">
                        Who it is for
                    </div>

                    <div class="scheme-body">
                        {eligibility_text}
                    </div>

                    <div class="why {status_class}">
                        <b>{status_text}</b><br>
                        {why}
                    </div>

                    <a
                        class="official-link"
                        href="{url}"
                        target="_blank"
                    >
                        🔗 Open official source
                    </a>

                </div>
                """

                with col:

                    st.markdown(
                        card,
                        unsafe_allow_html=True,
                    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "This is an information and discovery assistant. "
    "Matches and eligibility labels are preliminary. "
    "Always verify the latest eligibility, deadlines and application "
    "instructions on the linked official Government of Punjab source."
)
