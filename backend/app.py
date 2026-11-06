import json
import os
import re

import joblib
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import database
from scraper import ScrapeError, fetch_article
from train_model import MODEL_PATH, REPORT_PATH, clean_text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)  # Live Server (port 5500) se bhi API call allow
database.init_db()

# Model ek baar load karo (har request par nahi)
bundle = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None


def client_id():
    """Har browser/phone apni random ID bhejta hai, taaki sabki history alag rahe."""
    cid = request.headers.get("X-Client-Id", "")
    return cid if re.fullmatch(r"[A-Za-z0-9-]{8,64}", cid) else None


def explain(cleaned: str, top_n: int = 8):
    """Kaun se shabdon ne result ko FAKE ya REAL ki taraf dhakela."""
    vec = bundle["pipeline"].named_steps["tfidf"].transform([cleaned])
    idx = vec.indices
    contrib = vec.data * bundle["weights"][idx]
    order = contrib.argsort()
    names = bundle["feature_names"]

    def pick(indices):
        return [{"word": str(names[idx[i]]), "score": round(float(abs(contrib[i])), 4)}
                for i in indices]

    fake_words = pick([i for i in order[:top_n] if contrib[i] < 0])
    real_words = pick([i for i in order[::-1][:top_n] if contrib[i] > 0])
    return fake_words, real_words


# ---------- Pages ----------
@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/dashboard")
def dashboard():
    return send_from_directory(FRONTEND_DIR, "dashboard.html")


# ---------- API ----------
@app.route("/api/health")
def health():
    return jsonify({
        "message": "TruthLensAI Backend is running",
        "model_loaded": bundle is not None,
        "model": bundle["model_name"] if bundle else None,
    })


@app.route("/predict", methods=["POST"])
@app.route("/api/predict", methods=["POST"])
def predict():
    if bundle is None:
        return jsonify({"error": "Model nahi mila. Pehle 'python backend\\train_model.py' chalao."}), 500

    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    text = str(data.get("text", "")).strip()
    title = None

    if url:
        try:
            article = fetch_article(url)
        except ScrapeError as e:
            return jsonify({"error": str(e)}), 400
        title, text = article["title"], article["text"]
        text_for_model = f"{title} {text}"
    else:
        if len(text) < 20:
            return jsonify({"error": "Kam se kam 20 characters ka news text bhejo."}), 400
        text_for_model = text

    cleaned = clean_text(text_for_model)
    if not cleaned:
        return jsonify({"error": "Text mein English shabd nahi mile. Abhi model sirf English news samajhta hai."}), 400

    proba = bundle["pipeline"].predict_proba([cleaned])[0]  # [fake, real]
    is_real = proba[1] >= 0.5
    prediction = "REAL" if is_real else "FAKE"
    confidence = round(float(max(proba)) * 100, 2)
    fake_words, real_words = explain(cleaned)

    word_count = len(text.split())
    warning = None
    if word_count < 60:
        warning = "Text chhota hai, result kam bharosemand ho sakta hai. Poora article do."

    cid = client_id()
    check_id = None
    if cid:
        check_id = database.save_check(
            client_id=cid,
            source="url" if url else "text",
            url=url or None,
            title=title,
            snippet=text[:200],
            prediction=prediction,
            confidence=confidence,
        )

    return jsonify({
        "id": check_id,
        "prediction": prediction,
        "confidence": confidence,
        "fake_probability": round(float(proba[0]) * 100, 2),
        "real_probability": round(float(proba[1]) * 100, 2),
        "model": bundle["model_name"],
        "explanation": {"fake_words": fake_words, "real_words": real_words},
        "title": title,
        "text": text if url else None,
        "word_count": word_count,
        "warning": warning,
    })


@app.route("/api/history")
def history():
    cid = client_id()
    if not cid:
        return jsonify([])
    try:
        limit = max(1, min(int(request.args.get("limit", 50)), 500))
    except ValueError:
        limit = 50
    return jsonify(database.get_history(cid, limit))


@app.route("/api/history", methods=["DELETE"])
def clear_history():
    cid = client_id()
    if cid:
        database.clear_history(cid)
    return jsonify({"ok": True})


@app.route("/api/stats")
def stats():
    cid = client_id()
    if not cid:
        return jsonify({"total": 0, "fake": 0, "real": 0, "avg_confidence": 0, "daily": []})
    return jsonify(database.get_stats(cid))


@app.route("/api/model-info")
def model_info():
    if not os.path.exists(REPORT_PATH):
        return jsonify({"error": "Report nahi mili. Model train karo."}), 404
    with open(REPORT_PATH, encoding="utf-8") as f:
        return jsonify(json.load(f))


if __name__ == "__main__":
    # Laptop par: python backend\app.py
    # Online (Render) par gunicorn chalata hai, ye block wahan use nahi hota
    app.run(debug=True)
