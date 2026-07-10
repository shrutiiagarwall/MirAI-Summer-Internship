import streamlit as st
from google import genai
import os

# importing dotenv to load environment variables- python -m pip install python-dotenv
from dotenv import load_dotenv

load_dotenv()

st.title("THE MULTIVERSE OF CHATBOTS")

personality = st.selectbox("Who do you want to talk to?", [
    "An expert Hacker", "An angry Ravi Shastri", "A crazy Ronaldo Fan",
    "Nikola Tesla", "Donald Trump", "A friendly AI"
])

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

user_message = st.text_input("Say something to your chosen character")

if st.button("SEND"):
    if user_message:
        ai_instructions = (
            f"You are a {personality}. You are talking to a user. "
            f"You are to respond to the {user_message} staying completely in character. "
            f"You are to respond in a way that is appropriate for the personality."
        )
        with st.spinner("Connecting to the multiverse!....."):
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=ai_instructions
                )

                # Check that response actually has usable text
                if response and response.text:
                    st.success("Message received!.....")
                    st.write(response.text)
                else:
                    st.error("Hmm, no response text came back. Try again!")

            except Exception as e:
                st.error(f"Oops! Something went wrong: {e}")
    else:
        st.warning("Please enter a message first!")