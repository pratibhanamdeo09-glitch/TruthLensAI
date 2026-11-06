"""
TruthLensAI - model training + comparison script.

Fake.csv aur True.csv se kai models train karta hai, unko compare karta hai,
aur sabse acche model ko models/ folder mein save karta hai.

Run (project root se):
    python backend\train_model.py
"""
import json
import os
import re
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
MODELS_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODELS_DIR, "fake_news_model.pkl")
REPORT_PATH = os.path.join(MODELS_DIR, "model_report.json")


def clean_text(text: str) -> str:
    text = str(text)
    # True.csv ke articles "WASHINGTON (Reuters) - ..." se shuru hote hain.
    # Ye hata dete hain, warna model sirf "Reuters" dekh kar answer de dega.
    text = re.sub(r"^.{0,80}?\(Reuters\)\s*-\s*", "", text)
    text = text.lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load_data() -> pd.DataFrame:
    fake = pd.read_csv(os.path.join(DATASET_DIR, "Fake.csv"))
    true = pd.read_csv(os.path.join(DATASET_DIR, "True.csv"))
    fake["label"] = 0  # 0 = FAKE
    true["label"] = 1  # 1 = REAL
    df = pd.concat([fake, true], ignore_index=True)
    df["content"] = (df["title"].fillna("") + " " + df["text"].fillna("")).map(clean_text)
    df = df[df["content"].str.len() > 0].drop_duplicates(subset="content")
    return df.sample(frac=1, random_state=42).reset_index(drop=True)


# Jitne models compare karne hain
CANDIDATES = {
    "Naive Bayes": lambda: MultinomialNB(alpha=0.1),
    "Logistic Regression": lambda: LogisticRegression(max_iter=1000, C=10),
    "Linear SVM": lambda: CalibratedClassifierCV(LinearSVC(C=1.0), cv=3),
    "SGD Classifier": lambda: SGDClassifier(loss="modified_huber", random_state=42),
    "Random Forest": lambda: RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=42),
}


def word_weights(clf):
    """
    Har shabd ka 'weight' nikalta hai: positive = REAL ki taraf, negative = FAKE ki taraf.
    Isi se 'Explain why' feature kaam karta hai. Random Forest jaise models
    direction nahi batate, unke liye None return hota hai.
    """
    if isinstance(clf, MultinomialNB):
        return clf.feature_log_prob_[1] - clf.feature_log_prob_[0]
    if isinstance(clf, CalibratedClassifierCV):
        return np.mean([c.estimator.coef_[0] for c in clf.calibrated_classifiers_], axis=0)
    if hasattr(clf, "coef_"):
        return clf.coef_[0]
    return None


def main():
    print("Dataset load ho raha hai...")
    df = load_data()
    print(f"Total articles: {len(df)}  (fake={sum(df.label == 0)}, real={sum(df.label == 1)})")

    X_train, X_test, y_train, y_test = train_test_split(
        df["content"], df["label"], test_size=0.2, random_state=42, stratify=df["label"]
    )

    print("Text ko numbers (TF-IDF) mein badal rahe hain...")
    tfidf = TfidfVectorizer(stop_words="english", max_df=0.7, min_df=2,
                            ngram_range=(1, 2), max_features=100_000)
    Xtr = tfidf.fit_transform(X_train)
    Xte = tfidf.transform(X_test)

    results, fitted = [], {}
    for name, make in CANDIDATES.items():
        print(f"  -> {name} train ho raha hai...", end=" ", flush=True)
        clf = make()
        start = time.time()
        clf.fit(Xtr, y_train)
        secs = time.time() - start
        preds = clf.predict(Xte)
        tn, fp, fn, tp = confusion_matrix(y_test, preds).ravel()
        r = {
            "model": name,
            "accuracy": round(accuracy_score(y_test, preds), 4),
            "precision": round(precision_score(y_test, preds), 4),
            "recall": round(recall_score(y_test, preds), 4),
            "f1": round(f1_score(y_test, preds), 4),
            "train_seconds": round(secs, 1),
            "confusion_matrix": {"true_fake": int(tn), "fake_as_real": int(fp),
                                 "real_as_fake": int(fn), "true_real": int(tp)},
        }
        results.append(r)
        fitted[name] = clf
        print(f"accuracy={r['accuracy']:.4f}  f1={r['f1']:.4f}  ({secs:.1f}s)")

    results.sort(key=lambda r: (r["f1"], r["accuracy"]), reverse=True)
    best_name = results[0]["model"]
    best = fitted[best_name]

    # Explanation ke liye weights: best model se, warna Logistic Regression se
    weights = word_weights(best)
    explainer = best_name
    if weights is None:
        weights = word_weights(fitted["Logistic Regression"])
        explainer = "Logistic Regression"

    print("\n=== Model Comparison ===")
    print(f"{'Model':<22}{'Accuracy':>10}{'F1':>10}{'Time(s)':>10}")
    for r in results:
        print(f"{r['model']:<22}{r['accuracy']:>10.4f}{r['f1']:>10.4f}{r['train_seconds']:>10}")
    print(f"\nSabse accha model: {best_name}")

    bundle = {
        "pipeline": Pipeline([("tfidf", tfidf), ("clf", best)]),
        "model_name": best_name,
        "feature_names": tfidf.get_feature_names_out(),
        "weights": np.asarray(weights, dtype=float),
        "explainer": explainer,
    }
    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(bundle, MODEL_PATH)

    report = {
        "best_model": best_name,
        "explainer": explainer,
        "dataset": {"total": int(len(df)), "fake": int(sum(df.label == 0)),
                    "real": int(sum(df.label == 1)), "test_size": int(len(y_test))},
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Model save ho gaya: {MODEL_PATH}")
    print(f"Report save ho gayi: {REPORT_PATH}")


if __name__ == "__main__":
    main()
