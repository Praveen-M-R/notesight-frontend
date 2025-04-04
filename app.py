import streamlit as st
import requests
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io
import re
BASE_URL = "http://localhost:8000"
st.set_page_config(layout="wide", page_title="POC for Notesight")

st.sidebar.title("Features")
page = st.sidebar.radio("Go to", ["Chat"])

if "flashcards" not in st.session_state:
    st.session_state.flashcards = []

if "topics_hierarchy" not in st.session_state:
    st.session_state["topics_hierarchy"] = {}
if "selected_topics" not in st.session_state:
    st.session_state["selected_topics"] = []

if "messages" not in st.session_state:
    st.session_state.messages = []
if "file_path" not in st.session_state:
    st.session_state.file_path = None
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "gemini"


if "notes_text" not in st.session_state:
    st.session_state.notes_text = ""

if page == "Notes":
    st.title("Notesight POC - 📄 Generate Notes")

    uploaded_files = st.file_uploader("Upload Files for Notes Generation", accept_multiple_files=True)

    model_options = {"Gemini": "gemini", "ChatGPT": "chatgpt", "Mistral": "mistral"}
    model = st.selectbox("Select AI Model", list(model_options.values()))

    if uploaded_files and st.button("📝 Generate Notes"):
        files = [("files", (file.name, file, "application/pdf")) for file in uploaded_files]
        response = requests.post(f"{BASE_URL}/notes/", files=files, data={"model": model}, stream=True)

        if response.status_code == 200:
            st.session_state.notes_text = "" 
            notes_placeholder = st.empty()  

            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    decoded_chunk = chunk.decode("utf-8")
                    st.session_state.notes_text += decoded_chunk 
                    notes_placeholder.markdown(st.session_state.notes_text, unsafe_allow_html=True)
            notes_placeholder.empty()
            
        else:
            st.error("❌ Failed to generate notes")

    if st.session_state.notes_text:
        st.subheader("Generated Notes:")
        st.markdown(st.session_state.notes_text,unsafe_allow_html=True)
        pdf_text = st.session_state.notes_text
        pdf_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', pdf_text)
        pdf_text = pdf_text.replace('\n\n', '<br/><br/>').replace('\n', '<br/>')
        pdf_text = pdf_text.replace('<para>', '').replace('</para>', '')
        st.download_button(
            label="📥 Download as Text",
            data=st.session_state.notes_text,
            file_name=f'Generated_notes.txt',
            mime="text/plain"
        )

        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = [Paragraph(pdf_text, styles["Normal"])]
        doc.build(story)
        pdf_buffer.seek(0)

        st.download_button(
            label="📥 Download as PDF",
            data=pdf_buffer,
            file_name=f'Generated_notes.pdf',
            mime="application/pdf"
        )


elif page == "Flashcards":
    st.title("Notesight POC - 📚 Flashcard Generator")
    uploaded_files = st.file_uploader("Upload Files for Flashcards", type=["pdf", "txt", "png", "jpg", "jpeg"], accept_multiple_files=True)
    model_options = {"Gemini": "gemini", "ChatGPT": "chatgpt", "Mistral": "mistral"}
    selected_model = st.selectbox("Select AI Model", list(model_options.keys()))

    if uploaded_files and st.button("🔹 Generate Flashcards"):
        files = [("files", (file.name, file, "application/pdf")) for file in uploaded_files]
        data = {"model": model_options[selected_model]}

        with st.spinner(f"Generating flashcards using {selected_model}... ⏳"):
            response = requests.post(f"{BASE_URL}/flashcards/", files=files, data=data)

            if response.status_code == 200:
                st.session_state.flashcards = response.json().get("flashcards", [])

                if st.session_state.flashcards:
                    st.success(f"✅ Flashcards Generated Using {selected_model}")
                else:
                    st.warning("⚠ No flashcards were generated.")
            else:
                st.error(f"❌ Failed to generate flashcards using {selected_model}")

    if st.session_state.flashcards:
        st.subheader(f"📝 Flashcards (Generated by {selected_model})")
        for flashcard in st.session_state.flashcards:
            with st.expander(f"**{flashcard.get('concept')}**"):
                definition = flashcard.get("definition")
                if "$$" in definition or "\\" in definition: 
                    st.write(r'''{definition}''')
                else:
                    st.write(definition)

elif page == "Chat":
    
    st.title("Notesight POC - Document QA")
    MODEL_OPTIONS = {"Gemini": "gemini", "ChatGPT": "chatgpt"}  
    selected_model = st.selectbox("🤖 Select AI Model", list(MODEL_OPTIONS.keys()), index=list(MODEL_OPTIONS.keys()).index("Gemini"))
    st.session_state.selected_model = MODEL_OPTIONS[selected_model]

    uploaded_file = st.file_uploader("Upload a File")

    if uploaded_file and st.button("📤 Upload File"):
        files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
        data = {"model": st.session_state.selected_model}
        response = requests.post(f"{BASE_URL}/upload/", files=files, data=data)

        if response.status_code == 200:
            st.success("✅ File uploaded successfully!")
            st.session_state.file_path = response.json().get("file_path")
        else:
            st.error(f"❌ Failed to upload file: {response.json().get('detail', 'Unknown error')}")
            st.stop()

    st.subheader("💬 Ask Questions About the Document")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    query = st.chat_input("Ask a question about the document...")
    if query:
        with st.chat_message("user"):
            st.markdown(query)
        st.session_state.messages.append({"role": "user", "content": query})

        response = requests.post(
            f"{BASE_URL}/ask/",
            data={"query": query, "model": st.session_state.selected_model}
        )

        answer = response.json().get("answer", "⚠ No response received.") if response.status_code == 200 else f"❌ Error: {response.json().get('detail', 'Failed to get a response.')}"
        
        with st.chat_message("assistant"):
            st.markdown(answer,unsafe_allow_html=True)

        st.session_state.messages.append({"role": "assistant", "content": answer})

