import re

def _contains(text, words):
    text = (text or "").lower()
    return any(w in text for w in words)

def build_profile_from_text(
    query,
    age,
    district,
    occupation,
    student,
    farmer,
    business_owner,
    income,
    marks,
):
    q = (query or "").lower()

    # Fill only what can reasonably be inferred from the user's own text.
    if occupation == "Not specified":
        if _contains(q, ["student", "university", "college", "degree", "scholarship", "laptop"]):
            occupation = "Student"
        elif _contains(q, ["farmer", "kisan", "kissan", "crop", "farm", "tractor", "agriculture"]):
            occupation = "Farmer"
        elif _contains(q, ["business", "shop", "entrepreneur", "startup", "enterprise", "loan"]):
            occupation = "Business owner"

    student = student or occupation == "Student" or _contains(
        q, ["student", "university", "college", "scholarship", "semester"]
    )
    farmer = farmer or occupation == "Farmer" or _contains(
        q, ["farmer", "kisan", "kissan", "crop", "farm", "tractor", "agriculture"]
    )
    business_owner = business_owner or occupation in ["Business owner", "Self-employed"] or _contains(
        q, ["business", "shop", "entrepreneur", "startup", "enterprise"]
    )

    # Extract an age only when the text clearly uses an age pattern.
    if age is None:
        match = re.search(r"\b(?:i am|i'm|age is|aged)\s*(\d{1,2})\b", q)
        if match:
            age = int(match.group(1))

    return {
        "age": age,
        "district": (district or "").strip(),
        "occupation": occupation,
        "student": student,
        "farmer": farmer,
        "business_owner": business_owner,
        "income": income,
        "marks": marks,
    }


def infer_category_from_query(query, profile=None):
    """Infer a strong user-intent category so semantic retrieval does not surface unrelated schemes."""
    q = (query or "").lower()
    profile = profile or {}

    # Need/goal terms get priority over generic profile words.
    intents = [
        ("Education", ["university fee", "university fees", "tuition", "fee", "fees", "scholarship", "stipend", "education", "college fee", "study", "laptop"]),
        ("Agriculture", ["tractor", "kisan", "kissan", "farmer", "crop", "farm", "agriculture", "irrigation", "fertilizer", "machinery"]),
        ("Business", ["business", "shop", "startup", "entrepreneur", "enterprise", "sme", "business loan", "business finance"]),
        ("Energy", ["solar", "electricity bill", "electricity", "solar panel"]),
        ("Livestock", ["livestock", "cattle", "dairy", "animal farming"]),
        ("Social Welfare", ["zakat", "marriage assistance", "rashan", "financial assistance for poor"]),
    ]

    # Explicit need words beat a generic occupation.
    for category, terms in intents:
        if any(term in q for term in terms):
            return category

    if profile.get("student"):
        return "Education"
    if profile.get("farmer"):
        return "Agriculture"
    if profile.get("business_owner") or profile.get("occupation") == "Self-employed":
        return "Business"
    return None


def is_service_query(query):
    """Return True only when the user is clearly asking for a government service/document/license."""
    q = (query or "").lower()
    service_terms = [
        "driving license", "driving licence", "learner license", "learner licence",
        "domicile", "birth certificate", "death certificate", "marriage certificate",
        "divorce certificate", "fard", "registry copy", "mutation", "challan",
        "police verification", "character certificate", "fir copy", "traffic challan",
        "vehicle registration", "token tax", "property tax", "food business license",
        "food business licence", "college admission", "government service",
        "government services", "dastak", "doorstep service", "license renewal",
        "licence renewal", "duplicate license", "duplicate licence",
    ]
    return any(term in q for term in service_terms)


def assess_scheme(scheme, profile):
    rules = scheme.get("rules", {})
    reasons = []

    if profile["age"] is not None:
        if rules.get("min_age") is not None and profile["age"] < rules["min_age"]:
            return {"status": "not_eligible", "reasons": [f"Minimum age is {rules['min_age']} years."]}
        if rules.get("max_age") is not None and profile["age"] > rules["max_age"]:
            return {"status": "not_eligible", "reasons": [f"Maximum age is {rules['max_age']} years."]}

    if rules.get("student_required"):
        if not profile["student"]:
            return {"status": "not_eligible", "reasons": ["Student status is required."]}
        reasons.append("You indicated that you are a student.")

    if rules.get("farmer_required"):
        if not profile["farmer"]:
            return {"status": "not_eligible", "reasons": ["Farmer status is required."]}
        reasons.append("You indicated that you are a farmer.")

    if rules.get("business_required"):
        if not profile["business_owner"]:
            return {"status": "not_eligible", "reasons": ["The scheme is intended for entrepreneurs/business owners."]}
        reasons.append("You indicated that you own or plan to start a business.")

    if rules.get("min_income") is not None and profile["income"] is not None:
        if profile["income"] >= rules["min_income"]:
            return {"status": "not_eligible", "reasons": [f"The stored criterion requires family income below Rs. {rules['min_income']:,} per month."]}

    if rules.get("max_income") is not None and profile["income"] is not None:
        if profile["income"] >= rules["max_income"]:
            return {"status": "not_eligible", "reasons": [f"The stored criterion requires family income below Rs. {rules['max_income']:,} per month."]}
        reasons.append("Your income information is within the stored threshold.")

    if rules.get("min_marks") is not None and profile["marks"] is not None:
        if profile["marks"] < rules["min_marks"]:
            return {"status": "not_eligible", "reasons": [f"Minimum marks stored for this scheme are {rules['min_marks']}%."]}
        reasons.append("Your marks meet the stored minimum.")

    if rules.get("districts") and profile["district"]:
        allowed = [x.lower() for x in rules["districts"]]
        if profile["district"].lower() not in allowed:
            return {"status": "not_eligible", "reasons": ["Your district is outside the stored project area."]}

    # If important rules exist but the user didn't provide the needed facts,
    # don't falsely call them eligible.
    missing = []
    if rules.get("income_required") and profile["income"] is None:
        missing.append("family income")
    if rules.get("marks_required") and profile["marks"] is None:
        missing.append("academic marks")
    if rules.get("district_required") and not profile["district"]:
        missing.append("district")

    if missing:
        return {
            "status": "needs_verification",
            "reasons": ["We need " + ", ".join(missing) + " to assess that criterion."]
        }

    if not rules:
        return {
            "status": "needs_verification",
            "reasons": ["The MVP does not encode every official criterion for this scheme."]
        }

    return {
        "status": "likely",
        "reasons": reasons or ["Your provided information matches the basic rules encoded in this MVP."]
    }
