
# Copyright 2025 Snowflake Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from htbuilder.units import rem
from htbuilder import div, styles
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
import datetime
import textwrap
import time
import json

import streamlit as st
from knowledgeBase import BedrockKnowledgeBase, knowledge_base_id
from extractOutcomes import OutcomeExtractor

st.set_page_config(page_title="CBA Farm Assistant", page_icon="🧑‍🌾")

# -----------------------------------------------------------------------------
# Set things up.


DEBUG_MODE = True
executor = ThreadPoolExecutor(max_workers=5)


SUGGESTIONS = {    
    ":green[:material/database:] what are the best diversity indicator?": (
        "What is the highest accuracy, lowest cost method for the species diversity indicator?"
        ""
    ),
}

kb = BedrockKnowledgeBase()
extractor = OutcomeExtractor()

def build_prompt(**kwargs):
    """Builds a prompt string with the kwargs as HTML-like tags.

    For example, this:

        build_prompt(foo="1\n2\n3", bar="4\n5\n6")

    ...returns:

        '''
        <foo>
        1
        2
        3
        </foo>
        <bar>
        4
        5
        6
        </bar>
        '''
    """
    prompt = []

    for name, contents in kwargs.items():
        if contents:
            prompt.append(f"<{name}>\n{contents}\n</{name}>")

    prompt_str = "\n".join(prompt)

    return prompt_str


# Just some little objects to make tasks more readable.
TaskInfo = namedtuple("TaskInfo", ["name", "function", "args"])
TaskResult = namedtuple("TaskResult", ["name", "result"])


def build_question_prompt(question):
    return question


def generate_chat_summary(messages):
    """Summarizes the chat history in `messages`."""
    prompt = build_prompt(
        instructions="Summarize this conversation as concisely as possible.",
        conversation=history_to_text(messages),
    )

    return kb.query_with_generation(
        knowledge_base_id=knowledge_base_id,
        query=prompt,
        model_arn="arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
    )


def history_to_text(chat_history):
    """Converts chat history into a string."""
    return "\n".join(f"[{h['role']}]: {h['content']}" for h in chat_history)


def search_relevant_pages(query):
    """Searches the markdown contents of Streamlit's documentation."""
    cortex_search_service = (
        root.databases[DB].schemas[SCHEMA].cortex_search_services[PAGES_SEARCH_SERVICE]
    )

    context_documents = cortex_search_service.search(
        query,
        columns=["PAGE_URL", "PAGE_CHUNK"],
        filter={},
        limit=PAGES_CONTEXT_LEN,
    )

    results = context_documents.results

    context = [f"[{row['PAGE_URL']}]: {row['PAGE_CHUNK']}" for row in results]
    context_str = "\n".join(context)

    return context_str


def search_relevant_docstrings(query):
    """Searches the docstrings of Streamlit's commands."""
    cortex_search_service = (
        root.databases[DB]
        .schemas[SCHEMA]
        .cortex_search_services[DOCSTRINGS_SEARCH_SERVICE]
    )

    context_documents = cortex_search_service.search(
        query,
        columns=["STREAMLIT_VERSION", "COMMAND_NAME", "DOCSTRING_CHUNK"],
        filter={"@eq": {"STREAMLIT_VERSION": "latest"}},
        limit=DOCSTRINGS_CONTEXT_LEN,
    )

    results = context_documents.results

    context = [
        f"[Document {i}]: {row['DOCSTRING_CHUNK']}" for i, row in enumerate(results)
    ]
    context_str = "\n".join(context)

    return context_str


def get_response(prompt):
    
    return  kb.query_with_generation(
        knowledge_base_id=knowledge_base_id,
        query=prompt,
        model_arn="arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
    )


def send_telemetry(**kwargs):
    """Records some telemetry about questions being asked."""
    # TODO: Implement this.
    pass


def show_feedback_controls(message_index):
    """Shows the "How did I do?" control."""
    st.write("")

    with st.popover("How did I do?"):
        with st.form(key=f"feedback-{message_index}", border=False):
            with st.container(gap=None):
                st.markdown(":small[Rating]")
                rating = st.feedback(options="stars")

            details = st.text_area("More information (optional)")

            if st.checkbox("Include chat history with my feedback", True):
                relevant_history = st.session_state.messages[:message_index]
            else:
                relevant_history = []

            ""  # Add some space

            if st.form_submit_button("Send feedback"):
                # TODO: Submit feedback here!
                pass


def get_indicators(outcomes):
    """Extract indicators from outcomes."""
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

    return indicators_data

def get_indicator_method(indicator, preference):
    """use the berock knowledge base to get the best method for an indicator"""
    prompt = f"""I want to know the best method for the indicator {indicator}. Please return the best method based on {preference}"""

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

    return indicators_data


# -----------------------------------------------------------------------------
# Draw the UI.

