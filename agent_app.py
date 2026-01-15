import streamlit as st
import time
import json
from pathlib import Path
from ArgicultureAgent import agriculture_agent


############################################

st.set_page_config(page_title="CBA - ReGen Platform", page_icon="🌱")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "file_processed" not in st.session_state:
    st.session_state.file_processed = False

# Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,400;0,600;0,700;1,400&display=swap');
.stApp {
    background-color: #031f35;
    font-family: 'Montserrat', 'Avenir Next', sans-serif;
}
h1 {
    color: white !important;
    font-family: 'Montserrat', 'Avenir Next', sans-serif;
    font-weight: 700;
    text-transform: uppercase;
}
p {
    color: white !important;
    font-family: 'Montserrat', 'Avenir Next', sans-serif;
    font-weight: 400;
}
ul, ol, li {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# Header
st.image("materials/CBA_logo_RGB.svg", width=200)
st.title("CBA ReGen Platform")
st.markdown("*Your AI assistant for regenerative landscape monitoring and evaluation*")
st.markdown("---")

# File upload
uploaded_file = st.file_uploader(
    "📄 Drag and drop your Project PDF here to start",
    type=["pdf"],
    accept_multiple_files=False
)

if uploaded_file and not st.session_state.file_processed:
    st.success(f"Uploaded: {uploaded_file.name}")
    
    # Write PDF to file
    pdf_path = Path(uploaded_file.name)
    pdf_path.write_bytes(uploaded_file.getvalue())
    
    # Add upload message
    st.chat_message("user").markdown(f"Uploaded file: {uploaded_file.name}")
    st.session_state.messages.append({"role": "user", "content": f"Uploaded file: {uploaded_file.name}"})
    
    # Get initial agent response
    with st.spinner("Processing document."):
        response = agriculture_agent(f"Please process this agriculture PDF: '{uploaded_file.name}'")
    st.chat_message("assistant").markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.session_state.file_processed = True
    st.session_state.uploaded_file_name = uploaded_file.name
    st.rerun()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])



# Chat input
if st.session_state.file_processed:
    user_input = st.chat_input("What do you want to know?")
    
    if user_input:
        # Add user message
        st.chat_message("user").markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Get AI response
        with st.spinner("Thinking..."):
            response = agriculture_agent(user_input)
        
        # Add AI response
        st.chat_message("assistant").markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
