# 🔍 TruthLensAI – Fake News Detector

TruthLensAI is a web app that checks whether a news article looks **REAL** or **FAKE**,
and explains *which words* influenced the decision.

## Features
- **Text or URL input** – paste an article, or just give its link
- **Explainable AI** – shows the words that pushed the result towards fake or real, highlighted in the article
- **Model comparison** – 5 ML models trained and compared; the best one (Linear SVM, ~99.2% test accuracy) is used
- **Dashboard** – personal history of checks, daily chart, and model performance
- **Mobile friendly**

## Tech stack
- **ML:** scikit-learn (TF-IDF + Linear SVM, Logistic Regression, SGD, Random Forest, Naive Bayes)
- **Backend:** Python, Flask, SQLite, BeautifulSoup
- **Frontend:** HTML, CSS, JavaScript

## Dataset
[Fake and Real News Dataset](https://www.kaggle.com/datasets/clmentbisaillon/fake-and-real-news-dataset) (Kaggle) –
~44,000 English news articles. The `(Reuters)` prefix is removed from real articles so the model
cannot cheat by spotting the news agency name.

## Run locally
```bash
pip install -r requirements.txt
python backend/train_model.py   # only needed if models/ is empty (requires dataset/)
python backend/app.py
```
Open http://127.0.0.1:5000

## Project structure
```
backend/
  app.py          Flask server + API
  train_model.py  trains & compares models
  scraper.py      extracts article text from a URL
  database.py     SQLite history
frontend/         web pages (checker + dashboard)
models/           trained model + comparison report
```

## Limitations
The model judges **writing style**, not facts. It was trained only on English news from 2015–2018,
so it may be wrong on short headlines, other languages, or newer topics.
