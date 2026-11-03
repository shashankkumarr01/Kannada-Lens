
import os
import re
import sqlite3
import json
import requests

from pathlib import Path
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY")

# -----------------------------------------
# 1. DATABASE CONFIGURATION
# -----------------------------------------

DB_FILE = Path(__file__).parent / "data" / "alar.db"


def lookup_alar(word):
    """Find a Kannada word using SQLite."""

    if not DB_FILE.exists():
        print("Alar SQLite database not found:", DB_FILE)
        return None

    try:
        with sqlite3.connect(
            f"file:{DB_FILE.as_posix()}?mode=ro",
            uri=True,
            timeout=3
        ) as connection:

            row = connection.execute(
                "SELECT defs, phone FROM alar WHERE entry = ?",
                (word.strip(),)
            ).fetchone()

        if not row:
            return None

        definitions = json.loads(row[0] or "[]")

        meanings = [
            item.get("entry", "").strip()
            for item in definitions[:3]
            if isinstance(item, dict)
            and item.get("entry", "").strip()
        ]

        if not meanings:
            return None

        return {
            "english": "; ".join(meanings),
            "meaning": "Definition from Alar Kannada-English Dictionary.",
            "pronunciation": row[1] or "Not available",
            "example": "",
            "example_pronunciation": "",
            "example_meaning": "No verified example available."
        }

    except (sqlite3.Error, json.JSONDecodeError) as error:
        print("Alar SQLite lookup error:", error)
        return None


# -----------------------------------------
# 2. LOCAL KANNADA DICTIONARY
# -----------------------------------------

kannada_words = {
    "ಬೆಂಗಳೂರು": {
        "english": "Bengaluru",
        "meaning": "The capital city of Karnataka.",
        "pronunciation": "Ben-ga-loo-ru",
        "example": "ನಾನು ಬೆಂಗಳೂರಿಗೆ ಹೋಗುತ್ತೇನೆ.",
        "example_pronunciation": "Nānu Bengalūrige hōguttēne.",
        "example_meaning": "I am going to Bengaluru."
    },
    "ನಮಸ್ಕಾರ": {
        "english": "Hello / Greetings",
        "meaning": "A respectful way to greet someone.",
        "pronunciation": "Na-mas-ka-ra",
        "example": "ನಮಸ್ಕಾರ, ನೀವು ಹೇಗಿದ್ದೀರಿ?",
        "example_pronunciation": "Namaskāra, nīvu hēgiddīri?",
        "example_meaning": "Hello, how are you?"
    }
}


# -----------------------------------------
# 3. TANGLISH WORDS
# -----------------------------------------

tanglish_words = {
    "namaskara": "ನಮಸ್ಕಾರ",
    "bengaluru": "ಬೆಂಗಳೂರು",
    "hegidira": "ಹೇಗಿದ್ದೀರಾ",
    "dhanyavada": "ಧನ್ಯವಾದ",
    "nanu": "ನಾನು",
    "neevu": "ನೀವು",
    "oota": "ಊಟ",
    "neeru": "ನೀರು",
    "mane": "ಮನೆ",
    "hogi": "ಹೋಗಿ"
}


# -----------------------------------------
# 4. FLASK PAGE ROUTES
# -----------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/scan")
def scan():
    return render_template("scan.html")


@app.route("/bank")
def bank():
    return render_template("bank.html")


@app.route("/practice")
def practice():
    return render_template("practice.html")


# -----------------------------------------
# 5. SARVAM AI TRANSLATION
# -----------------------------------------

def translate_kannada_word(word):
    """Translate one Kannada word using Sarvam AI."""

    if not SARVAM_API_KEY:
        return None, "Sarvam API key is missing."

    try:
        response = requests.post(
            "https://api.sarvam.ai/translate",
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "input": word,
                "source_language_code": "kn-IN",
                "target_language_code": "en-IN",
                "model": "mayura:v1",
                "mode": "modern-colloquial"
            },
            timeout=15
        )

        response.raise_for_status()

        translated = response.json().get(
            "translated_text", ""
        ).strip()

        if not translated:
            return None, "No translation was returned."

        return translated, None

    except requests.RequestException as error:
        print("Sarvam API error:", error)
        return None, "Online translation is temporarily unavailable."


