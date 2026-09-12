import os
import json
import urllib.request
import urllib.error

def explain_results(query, profile, results):
    if not results:
        return None

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "I found these schemes based on the meaning of your request. Open the official source on each card to verify the latest rules."

    # Keep the LLM grounded: it only receives retrieved scheme records.
    compact = []
    for item, score in results[:5]:
        compact.append({
            "name": item["name"],
            "category": item["category"],
            "description": item["description"],
            "benefits": item["benefits"],
            "eligibility": item["eligibility"],
            "official_url": item["official_url"],
        })

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a concise public-service assistant. "
                    "Use ONLY the retrieved scheme data provided by the application. "
                    "Do not invent eligibility, deadlines, amounts, URLs, or scheme names. "
                    "Do not say a person is officially eligible. "
                    "Return 2-4 short sentences explaining which results seem most relevant and why. "
                    "Tell the user to verify final eligibility on the official source."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "user_request": query,
                    "user_profile": profile,
                    "retrieved_schemes": compact,
                }, ensure_ascii=False),
            },
        ],
        "temperature": 0.1,
        "max_tokens": 250,
    }

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return "I found these schemes from the official-source dataset. Review the cards below and verify the latest requirements on the linked government source."
