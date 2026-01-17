"""
Web scraper: fetches a short description for each politician from Wikipedia,
summarizes it to 1-2 sentences using AI (OpenAI or Gemini), and stores it
in Firestore as politician_description.

Setup:
1. Install dependencies: pip install firebase-admin
2. Optional (for AI): pip install openai OR pip install google-generativeai
3. Set environment variable:
   - For OpenAI: export OPENAI_API_KEY="your-key"
   - For Gemini: export GEMINI_API_KEY="your-key" (or GOOGLE_API_KEY)
4. Run: python scraper.py

If no AI API key is set, it will use a simple heuristic (first 1-2 sentences).
"""
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
import re
import time
from urllib.parse import quote
from urllib.request import urlopen, Request

# Optional AI imports
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# Paths
script_dir = os.path.dirname(os.path.abspath(__file__))
service_account_path = os.path.join(script_dir, "serviceAccountKey.json")

# Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred)
db = firestore.client()

WIKI_API = "https://en.wikipedia.org/w/api.php"


def _fetch_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "GovPropsScraper/1.0"})
    with urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def get_wikipedia_extract(name: str) -> str:
    """Get the intro extract from the best-matching Wikipedia article."""
    if not (name or name.strip()):
        return ""
    name = name.strip()

    # 1) Search for the best matching page
    search_url = (
        f"{WIKI_API}?action=query&list=search&srsearch={quote(name)}"
        "&srlimit=1&format=json"
    )
    try:
        data = _fetch_json(search_url)
        hits = data.get("query", {}).get("search", [])
        if not hits:
            # Fallback: try exact title (e.g. "Joe Biden" -> "Joe_Biden")
            title = name.replace(" ", "_")
        else:
            title = hits[0].get("title", name.replace(" ", "_"))
    except Exception as e:
        print(f"  [search error for {name!r}: {e}]")
        return ""

    # 2) Get extract (intro section) for that page
    extract_url = (
        f"{WIKI_API}?action=query&prop=extracts&exintro&explaintext"
        f"&redirects=1&format=json&titles={quote(title)}"
    )
    try:
        data = _fetch_json(extract_url)
        pages = data.get("query", {}).get("pages", {})
        # Page id can be -1 if not found
        for pid, p in pages.items():
            if pid == "-1":
                return ""
            text = (p or {}).get("extract", "")
            if not text:
                return ""
            # Clean whitespace
            text = re.sub(r"\s+", " ", text).strip()
            return text
    except Exception as e:
        print(f"  [extract error for {name!r}: {e}]")
        return ""


def summarize_with_ai(text: str) -> str:
    """
    Summarize text to 1-2 sentences using AI (OpenAI or Gemini).
    Falls back to heuristic if no AI available.
    """
    if not text or len(text) < 20:
        return ""

    # Try OpenAI first
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key and HAS_OPENAI:
        try:
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": f"Summarize the following in exactly 1-2 short sentences (max 200 characters):\n\n{text[:2000]}"
                    }
                ],
                max_tokens=100,
                temperature=0.3
            )
            result = response.choices[0].message.content.strip()
            if result:
                return result
        except Exception as e:
            print(f"  [OpenAI error: {e}]")

    # Try Gemini
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gemini_key and HAS_GEMINI:
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"Summarize in exactly 1-2 short sentences (max 200 characters):\n\n{text[:2000]}"
            response = model.generate_content(prompt)
            result = response.text.strip()
            if result:
                return result
        except Exception as e:
            print(f"  [Gemini error: {e}]")

    # Fallback: extract first 1-2 sentences heuristically
    sentences = re.findall(r'[^.!?]+[.!?]', text)
    if len(sentences) >= 2:
        return (sentences[0] + " " + sentences[1]).strip()
    elif len(sentences) == 1:
        return sentences[0].strip()
    else:
        # No sentence endings found, take first 200 chars
        return text[:200].strip() + ("..." if len(text) > 200 else "")


def run():
    coll = db.collection("Politicians")
    docs = list(coll.stream())
    print(f"Found {len(docs)} politicians in Firestore.")

    for i, doc in enumerate(docs):
        data = doc.to_dict() or {}
        name = data.get("Name") or ""
        doc_id = doc.id

        if not name:
            print(f"[{i+1}/{len(docs)}] Skip (no Name): {doc_id}")
            continue

        # Optional: skip if already has a description
        # if data.get("politician_description"):
        #     print(f"[{i+1}/{len(docs)}] Skip (has description): {name}")
        #     continue

        print(f"[{i+1}/{len(docs)}] {name} ... ", end="", flush=True)
        extract = get_wikipedia_extract(name)
        if not extract:
            print("(no Wikipedia extract)")
            continue

        desc = summarize_with_ai(extract)
        if not desc:
            print("(summarization failed)")
            continue

        try:
            doc.reference.update({"politician_description": desc})
            print(f"ok ({len(desc)} chars)")
        except Exception as e:
            print(f" Firestore error: {e}")

        # Be nice to Wikipedia and AI APIs
        time.sleep(0.6)


if __name__ == "__main__":
    run()