# -----------------------------------------
# 6. UNDERSTAND KANNADA TEXT
# -----------------------------------------

@app.route("/understand", methods=["POST"])
def understand():

    data = request.get_json(silent=True) or {}
    text = data.get("word", "")

    if not isinstance(text, str):
        return jsonify({
            "success": False,
            "message": "Invalid Kannada text."
        }), 400

    text = text.strip()

    if not text:
        return jsonify({
            "success": False,
            "message": "No Kannada text was received."
        }), 400

    if len(text) > 300:
        return jsonify({
            "success": False,
            "message": "Please scan a shorter text."
        }), 400

    # Extract Kannada words from OCR output.
    words = re.findall(r"[\u0C80-\u0CFF]+", text)

    if not words:
        return jsonify({
            "success": False,
            "message": "No Kannada words could be identified."
        }), 400

    results = []

    # Avoid duplicate lookups.
    for word in dict.fromkeys(words):

        # PRIORITY 1: LOCAL DICTIONARY
        if word in kannada_words:

            results.append({
                "word": word,
                "source": "Kannada Lens Local Dictionary",
                "details": kannada_words[word]
            })

            continue

        # PRIORITY 2: ALAR SQLITE DICTIONARY
        alar_result = lookup_alar(word)

        if alar_result:

            results.append({
                "word": word,
                "source": "Alar Kannada-English Dictionary",
                "details": alar_result
            })

            continue

        # PRIORITY 3: SARVAM AI
        translated, error = translate_kannada_word(word)

        if translated:

            is_transliteration = (
                translated.casefold() == word.casefold()
                or (
                    re.fullmatch(r"[A-Za-z][A-Za-z\s'-]*", translated)
                    and translated.casefold() in {
                        "maruti", "krishna", "rama", "sita"
                    }
                )
            )

            if is_transliteration:

                results.append({
                    "word": word,
                    "source": "Sarvam AI - Possible Proper Noun",
                    "details": {
                        "english": translated,
                        "meaning": (
                            "This may be a person's name or proper noun. "
                            "A verified dictionary meaning was not found."
                        ),
                        "pronunciation": "Not available",
                        "example": "",
                        "example_pronunciation": "",
                        "example_meaning": "No verified example available."
                    }
                })

            else:

                results.append({
                    "word": word,
                    "source": "Sarvam AI Translation",
                    "details": {
                        "english": translated,
                        "meaning": (
                            "AI-generated translation. "
                            "Meaning may depend on context."
                        ),
                        "pronunciation": "Not available",
                        "example": "",
                        "example_pronunciation": "",
                        "example_meaning": "No verified example available."
                    }
                })

        else:

            results.append({
                "word": word,
                "source": "Unavailable",
                "error": error or "No dictionary result found."
            })

    return jsonify({
        "success": True,
        "results": results
    })


# -----------------------------------------
# 7. TANGLISH SEARCH
# -----------------------------------------

@app.route("/tanglish-search", methods=["POST"])
def tanglish_search():

    data = request.get_json(silent=True) or {}

    query = data.get("query", "")

    if not isinstance(query, str):
        return jsonify({
            "success": False,
            "message": "Invalid search query."
        }), 400

    query = query.strip().lower()

    kannada_word = tanglish_words.get(query)

    if kannada_word:

        details = kannada_words.get(kannada_word)

        return jsonify({
            "success": True,
            "word": kannada_word,
            "details": details
        })

    return jsonify({
        "success": False,
        "message": "Word not found. Try another Tanglish word."
    })


# -----------------------------------------
# 8. RUN APPLICATION
# -----------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