# Set navy blue background
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
h2, h3 {
    color: white !important;
    font-family: 'Montserrat', 'Avenir Next', sans-serif;
    font-weight: 600;
}
p {
    color: white !important;
    font-family: 'Montserrat', 'Avenir Next', sans-serif;
    font-weight: 400;
}
strong {
    font-weight: 600;
}
em {
    font-style: italic;
    font-weight: 400;
}
</style>
""", unsafe_allow_html=True)

# Display CBA logo
st.image("materials/CBA_logo_RGB.svg", width=200)

title_row = st.container(
    horizontal=True,
    vertical_alignment="bottom",
)

with title_row:
    st.title(
        "CBA Living Labs Assistant",
        anchor=False,
        width="stretch",
    )

# Add descriptive blurb
st.markdown("*Our AI assistant helps regenerative landscape projects turn CBA’s seven science-based Principles into practical, measurable indicators. It guides teams to select the most relevant metrics and consolidate data into a unified system for tracking progress. By enabling consistent measurement, learning, and cross-project insights, the assistant strengthens accountability and accelerates the global adoption of nature-based solutions.*")
st.markdown("""---""")

user_just_asked_initial_question = (
    "initial_question" in st.session_state and st.session_state.initial_question
)

user_just_clicked_suggestion = (
    "selected_suggestion" in st.session_state and st.session_state.selected_suggestion
)

user_first_interaction = (
    user_just_asked_initial_question or user_just_clicked_suggestion
)

has_message_history = (
    "messages" in st.session_state and len(st.session_state.messages) > 0
)

## show file upload to start journey
if "file_processed" not in st.session_state:
    st.session_state.file_processed = False

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.container():
    # File uploader in main chat area
    uploaded_file = st.file_uploader(
        "📄 Drag and drop your Project PDF here to start",
        type=["pdf"],
        accept_multiple_files=False
    )

    if uploaded_file and not st.session_state.file_processed:
        st.success(f"Uploaded: {uploaded_file.name}")
        
        # Process file and start conversation
        with st.spinner("Processing your document..."):
            # Extract text from PDF (placeholder - implement actual extraction)
            # For now, we'll simulate processing
            time.sleep(1)
            
        # Agent starts conversation
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your project outcomes..."):
                initial_prompt = "I've reviewed your project document. To help you select the most appropriate monitoring methods and indicators, I need to understand your project context better. Could you please tell me about your team's technical capabilities and available budget for monitoring activities?"
                
                def response_generator():
                    for char in initial_prompt:
                        yield char
                
                st.write_stream(response_generator())
        
        # Add to chat history
        st.session_state.messages.append({"role": "assistant", "content": initial_prompt})
        st.session_state.file_processed = True
        st.rerun()



# Show chat input at the bottom
user_message = st.chat_input("Type your response...")

with title_row:

    def clear_conversation():
        st.session_state.messages = []
        st.session_state.initial_question = None
        st.session_state.selected_suggestion = None

    st.button(
        "Restart",
        icon=":material/refresh:",
        on_click=clear_conversation,
    )

if "prev_question_timestamp" not in st.session_state:
    st.session_state.prev_question_timestamp = datetime.datetime.fromtimestamp(0)

# Display chat messages from history as speech bubbles.
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.container()  # Fix ghost message bug.

        st.markdown(message["content"])

if user_message:
    # When the user posts a message...

    # Streamlit's Markdown engine interprets "$" as LaTeX code (used to
    # display math). The line below fixes it.
    user_message = user_message.replace("$", r"\$")

    # Display message as a speech bubble.
    with st.chat_message("user"):
        st.text(user_message)

    # Display assistant response as a speech bubble.
    with st.chat_message("assistant"):
        with st.spinner("Waiting..."):
            # Rate-limit the input if needed.
            question_timestamp = datetime.datetime.now()
            time_diff = question_timestamp - st.session_state.prev_question_timestamp
            st.session_state.prev_question_timestamp = question_timestamp


            user_message = user_message.replace("'", "")

        # Build a detailed prompt.
        if DEBUG_MODE:
            with st.status("Computing prompt...") as status:
                full_prompt = build_question_prompt(user_message)
                st.code(full_prompt)
                status.update(label="Prompt computed")
        else:
            with st.spinner("Researching..."):
                full_prompt = build_question_prompt(user_message)

        # Send prompt to LLM.
        with st.spinner("Thinking..."):
            response = get_response(full_prompt)
            response_str = response['output']['text']

            if 'citations' in response:
                ("Sources:", len(response['citations']), "citations found")


        # Put everything after the spinners in a container to fix the
        # ghost message bug.
        with st.container():
            # Stream the LLM response.
            def response_generator():
                for char in response_str:
                    yield char
            
            response = st.write_stream(response_generator())

            # Add messages to chat history.
            st.session_state.messages.append({"role": "user", "content": user_message})
            st.session_state.messages.append({"role": "assistant", "content": response})
