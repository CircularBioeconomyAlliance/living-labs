import streamlit as st
from knowledgeBase import BedrockKnowledgeBase, knowledge_base_id
from extractOutcomes import OutcomeExtractor
import time
import json

st.set_page_config(page_title="CBA ReGen Platform", page_icon="🌱")

# Initialize Bedrock Knowledge Base
kb = BedrockKnowledgeBase()

# initiate outcome extractor
extractor = OutcomeExtractor()

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
    
    # Process document
    with st.spinner("Processing your document and extracting goals..."):
        # Extract goals from document (placeholder)
        outcomes = extractor.extract_outcomes(uploaded_file.getvalue())
        # goals =   ', '.join(outcomes['outcomes'])
        goals = '\n\n'.join([f"• {outcome}" for outcome in outcomes['outcomes']])
    
    ## Identify indicators to measure based on the goals
    with st.spinner("Processing your document identifying indicators to measure..."):
        prompt = f"""
        You are an expert in ecological monitoring and CBA's Living Labs framework.
        Please extract the indicators from the following outcomes and return them as a JSON list of strings.
        Do not include any explanations or additional text, just the JSON list.

        Outcomes:
        {json.dumps(outcomes, indent=2)}
        """       
        
        response = kb.query_with_generation(
            knowledge_base_id=knowledge_base_id,
            query=prompt,
            model_arn="arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
        )

        try:
            # Extract JSON from AI response
            response_text = response['output']['text']
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            indicators_data = json.loads(response_text[json_start:json_end])
        except:
            indicators_data = []
    
    indicators = '\n\n'.join([f"• {indicator}" for indicator in indicators_data[:5]])

    # Agent starts conversation
    initial_message_outcomes = f"I've analyzed your project document. Here are the outcomes I identified:\n\n{goals}"
    st.session_state.messages.append({"role": "assistant", "content": initial_message_outcomes})
    initial_message_indicators = f"I have indentified the following indications which need to be measured.\n\n{indicators}\n\n\nWhich indicator would you like to start with? What is your budget and technical expertise and I'll help you find the correct method to collect the data?"
    st.session_state.messages.append({"role": "assistant", "content": initial_message_indicators})
    # initial_message = f"I've analyzed your project document. Here are the outcomes I identified:\n\n{goals}\n\n\n\nI have indentified the following indications which need to be measured.\n\n{indicators}\n\n\nWhich indicator would you like to start with? What is your budget and technical expertise and I'll help you find the correct method to collect the data?"
    # st.session_state.messages.append({"role": "assistant", "content": initial_message})
    st.session_state.file_processed = True
    st.session_state.goals = goals
    st.rerun()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])



# Chat input
if st.session_state.file_processed:
    user_input = st.chat_input("Type your response...")
    
    if user_input:
        # Get AI response
        with st.spinner("Thinking..."):
            response = kb.query_with_generation(
                knowledge_base_id=knowledge_base_id,
                query=user_input,
                conversation=json.dumps(st.session_state.messages),
                model_arn="arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
            )
            ai_response = response['output']['text']

        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Add AI response
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        st.rerun()
