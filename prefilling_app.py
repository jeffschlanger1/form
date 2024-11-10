import streamlit as st
import time
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
import urllib.parse

# Load environment variables
load_dotenv()

# Initialize OpenAI client
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Define the prompts
prompts = [
    """Extract the following fields from the text and provide the output in JSON format:
       - Agency
       - Case #
       - Occurred
       - Location
       - Officer
       - Exact Time
       - Age/Race/Gender
       - Written by""",
    "Please create a summary of report.",
    """Conduct a thorough analysis of the provided police report and BWC transcript, examining officer conduct and adherence to protocol. For each area listed below, provide an objective assessment based on both documents. Identify instances of exemplary behavior and any potential issues, and note any discrepancies between the police report and BWC transcript. Additionally, provide recommendations for continuous improvement based on your findings.

        1. *BWC Activation, Use, and Termination*: Determine if the BWC was activated, used continuously, and terminated appropriately according to policy.
        2. *Pre-Action Planning*: Assess if officers formulated a plan before engaging the subject, and if the plan was coordinated and clear.
        3. *Constitutionality of Initial Contact*: Evaluate the constitutionality of the initial contact...
        4. *Communication with Subject*: Review officers’ communication style, empathy, clarity, and active listening. Note if verbal warnings and advisements were clear and if linguistic barriers impacted communication.
         5. *De-escalation Efforts*: Analyze officers’ efforts to de-escalate the situation. Examine if their language, demeanor, and actions contributed to either reducing or escalating tension.
         6. *Search Constitutionality*: If a search was conducted, evaluate its adherence to constitutional standards, including the presence of probable cause or consent.
         7. *Miranda Warnings*: Verify if Miranda warnings were administered properly when the subject was taken into custody, and if advisement was timely and understandable.
         8. *General Professionalism*: Provide an assessment of the professionalism displayed, including language, demeanor, and respectfulness.
         9. *Tactical Appropriateness*: Assess the tactics used in relation to the situation. Note if they were suitable and prioritized officer and public safety.
         10. *Equipment Issues*: Identify any equipment-related issues that may have impacted the interaction, noting both functionality and failures.
         11. *Policy Revision Needs*: Based on observed issues or gaps, suggest any policy revisions that may improve outcomes in similar situations.
         12. *Adequacy of Documentation*: Evaluate the thoroughness and clarity of the officer’s documentation. Note if relevant details were missing or unclear.
         13. *Supervisory Review Quality*: If a supervisory review occurred, assess its adequacy. Did it address key issues or provide needed recommendations?
         14. *Alternative Approaches*: Suggest alternative approaches that could have potentially led to a more constructive or safer outcome.
         15. *Recommendations for Continuous Improvement*: Summarize recommendations for both individual officer improvement and department-wide adjustments, based on insights from the review.

         For each area, provide specific examples from the BWC transcript (with timestamps) and police report, and highlight any inconsistencies or notable conduct.
         Generate response in simple text not in bullets or points"""
]

def match_radio_option(value):
    radio_button_options = {
        "Aurora Police Department": "Aurora Police Department",
        "Petaluma Police Department": "Petaluma Police Department",
        "San Leandro Police Department": "San Leandro Police Department",
        "DHS-CRCL": "DHS-CRCL",
        "NYAG": "NYAG"
    }
    return radio_button_options.get(value, "")

def generate_prefilled_url(form_url, extracted_data_json, summary, ai_review):
    prefill_data = {
        "entry.1941630927": match_radio_option(extracted_data_json.get("Agency", "")),
        "entry.1124423131": extracted_data_json.get("Case #", ""),
        "entry.185129316": extracted_data_json.get("Occurred", ""),
        "entry.185415823": extracted_data_json.get("Location", ""),
        "entry.961768524": extracted_data_json.get("Exact Time", ""),
        "entry.1406046983": extracted_data_json.get("Officer", ""),
        "entry.1265328535": extracted_data_json.get("Officer", ""),
        "entry.1022627775": extracted_data_json.get("Age/Race/Gender", ""),
        "entry.1382641879": summary,
        "entry.57631527": ai_review  
    }
    return form_url + "?" + urllib.parse.urlencode(prefill_data)

def process_prompt(prompt, uploaded_files):
    chat = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
                "attachments": [
                    {"file_id": client.files.create(file=file, purpose="assistants").id, 
                     "tools": [{"type": "file_search"}]}
                    for file in uploaded_files
                ],
            }
        ]
    )
    run = client.beta.threads.runs.create(thread_id=chat.id, assistant_id=st.secrets["assistant_id"])
    
    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(thread_id=chat.id, run_id=run.id)
        time.sleep(0.5)
        
    message_response = client.beta.threads.messages.list(thread_id=chat.id)
    return message_response.data[0].content[0].text.value if run.status == "completed" else None

def extract_json_content(response_text):
    start_idx = response_text.find("{")
    end_idx = response_text.rfind("}") + 1
    json_part = response_text[start_idx:end_idx]
    return json.loads(json_part)

def main():
    st.title("Document Analysis with Custom GPT")
    st.image("WhatsApp Image 2024-10-23 at 4.47.56 PM.jpeg", use_column_width=True)
    uploaded_files = st.file_uploader(
        "Upload PDF or DOCX files", 
        type=["pdf", "docx"], 
        accept_multiple_files=True
    )
    
    if uploaded_files and st.button("Process"):
        vector_store = client.beta.vector_stores.create(name="Analyst Reports Vector")
        file_streams = [file for file in uploaded_files]
        
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id, files=file_streams
        )
        
        assistant = client.beta.assistants.update(
            # assistant_id=os.getenv("assistant_id"),
            assistant_id=st.secrets["assistant_id"],
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
        )
        
        extracted_data = summary = ai_review = None
        
        for idx, prompt in enumerate(prompts):
            response = process_prompt(prompt, uploaded_files)
            if response:
                if idx == 0:
                    extracted_data = response
                elif idx == 1:
                    summary = response
                elif idx == 2:
                    ai_review = response

        # st.subheader("Responses")
        if extracted_data:
            # st.write("**Extracted Fields**:")
            # st.write(extracted_data)
            extracted_data_json = extract_json_content(extracted_data)
            # case_no = extracted_data_json.get("Case #", "")
            # st.write("Case#", case_no)
        # if summary:
        #     st.write("**Summary**:")
        #     st.write(summary)
        # if ai_review:
        #     st.write("**AI Review**:")
        #     st.write(ai_review)

        # form_url = os.getenv("form_url")
        form_url = st.secrets["form_url"]
        prefilled_url = generate_prefilled_url(form_url, extracted_data_json, summary, ai_review)
        st.subheader("Prefilled Google Form")
        st.markdown(f"""
            <a href="{prefilled_url}" target="_blank" style="text-decoration:none;">
                <button style="
                    background-color: #4CAF50; 
                    color: white; 
                    padding: 10px 20px; 
                    font-size: 16px; 
                    border: none; 
                    border-radius: 5px; 
                    cursor: pointer;">
                    Open Google Form
                </button>
            </a>
            """, unsafe_allow_html=True)
    else:
        st.write("Please upload PDF or DOCX files to proceed and click the 'Process' button.")

if __name__ == "__main__":
    main()