elif page == "MCQ":
    st.title("📘 Notesight POC - Generate MCQs")

    uploaded_files = st.file_uploader("📂 Upload PDFs for MCQ generation",  type=["pdf", "txt", "png", "jpg", "jpeg"], accept_multiple_files=True)
    MODEL_OPTIONS = {"Gemini": "gemini", "ChatGPT": "chatgpt", "Mistral": "mistral"}
    selected_model = st.selectbox("🤖 Select AI Model", list(MODEL_OPTIONS.keys()))
    selected_model_key = MODEL_OPTIONS[selected_model]

    if uploaded_files and st.button("🔍 Extract Topics"):
        files = [("files", (file.name, file, "application/pdf")) for file in uploaded_files]
        with st.spinner(f"Extracting topics {selected_model.capitalize()}... ⏳"):
            response = requests.post(f"{BASE_URL}/mcqs/", files=files, data={"model": selected_model_key})

            if response.status_code == 200:
                st.session_state["topics_hierarchy"] = response.json().get("topics", {})
                st.success("✅ Topics Extracted! Select subtopics below.")
                st.session_state["file_paths"] = response.json().get("file_paths", [])
            else:
                st.error("❌ Failed to extract topics.")

    if "topics_hierarchy" in st.session_state and st.session_state["topics_hierarchy"]:
        st.subheader("📑 Select Subtopics for MCQ Generation")
        selected_subtopics = []

        for chapter, subtopics in st.session_state["topics_hierarchy"].items():
            with st.expander(f"📖 {chapter}"):
                chapter_selected = st.checkbox(f"Select All in {chapter}", key=f"{chapter}_all")
                for subtopic in subtopics:
                    subtopic_selected = st.checkbox(subtopic, key=f"{chapter}_{subtopic}", value=chapter_selected)
                    if subtopic_selected:
                        selected_subtopics.append(subtopic)

        st.session_state["selected_subtopics"] = selected_subtopics

    if "selected_subtopics" in st.session_state and st.session_state["selected_subtopics"] and st.button("🎯 Generate MCQs"):
        with st.spinner(f"Generating MCQs using {selected_model.capitalize()}... ⏳"):
            response = requests.post(
                f"{BASE_URL}/mcqs/generate/",
                json={"topics": st.session_state["selected_subtopics"], "file_paths": st.session_state["file_paths"], "model": selected_model}
            )

        if response.status_code == 200:
            mcqs = response.json()
            if mcqs:
                st.subheader("📚 Generated MCQs")
                for mcq in mcqs:
                    with st.expander(f"📝 {mcq['question']}"):
                        for option in mcq["options"]:
                            st.write(f"{option}")
                        st.success(f"✅ Correct Answer: {mcq['correct_answer']}")
            else:
                st.warning("⚠ No MCQs were generated.")
        else:
            st.error("❌ Failed to generate MCQs. Please try again.")

elif page == "report card":
    def upload_pdf(file):
        """Uploads a PDF to the backend for report generation."""
        files = {"file": file.getvalue()}
        response = requests.post(f"{BASE_URL}/report/", files=files)
        return response.json()

    def get_report(student_id):
        """Fetches a student's report by ID."""
        response = requests.get(f"{BASE_URL}/report/{student_id}")
        return response.json()

    st.title("Student Report Generator")

    
    st.subheader("Upload Student Marks PDF")
    uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
    if uploaded_file and st.button("Generate Report"):
        with st.spinner("Generating report..."):
            result = upload_pdf(uploaded_file)
            st.session_state["report"] = result.get("data", {})

    
    if "report" in st.session_state:
        report = st.session_state["report"]
        st.subheader("Generated Report")

        st.write(f"**Student Name:** {report['student_info']['name']}")
        st.write(f"**Roll Number:** {report['student_info']['roll_number']}")
        st.write(f"**Grade:** {report['student_info']['grade']}")
        st.write(f"**School:** {report['student_info']['school']}")

        st.subheader("Subject Performance")
        for subject, details in report["subject_performance"].items():
            st.write(f"- **{subject}:** {details.get('final_grade', 'N/A')}")

        st.subheader("Strengths")
        st.write(", ".join(report["strengths"]) if report["strengths"] else "No strengths identified.")

        st.subheader("Weaknesses")
        for weakness in report["weaknesses"]:
            st.write(f"- **{weakness['subject']}**: {weakness['reason']}")

        st.subheader("Overall Performance Summary")
        st.write(report["overall_performance_summary"])
