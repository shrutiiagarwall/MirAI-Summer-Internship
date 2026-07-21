# 📖 MirAI Visual Novel

> An AI-powered interactive narrative experience built for the Mirai School of Technology Capstone.

[![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit)](https://streamlit.io)
[![Gemini](https://img.shields.io/badge/Powered%20by-Gemini%20AI-4285F4?logo=google)](https://ai.google.dev)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org)

---

## 🎮 What It Does

MirAI Visual Novel is a fully interactive, AI-generated story experience where every choice you make shapes a unique narrative. The AI generates story text, images, and voice narration in real time.

**Choose your genre → make choices → watch your story unfold.**

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **AI Story Engine** | Gemini API generates structured story scenes (text + choices + mood) as strict JSON |
| 🖼️ **Dynamic Images** | Gemini image models generate scene visuals; falls back to Pollinations API |
| 🎙️ **Neural TTS** | `edge-tts` narrates each scene; `gTTS` as fallback |
| 🎤 **Voice Input** | Speak your choices using your microphone (Google Speech Recognition) |
| 🗺️ **Live Story Map** | Visual graph of your story path using Graphviz |
| 📄 **PDF Export** | Download your full playthrough as a styled PDF |
| 🏆 **Achievement System** | Unlock multiple endings based on your choices |
| 🔑 **API Key Rotation** | Automatically rotates across multiple Gemini keys when one hits rate limits |
| 🎭 **Demo Mode** | Runs entirely offline — no API calls, safe for demos and screen recording |

---

## 🏗️ Architecture

```
app.py                  ← Main Streamlit router & UI
├── gemini_client.py    ← Gemini API + key rotation + JSON parsing
├── image_client.py     ← Image generation (Gemini → Pollinations → local asset)
├── tts_client.py       ← Text-to-speech (edge-tts → gTTS)
├── story_state.py      ← Session state management & metrics
├── ui_components.py    ← Reusable UI widgets (trust meter, story map, etc.)
├── pdf_export.py       ← PDF generation with fpdf2
└── demo_data.py        ← Offline fallback scenes for demo mode
```

---

## 🚀 Quick Start (Local)

### 1. Clone and install

```bash
git clone https://github.com/shrutiiagarwall/MirAI-Summer-Internship.git
cd "MirAI-Summer-Internship/Assignment 5"
pip install -r requirements.txt
```

### 2. Set up API keys

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API keys:

```ini
GEMINI_API_KEY_1=your_key_here
GEMINI_API_KEY_2=optional_second_key
```

Get free keys at → [Google AI Studio](https://aistudio.google.com/app/apikey)

### 3. Run

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

> **No API keys?** Enable **Demo Mode** in the sidebar — the app runs fully offline.

---

## ☁️ Deployment (Streamlit Community Cloud)

1. Fork / push this repo to your GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select this repo → set **Main file path** to `Assignment 5/app.py`
4. Under **Advanced settings → Secrets**, add:

```toml
GEMINI_API_KEY_1 = "your_key_here"
GEMINI_API_KEY_2 = "your_second_key_here"
```

5. Click **Deploy** — live in ~2 minutes.

---

## 🔑 API Key Rotation

Add up to 5 Gemini keys. When Key 1 hits rate limits, the app automatically switches to Key 2, then Key 3, etc. — no manual intervention needed.

```ini
GEMINI_API_KEY_1=primary_key
GEMINI_API_KEY_2=backup_key
GEMINI_API_KEY_3=
GEMINI_API_KEY_4=
GEMINI_API_KEY_5=
```

If all Gemini keys are exhausted, images fall back to [Pollinations API](https://pollinations.ai) (free, no key needed).

---

## 📦 Requirements

```
streamlit >= 1.35
google-generativeai >= 0.7
google-genai
edge-tts
gTTS
Pillow
fpdf2
requests
python-dotenv
streamlit-mic-recorder
SpeechRecognition
```

---

## 📁 Project Structure

```
Assignment 5/
├── app.py                  ← Entry point
├── gemini_client.py        ← AI story generation
├── image_client.py         ← Image generation
├── tts_client.py           ← Voice narration
├── story_state.py          ← State management
├── ui_components.py        ← UI widgets
├── pdf_export.py           ← PDF export
├── demo_data.py            ← Offline demo scenes
├── create_assets.py        ← Generate local fallback images
├── assets/                 ← Mood-matched fallback images
├── requirements.txt
├── .env.example            ← Template (copy to .env)
└── .streamlit/
    └── config.toml         ← Dark theme configuration
```

---

## 🎓 Capstone Context

**Project**: MirAI School of Technology — Summer Internship, Assignment 5  
**Theme**: AI + Interactive Storytelling  
**Key Technologies**: Gemini 2.0 Flash, Streamlit, edge-tts, fpdf2, Pollinations  

---

## ⚠️ Notes

- `.env` is gitignored — **never commit your API keys**
- `temp_images/` and `temp_audio/` are generated at runtime and gitignored
- Demo Mode guarantees zero API calls — safe for offline demos
