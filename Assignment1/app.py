import streamlit as st

# ------------------------------------------------------------------
# TASK 1: The UI Shell
# ------------------------------------------------------------------
st.set_page_config(page_title="Echo Chamber 9000", page_icon="📡")

st.title("Echo Chamber 9000")
st.write(
    "Enter your name and a short message below, then hit **Transmit** "
    "to send it into the void. Both fields are required."
)

# ------------------------------------------------------------------
# TASK 2: Multi-Data Collection
# ------------------------------------------------------------------
user_name = st.text_input("Name")
user_message = st.text_input("Message")

# ------------------------------------------------------------------
# TASK 3: The Action Gate
# ------------------------------------------------------------------
transmit = st.button("Transmit")

if transmit:
    # Strip whitespace so a name/message of just spaces still counts as empty
    clean_name = user_name.strip()
    clean_message = user_message.strip()

    # --------------------------------------------------------------
    # TASK 4: Conditional Routing (Edge Cases)
    # --------------------------------------------------------------
    if clean_name == "":
        st.error("Please provide your name.")
    elif clean_message == "":
        st.warning("Please type a message to transmit.")
    else:
        # ----------------------------------------------------------
        # TASK 5: The Formatted Output
        # ----------------------------------------------------------
        st.success(
            f"Transmission successful! Greetings, {clean_name}. "
            f"We received your message: {clean_message}"
        )

        # ------------------------------------------------------
        # ADVANCED CHALLENGE: Token Cost Estimator
        # ------------------------------------------------------
        char_count = len(clean_message)
        token_count = char_count // 4  # 1 token ≈ 4 characters

        st.info(
            f"System Check: Your message will consume approximately "
            f"{token_count} tokens from our context window."
        )