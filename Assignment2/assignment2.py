import streamlit as st
from google import genai
from google.genai import types
import os
from datetime import datetime

# importing dotenv to load environment variables- python -m pip install python-dotenv
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Multiverse of Chatbots", layout="wide")
st.title("THE MULTIVERSE OF CHATBOTS")

# ---------------- Error resilience: check API key ----------------
if not os.getenv("GEMINI_API_KEY"):
    st.error("⚠️ GEMINI_API_KEY not found in your .env file. Please add it and restart the app.")
    st.stop()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ---------------- Character avatars ----------------
avatars = {
    "An expert Hacker": "💻",
    "An angry Ravi Shastri": "🏏",
    "A crazy Ronaldo Fan": "⚽",
    "Nikola Tesla": "⚡",
    "Donald Trump": "🇺🇸",
    "A friendly AI": "🤖"
}

personality_list = list(avatars.keys())

# ---------------- Session state ----------------
if "chat_display" not in st.session_state:
    st.session_state.chat_display = []  # list of dicts: role, name, avatar, text

# ---------------- Sidebar controls ----------------
st.sidebar.header("⚙️ Settings")

group_mode = st.sidebar.checkbox("🎭 Enable Group Chat Mode (talk to multiple characters at once)")

if group_mode:
    selected_personalities = st.sidebar.multiselect(
        "Who do you want in the group chat?",
        personality_list,
        default=[personality_list[0], personality_list[1]]
    )
else:
    personality = st.sidebar.selectbox("Who do you want to talk to?", personality_list)
    selected_personalities = [personality]

intensity = st.sidebar.slider("How intense do you want the conversation to be?", min_value=0, max_value=10, value=5)

response_length = st.sidebar.select_slider(
    "Response Length",
    options=["Short", "Medium", "Long"],
    value="Medium"
)

length_instruction_map = {
    "Short": "Keep your response short — around 2-3 sentences.",
    "Medium": "Keep your response moderate in length — around 4-6 sentences.",
    "Long": "Give a detailed response — around 8-10 sentences."
}

st.sidebar.divider()

# Clear chat button
if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state.chat_display = []
    st.rerun()

# ---------------- Two-column layout ----------------
col_profile, col_chat = st.columns([1, 3])

with col_profile:
    st.subheader("Character Profile")
    if not group_mode:
        st.markdown(f"<h1 style='text-align:center;'>{avatars[personality]}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='text-align:center;'>{personality}</h4>", unsafe_allow_html=True)
    else:
        for p in selected_personalities:
            st.markdown(f"{avatars.get(p, '🗣️')} **{p}**")

    st.caption("Intensity Level")
    st.progress(intensity / 10)

    if intensity <= 3:
        st.info("🙂 Calm mood")
    elif intensity <= 7:
        st.warning("😤 Fired up")
    else:
        st.error("🤬 MAXIMUM INTENSITY")

with col_chat:
    st.subheader("Chat")
    # Render existing chat history (display only, not sent back to API)
    for msg in st.session_state.chat_display:
        with st.chat_message(msg["role"], avatar=msg["avatar"]):
            st.markdown(f"**{msg['name']}**\n\n{msg['text']}")

# ---------------- Chat input (pins to bottom automatically) ----------------
user_message = st.chat_input("Say something to your chosen character(s)...")

if user_message:
    # Show user's message immediately
    st.session_state.chat_display.append({
        "role": "user",
        "name": "You",
        "avatar": "🧑",
        "text": user_message
    })
    with col_chat:
        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_message)

    # Typing indicator text based on intensity
    if intensity <= 3:
        thinking_msg = "🙂 Thinking calmly..."
    elif intensity <= 7:
        thinking_msg = "😤 Getting fired up..."
    else:
        thinking_msg = "🤬 EXPLODING with intensity..."

    # Generate response for each selected personality (group chat or single)
    for p in selected_personalities:
        ai_instructions = (
            f"You are a {p}. You are talking to a user. "
            f"You are to respond to the {user_message} staying completely in character with an intensity level of {intensity}. "
            f"{length_instruction_map[response_length]} "
            f"Always finish your response with a complete sentence — never cut off mid-thought. "
            f"You are to respond in a way that is appropriate for the personality."
        )

        with col_chat:
            with st.chat_message("assistant", avatar=avatars.get(p, "🗣️")):
                st.markdown(f"**{p}**")
                placeholder_caption = st.empty()
                placeholder_caption.caption(thinking_msg)
                try:
                    stream = client.models.generate_content_stream(
                        model="gemini-2.5-flash",
                        contents=ai_instructions
                    )

                    def stream_generator(s):
                        for chunk in s:
                            if chunk.text:
                                yield chunk.text

                    full_response = st.write_stream(stream_generator(stream))
                    placeholder_caption.empty()

                    if full_response:
                        st.caption("✅ Message received!")
                        st.session_state.chat_display.append({
                            "role": "assistant",
                            "name": p,
                            "avatar": avatars.get(p, "🗣️"),
                            "text": full_response
                        })
                    else:
                        st.error("Hmm, no response text came back. Try again!")

                except Exception as e:
                    placeholder_caption.empty()
                    st.error(f"Oops! Something went wrong with {p}: {e}")

# ---------------- Download chat as text file (moved to end, after latest messages are appended) ----------------
if st.session_state.chat_display:
    chat_text = "\n\n".join(
        f"[{msg['name']}]: {msg['text']}" for msg in st.session_state.chat_display
    )
    st.sidebar.download_button(
        label="📥 Download Chat",
        data=chat_text,
        file_name=f"multiverse_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain"
    )