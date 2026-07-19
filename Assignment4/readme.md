## 📸 Demo Video

Watch the app in action — showcasing the AI-powered Magic Enhance feature, the Prompt Battle A/B voting system, the Surprise Me generator, and downloading the image as a properly formatted `.png` file.

https://github.com/user-attachments/assets/f032453f-975b-47b8-ac43-22506172fabc

# 🎨 AI Image Studio

An interactive **Streamlit-based AI Image Generator** built using the **Pollinations API** and **Google Gemini API**, upgraded from a basic prototype into a feature-rich creative tool with AI-powered prompt engineering, gamified prompt battles, and session-based history.

## 🚀 Features

### Core Fixes
- **Working Width/Height Sliders** — Image dimensions are now correctly passed as URL parameters, so the generated image actually matches the size you select.
- **Correct File Extension** — Downloaded images are saved with a dynamic, style-based filename (e.g., `Anime_image.png`) so your device opens them correctly.

### AI-Powered Enhancements
- **✨ Magic Enhance (Gemini-Powered)** — Rewrites lazy, short prompts into vivid, descriptive prompts using the Gemini API, with a static fallback if the API is unavailable.
- **⚔️ Prompt Battle (A/B AI Duel)** — Gemini generates two distinct enhanced versions of your prompt; both are turned into images side-by-side, and you can vote for the better one.
- **🔍 Compare With/Without Enhance** — See the same prompt generated both with and without AI enhancement, side-by-side.

### Fun & Productivity Features
- **🎲 Surprise Me!** — Instantly generates an image from a curated list of creative prompts, for when you have writer's block.
- **🖼️ Session Gallery** — Every image you generate in a session is saved to a scrollable gallery with timestamps.
- **⭐ Favorites** — Save your best generations to a separate favorites section.
- **📐 Aspect Ratio Presets** — Quick buttons for Square, Portrait, and Landscape dimensions.
- **🚫 Style-Based Negative Prompts** — Each art style automatically avoids common visual mismatches (e.g., Photorealistic avoids cartoon/blurry results).
- **📝 Live Word Counter & Prompt Warning** — Alerts users if their prompt is too short for good results.
- **🎈 Success Animations** — Fun loading messages and balloon animations on successful generation.

## 🛠️ Tech Stack
- **Frontend/App Framework:** Streamlit
- **Image Generation:** Pollinations API (Flux model)
- **AI Prompt Enhancement:** Google Gemini API (`gemini-1.5-flash`)
- **Language:** Python

## ⚙️ Setup Instructions

1. Clone this repository:
```bash
   git clone <your-repo-url>
   cd <your-repo-folder>
```

2. Install dependencies:
```bash
   pip install streamlit requests google-generativeai python-dotenv
```

3. Create a `.env` file in the project root and add your Gemini API key:
   GEMINI_API_KEY=your_actual_key_here

4. Run the app:
```bash
   streamlit run app.py
```

## 📌 Notes
- If the Gemini API is unavailable or rate-limited, the app automatically falls back to a static prompt enhancement, ensuring the application never breaks.
- Built as part of the Mirai School of Technology internship assignment.

## 🙋‍♀️ Author
**Shruti** — B.Tech CSE (AI/ML), UEM Jaipur
