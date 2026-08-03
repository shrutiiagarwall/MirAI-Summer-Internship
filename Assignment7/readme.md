# Life-OS

**Your Brutal-But-Fair Productivity Command Center**

A Streamlit dashboard that visualizes 14-day screen time data and uses the Gemini API as a personalized productivity coach — built as the Mirai School of Technology internship capstone.

---

## 🔗 Live App

**[https://life-os-shruti.streamlit.app](https://my-life-os.streamlit.app/?date=2026-08-02&total=350)**

---

## 🎥 Demo Video

https://github.com/user-attachments/assets/b2cfb7bb-c594-4269-894d-dcc8f806c678

---

## Overview

Life-OS ingests 14 days of screen time data and turns it into an interactive dashboard with live KPIs, AI-driven coaching, and a set of gamified, purely-local features that don't cost a single extra API call. It's built around one core constraint: Gemini's free-tier quota is tiny, so the app is architected to use it as little as possible while still feeling AI-native.

## Features

| Category | Features |
|---|---|
| **Dashboard** | KPI row (total time, top app, delta vs. goal), 14-day trend chart, Life Score gauge, Compare Two Days, App-Flow Sankey diagram |
| **AI Coaching** | Gemini-powered coaching with quota-safe JSON caching, 3 selectable coach personalities (Zen Monk / Drill Sergeant / Sarcastic Bestie), offline rule-based fallback |
| **Gamification** | Streak & XP system, 8 unlockable Achievement Badges |
| **Insights** | What-If Time Machine, Real-World Equivalents converter, Digital Diet Pyramid |
| **Shareables** | Weekly Roast PDF report, Life-OS Wrapped downloadable PNG card, shareable Accountability Link |
| **Reliability** | Live AI / Cached / Offline status indicator, graceful fallback on API errors |

## Prerequisites

- Python 3.10+
- pip 23+
- A Google Gemini API key (free tier works — see [Quota Safety](#quota-safety))

## Installation

```bash
git clone <repo-url>
cd life-os
pip install -r requirements.txt
cp .env.example .env
```

Then open `.env` and set your key:

```
GEMINI_API_KEY=your_actual_key_here
```

## Running Locally

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

## Streamlit Cloud Deployment

1. Push the repo to GitHub (confirm `.env` is gitignored — it is, by default).
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Connect your repo and select `app.py` as the entry point.
4. Under **Secrets**, add:
   ```
   GEMINI_API_KEY = "your_actual_key_here"
   ```
5. Click **Deploy**.

## File Structure

```
life-os/
├── app.py                 # Main Streamlit application
├── screentime.csv         # 14-day screen time dataset
├── coaching_cache.json    # AI response cache (created at runtime)
├── requirements.txt       # Python dependencies
├── .env.example           # API key placeholder
├── .gitignore             # Keeps .env out of version control
└── README.md              # You are here
```

## Quota Safety

Gemini's free tier is limited (as low as 5 RPM / 20 RPD, and some projects see a hard 0-quota block). Life-OS is designed around this:

- The API is **never** called automatically — only the "Get My Coaching 🔥" button triggers a request.
- Responses are **cached by a content hash** (date + aggregated data + personality), so re-viewing the same day never re-calls the API.
- If the API fails for any reason (quota exhausted, network error, missing key), the app **falls back to rule-based offline coaching** instead of crashing.

## License

MIT — hack freely, stay accountable.
