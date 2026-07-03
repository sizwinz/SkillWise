import streamlit as st
import tempfile
import os
import json
import re
import time
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from resume_parser import parse_resume, parse_linkedin_json
from roadmap_generator import generate_roadmap
from goal_analyzer import analyze_goals
import google.generativeai as genai
import plotly.express as px
from datetime import timedelta
from smart_gap_analyzer import get_smart_gap_analysis, SmartGapAnalysisError
import hashlib

ROADMAPS_DB_PATH = os.path.join(os.path.dirname(__file__), "roadmaps_db.json")


def load_roadmaps_db():
    if os.path.exists(ROADMAPS_DB_PATH):
        with open(ROADMAPS_DB_PATH, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def save_roadmaps_db(roadmaps):
    with open(ROADMAPS_DB_PATH, "w") as f:
        json.dump(roadmaps, f, indent=2)

def roadmap_id(resume, goal, role):
    base = (resume.strip() + goal.strip() + role.strip()).encode("utf-8")
    return hashlib.sha256(base).hexdigest()[:16]

# Load skills data from JSON
@st.cache_data
def load_skills_data():
    try:
        with open("skills_data.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Error: skills_data.json not found. Please ensure it's in the same directory as app.py")
        return {}

skills_data = load_skills_data()

def update_progress(progress_bar, eta_placeholder, current_progress, total_stages, start_time, estimated_time, stage_name):
    """Update progress bar with current stage information."""
    progress = (current_progress / total_stages) * 100
    elapsed = time.time() - start_time
    eta = max(0, estimated_time - elapsed)
    progress_bar.progress(int(progress))
    eta_placeholder.text(f"⏳ {stage_name}... {int(progress)}%")

# Robust progress loading and saving
import re

def extract_roadmap_tasks(roadmap_text):
    # Extract checklist tasks from the roadmap text (lines starting with - [ ])
    tasks = []
    for line in roadmap_text.splitlines():
        match = re.match(r"\s*- \[.\] (.+)", line)
        if match:
            tasks.append(match.group(1).strip())
    return tasks

def get_active_roadmap():
    for r in st.session_state.roadmaps_db:
        if r.get("active"):
            return r
    return None

def sync_progress_from_active_roadmap():
    active = get_active_roadmap()
    if active is not None:
        # Ensure progress field exists and matches current roadmap tasks
        roadmap_tasks = extract_roadmap_tasks(active["roadmap"])
        if "progress" not in active or not isinstance(active["progress"], dict):
            active["progress"] = {task: False for task in roadmap_tasks}
        else:
            # Add missing tasks
            for task in roadmap_tasks:
                if task not in active["progress"]:
                    active["progress"][task] = False
            # Remove tasks not in roadmap
            for task in list(active["progress"].keys()):
                if task not in roadmap_tasks:
                    del active["progress"][task]
        st.session_state.progress = dict(active["progress"])
    else:
        st.session_state.progress = {}

def save_progress_to_active_roadmap():
    active = get_active_roadmap()
    if active is not None:
        active["progress"] = dict(st.session_state.progress)
        save_roadmaps_db(st.session_state.roadmaps_db)

# Configure Streamlit page
st.set_page_config(page_title="SkillWise", page_icon="💡", layout="wide", initial_sidebar_state="expanded")

# Load external CSS
with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Additional custom styles
st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">', unsafe_allow_html=True)


# Initialize session state
if "roadmap" not in st.session_state:
    st.session_state.roadmap = ""
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "parsed_resume" not in st.session_state:
    st.session_state.parsed_resume = None
if "goal" not in st.session_state:
    st.session_state.goal = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "custom_role" not in st.session_state:
    st.session_state.custom_role = ""
if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
if "progress" not in st.session_state:
    st.session_state.progress = {}

if "generation_time" not in st.session_state:
    st.session_state.generation_time = 10.0
if "first_visit" not in st.session_state:
    st.session_state.first_visit = True
if "survey_submitted" not in st.session_state:
    st.session_state.survey_submitted = False
if "survey_submitted" not in st.session_state:
    st.session_state.survey_submitted = False
if "resume_upload_time" not in st.session_state:
    st.session_state.resume_upload_time = 5.0
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

# Onboarding Walkthrough for first-time users
if st.session_state.first_visit:
    st.info("""
    ### Welcome to SkillWise! 🎉
    Follow these steps to get started:
    1. **Enter your Gemini API Key** in the sidebar (⚙️ Configuration).
    2. **Upload your resume** in the Resume tab (📄 Upload Your Resume).
    3. **Select your career goal and role** (e.g., AI Engineer).
    4. Click **Generate Roadmap** to create your personalized learning path.
    5. Explore your roadmap in the Roadmap tab (🗺️).
    """)
    st.session_state.first_visit = False

# Handle Gemini API key with Submit button and Change option
with st.sidebar:
    st.header("⚙️ Configuration")
    if not st.session_state.gemini_api_key:
        st.warning("⚠️ Gemini API key not found. Please enter it below.")
        api_key_input = st.text_input("Enter Gemini API Key", type="password")
        if st.button("Submit"):
            if api_key_input:
                st.session_state.gemini_api_key = api_key_input
                genai.configure(api_key=api_key_input)
                st.success("✅ API Key submitted!")
            else:
                st.error("❌ Please enter a valid API key.")
    else:
        st.success("✅ API Key is set!")
        if st.button("🔄 Change API Key"):
            st.session_state.gemini_api_key = ""
            st.rerun()
        


st.markdown("""
    <div style="text-align: center; padding: 2rem 0; margin-bottom: 2rem;">
        <h1 style="font-size: 3.5rem; background: linear-gradient(to right, #6366f1, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem; font-family: 'Outfit', sans-serif; font-weight: 700;">SkillWise</h1>
        <p style="font-size: 1.2rem; color: #94a3b8; font-family: 'Inter', sans-serif;">AI-Powered Learning Path Generator</p>
    </div>
""", unsafe_allow_html=True)

# Tabs
tab1, tab2 = st.tabs(["Resume", "Roadmap"])

# Resume Tab
with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("🎯 Select Career Goal")
        st.session_state.goal = st.text_input("What role are you targeting?", placeholder="e.g., AI Developer, Product Manager", value=st.session_state.goal)
        if st.session_state.goal.strip():
            goal_analysis = analyze_goals(st.session_state.goal)
            # Check for the specific NLTK error message
            if "Error analyzing goal" in goal_analysis:
                st.warning("⚠️ There was an issue analyzing your goal. Please ensure NLTK data is correctly set up or try a different goal.")
            else:
                pass

    with col2:
        st.subheader("📚 Select Tech Role")
        roles = [
            "Select a tech role",
            "AI Engineer",
            "Frontend Developer",
            "Backend Developer",
            "Full Stack Developer",
            "Product Manager",
            "Data Analyst",
            "Cybersecurity Expert",
            "DevOps Engineer",
            "UI/UX Designer",
            "Machine Learning Engineer",
            "Blockchain Developer",
            "Cloud Architect",
            "Data Scientist",
            "Software Engineer",
            "Mobile App Developer",
            "Other"
        ]
        st.session_state.role = st.selectbox("Choose a role", roles, index=roles.index(st.session_state.role) if st.session_state.role in roles else 0)
        if st.session_state.role == "Other":
            st.session_state.custom_role = st.text_input("Please specify your role", placeholder="e.g., Game Developer", value=st.session_state.custom_role)
    
    effective_role = st.session_state.custom_role if st.session_state.role == "Other" and st.session_state.custom_role else st.session_state.role
    st.subheader("📄 Upload Your Resume")
    uploaded_file = st.file_uploader("Upload your resume (PDF or LinkedIn JSON)", type=["pdf", "json"])
    
    if uploaded_file is not None and not st.session_state.is_processing:
        st.session_state.is_processing = True
        status_container = st.empty()
        progress_bar = status_container.progress(0)
        eta_placeholder = status_container.empty()
        start_time = time.time()
        tmp_path = None # Initialize tmp_path to ensure it's always defined for finally block

        try:
            file_type = uploaded_file.type
            update_progress(progress_bar, eta_placeholder, 0, 100, start_time, st.session_state.resume_upload_time, "Processing Resume")

            parsed_text = ""
            if file_type == "application/pdf":
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_path = tmp_file.name
                update_progress(progress_bar, eta_placeholder, 50, 100, start_time, st.session_state.resume_upload_time, "Parsing PDF")
                parsed_text = parse_resume(tmp_path)
            elif file_type == "application/json":
                update_progress(progress_bar, eta_placeholder, 50, 100, start_time, st.session_state.resume_upload_time, "Parsing JSON")
                json_data = json.load(uploaded_file)
                parsed_text = parse_linkedin_json(json_data)
            
            if len(parsed_text.strip()) > 20:
                st.session_state.parsed_resume = parsed_text
                st.session_state.resume_text = parsed_text
                status_container.success("✅ Resume processed successfully!")
            else:
                status_container.error("⚠️ Failed to extract meaningful content. Try another file or format.")
                
        except Exception as e:
            status_container.error(f"❌ Error processing resume: {str(e)}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception as e:
                    print(f"Error removing temp file: {e}") # Log error, don't crash
            status_container.empty()
            st.session_state.is_processing = False
            
            total_time = time.time() - start_time
            st.session_state.resume_upload_time = total_time

    if st.button("🚀 Generate Roadmap") and not st.session_state.is_processing:
        if not st.session_state.parsed_resume:
            st.warning("⚠️ Please upload a resume.")
        elif effective_role == "Select a tech role":
            st.warning("⚠️ Please select a valid role.")
        elif st.session_state.role == "Other" and not st.session_state.custom_role.strip():
            st.warning("⚠️ Please specify a role in the text field.")
        elif not st.session_state.gemini_api_key:
            st.error("❌ Please enter a Gemini API key in the sidebar.")
        else:
            # --- Persistent Roadmap Management Integration ---
            new_id = roadmap_id(st.session_state.resume_text, st.session_state.goal, effective_role)
            found = None
            for r in st.session_state.roadmaps_db:
                if r["id"] == new_id:
                    found = r
                    break
            if found:
                # Load existing
                for rr in st.session_state.roadmaps_db:
                    rr["active"] = (rr["id"] == found["id"])
                    if rr["active"]:
                        rr["last_accessed"] = datetime.now().isoformat()
                save_roadmaps_db(st.session_state.roadmaps_db)
                st.session_state.resume_text = found["resume"]
                st.session_state.goal = found["goal"]
                st.session_state.role = found["role"]
                st.session_state.roadmap = found["roadmap"]
                # Reset progress for loaded roadmap
                roadmap_tasks = extract_roadmap_tasks(st.session_state.roadmap)
                st.session_state.progress = {task: False for task in roadmap_tasks}
                save_progress_to_active_roadmap()
                st.success("Loaded existing roadmap for this resume/goal/role. Check it in the Roadmap tab.")
                st.rerun()
            else:
                st.session_state.is_processing = True
                processing_status_container = st.empty()
                prompt = (
                    f"Resume Text:\n{st.session_state.resume_text}\n\n"
                    f"Target Role: {effective_role}\n"
                    f"Career Goal: {st.session_state.goal}\n\n"
                    "Generate a personalized 6-month learning roadmap. Focus on free or low-cost resources. "
                    "Include specific course suggestions (if possible, from platforms like Coursera, edX, YouTube), "
                    "project ideas to build a portfolio, and a general career plan or phases. "
                    "The roadmap should be structured with clear phases, modules, and actionable tasks. "
                    "Indicate estimated durations for tasks or modules (e.g., in weeks or days)."
                )
                with processing_status_container.container():
                    progress_bar = st.progress(0)
                    eta_placeholder = st.empty()
                start_time = time.time()
                error_occurred = False
                try:
                    genai.configure(api_key=st.session_state.gemini_api_key)
                    estimated_duration = st.session_state.generation_time
                    steps = 50
                    for i in range(steps):
                        progress_val = int((i / steps) * 90)
                        update_progress(progress_bar, eta_placeholder, progress_val, 100, start_time, estimated_duration, "Generating Roadmap")
                        time.sleep(estimated_duration / (steps * 10))
                    st.session_state.roadmap = generate_roadmap(prompt)
                    # Reset progress for new roadmap
                    roadmap_tasks = extract_roadmap_tasks(st.session_state.roadmap)
                    st.session_state.progress = {task: False for task in roadmap_tasks}
                    save_progress_to_active_roadmap()
                    update_progress(progress_bar, eta_placeholder, 100, 100, start_time, estimated_duration, "Complete")
                    actual_time = time.time() - start_time
                    st.session_state.generation_time = actual_time
                    processing_status_container.success("✅ Roadmap generated! Check it in the Roadmap tab.")
                    # Save new roadmap to DB
                    new_roadmap = {
                        "id": new_id,
                        "resume": st.session_state.resume_text,
                        "goal": st.session_state.goal,
                        "role": effective_role,
                        "roadmap": st.session_state.roadmap,
                        "timestamp": datetime.now().isoformat(),
                        "last_accessed": datetime.now().isoformat(),
                        "active": True
                    }
                    for rr in st.session_state.roadmaps_db:
                        rr["active"] = False
                    st.session_state.roadmaps_db.insert(0, new_roadmap)
                    save_roadmaps_db(st.session_state.roadmaps_db)
                    st.success("New roadmap saved and set as active. Check it in the Roadmap tab.")
                    st.rerun()
                except Exception as e:
                    error_occurred = True
                    processing_status_container.error(f"❌ Error generating roadmap: {str(e)}")
                finally:
                    st.session_state.is_processing = False

    st.markdown("---")
    # Job Role Simulator Expander
    with st.expander("🎯 Job Role Simulator (Optional)", expanded=False):
        st.subheader("Simulate Your Fit for a Specific Job")
        jd_text_input = st.text_area("Paste Job Description Text Here:", height=200, key="jd_text_input",
                                     help="Paste the full text of the job description you are interested in.")


        if st.button("🚀 Analyze Fit & Generate Focused Roadmap", key="analyze_jd_button"):
            if not st.session_state.parsed_resume:
                st.warning("⚠️ Please upload your resume first before analyzing a job description.")
            elif not jd_text_input.strip(): # and not jd_url_input.strip()
                st.warning("⚠️ Please paste the job description text.") # or provide a URL
            elif not st.session_state.gemini_api_key:
                st.error("❌ Please enter a Gemini API key in the sidebar.")
            else:
                job_description_content = jd_text_input.strip()


                if job_description_content:
                    st.session_state.is_processing_jd = True # New state variable for JD processing
                    jd_status_container = st.empty()

                    with jd_status_container.container():
                        st.subheader("🔍 Job Fit Analysis:")
                        with st.spinner("Analyzing your resume against the job description..."):
                            try:
                                fit_analysis_prompt = (
                                    f"My resume is:\n---\n{st.session_state.resume_text}\n---\n\n"
                                    f"The job description is:\n---\n{job_description_content}\n---\n\n"
                                    "Please provide a concise analysis of how well my resume matches this specific job description. "
                                    "Highlight key strengths and specific gaps or missing qualifications relevant to this job. "
                                    "Conclude with a percentage fit score (e.g., Fit Score: 75%)."
                                )
                                model = genai.GenerativeModel("gemini-2.0-flash") # Ensure model is configured
                                response_fit = model.generate_content(fit_analysis_prompt)
                                st.session_state.job_fit_analysis = response_fit.text.strip()
                                st.markdown(st.session_state.job_fit_analysis)
                            except Exception as e:
                                st.error(f"Error during Job Fit Analysis: {e}")
                                st.session_state.job_fit_analysis = None

                        if st.session_state.job_fit_analysis:
                            st.subheader("🗺️ Generating Focused Roadmap for this Job:")
                            with st.spinner("Generating a new roadmap focused on this job's requirements..."):
                                try:
                                    focused_roadmap_prompt = (
                                        f"My resume is:\n---\n{st.session_state.resume_text}\n---\n\n"
                                        f"The target job description is:\n---\n{job_description_content}\n---\n\n"
                                        f"My previous general career goal was '{st.session_state.goal}' for the role of '{effective_role}'.\n\n"
                                        "Now, generate a highly focused 6-month learning roadmap to specifically address the gaps and requirements for THIS job description. "
                                        "Prioritize skills and experiences mentioned in the job description. "
                                        "Suggest concrete learning steps, resources (like specific types of courses or projects), and how they help bridge the gap for this particular job. "
                                        "The output should be a structured roadmap."
                                    )
                                    # We can reuse the existing roadmap_generator.py function
                                    focused_roadmap = generate_roadmap(focused_roadmap_prompt)
                                    st.session_state.focused_jd_roadmap = focused_roadmap

                                    # Option: Update main roadmap or show separately
                                    # For now, let's update the main roadmap and notify the user
                                    st.session_state.roadmap = focused_roadmap
                                    st.success("✅ Focused roadmap generated and updated in the 'Roadmap' tab!")
                                    # Also clear any previous smart gap analysis as the roadmap context has changed
                                    if "smart_gap_analysis_result" in st.session_state:
                                        del st.session_state.smart_gap_analysis_result
                                    st.rerun() # Rerun to refresh the roadmap tab
                                except Exception as e:
                                    st.error(f"Error generating focused roadmap: {e}")
                                    st.session_state.focused_jd_roadmap = None
                    st.session_state.is_processing_jd = False
                elif not jd_text_input.strip():
                     st.warning("Please paste the job description text.")


# Roadmap Tab
with tab2:
    if st.session_state.roadmap:
        st.header("🗺️ Your AI-Powered Learning Roadmap")
        
        required_skills = {}
        default_skills = []
        expanded_skill_terms = {}
        course_recommendations = {}
        skills_to_check = [] # Initialize to an empty list

        if isinstance(skills_data, dict) and skills_data:
            required_skills = skills_data.get("required_skills", {})
            default_skills = skills_data.get("default_skills", [])
            expanded_skill_terms = skills_data.get("expanded_skill_terms", {})
            course_recommendations = skills_data.get("course_recommendations", {})

            skills_to_check = required_skills.get(effective_role, default_skills)
        else:
            st.warning("⚠️ Skill data could not be loaded. Please check 'skills_data.json'.")

        # Smart AI Gap Detector
        st.subheader("🤖 Smart AI Gap Analysis")
        if st.session_state.resume_text and effective_role != "Select a tech role":
            if "smart_gap_analysis_result" not in st.session_state or \
               st.session_state.get("smart_gap_analysis_role") != effective_role or \
               st.session_state.get("smart_gap_analysis_resume") != st.session_state.resume_text:

                # Button to trigger analysis to avoid running on every rerun if not needed
                if st.button("🔬 Analyze My Skills with AI", key="run_smart_analysis"):
                    with st.spinner("Performing Smart AI Gap Analysis... This may take a moment."):
                        try:
                            analysis_result = get_smart_gap_analysis(
                                st.session_state.resume_text,
                                effective_role,
                                st.session_state.goal
                            )
                            st.session_state.smart_gap_analysis_result = analysis_result
                            st.session_state.smart_gap_analysis_role = effective_role # Cache the role for which analysis was run
                            st.session_state.smart_gap_analysis_resume = st.session_state.resume_text # Cache resume
                            st.markdown(st.session_state.smart_gap_analysis_result)
                        except SmartGapAnalysisError as e:
                            st.error(f"Smart AI Gap Analysis Error: {e}")
                            st.session_state.smart_gap_analysis_result = None # Clear previous results on error
                        except Exception as e:
                            st.error(f"An unexpected error occurred during analysis: {e}")
                            st.session_state.smart_gap_analysis_result = None
                elif "smart_gap_analysis_result" in st.session_state and st.session_state.smart_gap_analysis_result:
                     st.markdown(st.session_state.smart_gap_analysis_result) # Show cached result
                else:
                    st.info("Click the button above to perform an AI-powered skill gap analysis for your selected role and uploaded resume.")

            elif st.session_state.smart_gap_analysis_result: # Result is cached and inputs match
                st.markdown(st.session_state.smart_gap_analysis_result)
            else: # Should not happen if logic is correct, but as a fallback
                st.info("Click 'Analyze My Skills with AI' to get your smart gap analysis.")
        else:
            st.warning("Please upload a resume and select a target role to enable Smart AI Gap Analysis.")

        st.markdown("---")

        # Old keyword-based analysis (can be kept for comparison or removed)
        # For now, I'll comment it out to prioritize the new AI analysis.
        # if skills_to_check:
        #     resume_text_lower = st.session_state.resume_text.lower()
        #     matched_conceptual_skills = []
        #     for conceptual_skill in skills_to_check:
        #         aliases = expanded_skill_terms.get(conceptual_skill, [conceptual_skill])
        #         if any(alias.lower() in resume_text_lower for alias in aliases):
        #             matched_conceptual_skills.append(conceptual_skill)
        #
        #     skill_match_score = (len(matched_conceptual_skills) / len(skills_to_check)) * 100 if skills_to_check else 0
        #     st.subheader("📊 Keyword-Based Skill Match Score")
        #     st.markdown(f"Your skills match {skill_match_score:.1f}% of the keyword requirements for {effective_role}.")
        #
        #     st.subheader("🔍 Keyword-Based Skill Gap Analysis")
        #     missing_conceptual_skills = [skill for skill in skills_to_check if skill not in matched_conceptual_skills]
        #
        #     if missing_conceptual_skills:
        #         st.markdown(f"Skills missing (keywords): {', '.join(missing_conceptual_skills)}")
        #         st.subheader("📚 Recommended Courses for Skill Gaps (Keyword-Based)")
        #         for skill in missing_conceptual_skills:
        #             if skill in course_recommendations:
        #                 st.markdown(f"- **{skill}**: {course_recommendations[skill]}")
        #             else:
        #                 st.markdown(f"- **{skill}**: No specific course recommendation available. Try searching on Coursera or Udemy.")
        #     else:
        #         st.markdown("✅ Your resume covers all key skills for this role based on keywords!")
        # st.markdown("---")

        # Visual Timeline (Gantt Chart)
        st.subheader("🗓️ Visual Timeline (6 Months)")

        def parse_duration(duration_str):
            """Parses duration like '(1 week)', '(3 days)' into timedelta."""
            if not duration_str:
                return timedelta(weeks=1) # Default duration
            match = re.search(r'\((\d+)\s*(week|day)s?\)', duration_str, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                unit = match.group(2).lower()
                if unit == "week":
                    return timedelta(weeks=value)
                elif unit == "day":
                    return timedelta(days=value)
            return timedelta(weeks=1) # Default if parsing fails

        roadmap_tasks_for_gantt = []
        current_date = datetime.now()
        overall_start_date = current_date

        roadmap_lines = st.session_state.roadmap.splitlines()
        current_phase_gantt = "General"
        current_module_gantt = "General"

        for line_idx, line_content in enumerate(roadmap_lines):
            line_content = line_content.strip()
            if not line_content:
                continue

            task_name = ""
            task_type = "Task" # Phase, Module, Task
            duration_text = ""

            if line_content.startswith("##"): # Phase
                task_name = line_content[2:].strip()
                # Try to extract duration from phase title, e.g., "## Phase 1: Foundations (Weeks 1-4)"
                duration_match = re.search(r'\(Weeks (\d+)-(\d+)\)', task_name, re.IGNORECASE)
                if duration_match:
                    start_week = int(duration_match.group(1))
                    end_week = int(duration_match.group(2))
                    duration = timedelta(weeks=(end_week - start_week + 1))
                    task_name = re.sub(r'\s*\(Weeks \d+-\d+\)', '', task_name).strip() # Clean task name
                else:
                    duration = timedelta(weeks=4) # Default phase duration
                current_phase_gantt = task_name
                task_type = "Phase"
            elif line_content.startswith("**") and line_content.endswith("**"): # Module
                task_name = line_content[2:-2].strip()
                duration = timedelta(weeks=2) # Default module duration, sum of sub-tasks later if possible
                current_module_gantt = task_name
                task_type = "Module"
            elif line_content.startswith("*"): # Task
                task_name = line_content[1:].strip()
                duration_match = re.search(r'(\(.*\))', task_name)
                if duration_match:
                    duration_text = duration_match.group(1)
                    task_name = task_name.replace(duration_text, "").strip()
                duration = parse_duration(duration_text)
                task_type = "Task"

            if task_name:
                # Key for progress tracking should match the one used in checkboxes
                # For phases/modules, we don't have checkboxes yet, so make a unique key
                if task_type == "Phase":
                    progress_key = f"phase_{task_name}"
                elif task_type == "Module":
                    progress_key = f"{current_phase_gantt}_{task_name}"
                else: # Task
                    # This needs to match the checkbox key logic: f"{current_section}_{content_line}"
                    # We need to reconstruct `current_section` as it was when checkboxes were made.
                    # This is tricky. For now, let's assume module name is a good proxy for section for tasks.
                    progress_key = f"{current_module_gantt}_{line_content}"


                completed_status = st.session_state.progress.get(progress_key, False)

                roadmap_tasks_for_gantt.append(dict(
                    Task=task_name,
                    Start=current_date.strftime("%Y-%m-%d"),
                    Finish=(current_date + duration).strftime("%Y-%m-%d"),
                    Resource=current_phase_gantt if task_type != "Phase" else "Project Phases", # Group by phase
                    Status="Completed" if completed_status else "Pending",
                    Type=task_type
                ))
                if task_type != "Phase": # Only advance date for modules and tasks within a phase
                    current_date += duration

        if roadmap_tasks_for_gantt:
            # Ensure overall timeline doesn't exceed ~6 months from the first task for display scaling
            # This is a rough cap for visualization if total duration is very long.
            # More sophisticated would be to scale durations proportionally if they exceed 6 months.

            # Create a DataFrame
            import pandas as pd
            df_gantt = pd.DataFrame(roadmap_tasks_for_gantt)
            df_gantt['Start'] = pd.to_datetime(df_gantt['Start'])
            df_gantt['Finish'] = pd.to_datetime(df_gantt['Finish'])

            # Cap end dates at 6 months from the start of the first task for visualization
            # overall_project_end_date = df_gantt['Start'].min() + timedelta(days=180)
            # df_gantt['Finish'] = df_gantt['Finish'].apply(lambda x: min(x, overall_project_end_date))


            fig_gantt = px.timeline(
                df_gantt,
                x_start="Start",
                x_end="Finish",
                y="Task",
                color="Status",
                title="Project Timeline",
                hover_name="Task",
                color_discrete_map={"Completed": "#10b981", "Pending": "#f59e0b", "Overdue": "#ef4444"}, 
                category_orders={"Task": df_gantt.sort_values(by="Start")["Task"].tolist()} # Preserve order
            )
            fig_gantt.update_yaxes(autorange="reversed") # To display tasks from top to bottom
            fig_gantt.update_layout(
                title_font_size=20,
                font_size=12,
                plot_bgcolor='rgba(15, 23, 42, 0.4)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font_color="#f8fafc",
                legend_title_text='Task Status',
                font_family="Inter"
            )
            st.plotly_chart(fig_gantt, use_container_width=True)

            # "Mark Complete" and "Remind Me" buttons for tasks shown in Gantt
            st.markdown("---")
            st.subheader("Timeline Task Actions")
            selected_gantt_task_name = st.selectbox(
                "Select a task from timeline to manage:",
                options=[t['Task'] for t in roadmap_tasks_for_gantt if t['Type'] == 'Task'] # Only individual tasks
            )

            if selected_gantt_task_name:
                # Find the original line content for the selected task to build the correct progress_key
                original_line_for_selected_task = ""
                # This is a simplification: assuming task names are unique enough for this demo
                # A more robust solution would involve storing unique IDs for each task during parsing.
                for r_line in roadmap_lines:
                    if selected_gantt_task_name in r_line and r_line.strip().startswith("*"):
                        original_line_for_selected_task = r_line.strip()
                        break

                # Reconstruct progress key (needs to be robust)
                # This is still a bit fragile. Finding the exact section header for the task is key.
                # For now, we'll try to find the module it belongs to.
                _current_module_for_key = "General" # default
                for task_info in roadmap_tasks_for_gantt:
                    if task_info["Task"] == selected_gantt_task_name:
                        # Find its module by looking at previous items or its resource
                        for r_task in reversed(roadmap_tasks_for_gantt[:roadmap_tasks_for_gantt.index(task_info)]):
                            if r_task["Type"] == "Module":
                                _current_module_for_key = r_task["Task"]
                                break
                        break

                # The progress key for a checkbox is `f"{current_section}_{content_line}"`
                # where current_section is the module name (e.g. "Module 1.1: Introduction to X")
                # and content_line is the task line (e.g. "* Learn basic syntax (1 week)")
                # This part is the most complex to get right with current parsing.
                # The Gantt task name is cleaned, but the progress key uses the raw line.

                # Let's try to find the progress key more directly if possible
                # This requires matching the cleaned task name back to its original form + section
                target_progress_key = None
                for key_iter, val_iter in st.session_state.progress.items():
                    # Progress keys are like "Section Name_* Task Name (duration)"
                    if selected_gantt_task_name in key_iter and key_iter.endswith(original_line_for_selected_task):
                        target_progress_key = key_iter
                        break
                # Fallback if exact match not found (e.g. due to name cleaning)
                if not target_progress_key and original_line_for_selected_task:
                     # Attempt to find a key that contains the task name and its original line structure
                    for key_iter, val_iter in st.session_state.progress.items():
                        if selected_gantt_task_name in key_iter and original_line_for_selected_task.split('(')[0].strip() in key_iter :
                             target_progress_key = key_iter
                             break

                if not target_progress_key and original_line_for_selected_task:
                    # Last resort: construct based on identified module and original line
                    # This relies on _current_module_for_key being accurately identified for the task
                    target_progress_key = f"{_current_module_for_key}_{original_line_for_selected_task}"


                col_gantt_action1, col_gantt_action2 = st.columns(2)
                with col_gantt_action1:
                    if target_progress_key and target_progress_key in st.session_state.progress:
                        current_status = st.session_state.progress[target_progress_key]
                        button_label = "Mark as Pending" if current_status else "Mark as Complete"
                        if st.button(button_label, key=f"gantt_toggle_{selected_gantt_task_name}"):
                            st.session_state.progress[target_progress_key] = not current_status
                            save_progress_to_active_roadmap()
                            st.success(f"Task '{selected_gantt_task_name}' status updated.")
                            st.rerun() # To update Gantt chart color
                    else:
                        st.warning(f"Could not reliably link '{selected_gantt_task_name}' to progress tracker. Progress key: {target_progress_key}")


        else:
            st.info("No tasks found in the roadmap to display on the timeline.")

        st.markdown("---") # Separator before the old progress tracker

        st.subheader("📈 Progress Tracker (Checklist)")
        sync_progress_from_active_roadmap()

        # Re-parse roadmap for checklist section, ensuring keys are consistent.
        # The key challenge is that Gantt parsing might differ slightly from checklist parsing.
        # The `current_section` for checklist items is typically the module header.

        checklist_roadmap_lines = st.session_state.roadmap.splitlines()
        checklist_current_section = None # This is usually the module name like "**Module 1.1**"
        checklist_section_content = []

        # Logic for displaying checkboxes (similar to original)
        # This section needs to be careful about how `current_section` is defined for tasks
        # to match the keys used by Gantt chart actions if possible.

        temp_current_section_for_checklist = "Unknown Section" # Default if no section found

        for i, line in enumerate(checklist_roadmap_lines):
            line = line.strip()
            if not line:
                continue

            is_section_header = line.startswith("**") and line.endswith("**")
            is_phase_header = line.startswith("##")

            if is_phase_header: # A phase header also resets the section for checklist
                if checklist_current_section and checklist_section_content: # Process previous section
                    st.markdown(f"### {checklist_current_section}") # Use H3 for modules in checklist
                    # Edit button logic can remain similar if needed for these sections
                    # if st.button("Edit Section", key=f"edit_checklist_{temp_current_section_for_checklist.replace(' ','_')}"):
                    #    st.session_state.editing_section = ... (needs careful index mapping)
                    for content_line_idx, content_line in enumerate(checklist_section_content):
                        if content_line.startswith("*"):
                            item_key = f"{checklist_current_section}_{content_line}"
                            if item_key not in st.session_state.progress:
                                st.session_state.progress[item_key] = False
                            completed = st.checkbox(
                                f"{content_line[1:]}",
                                value=st.session_state.progress[item_key],
                                key=f"check_{checklist_current_section}_{i}_{content_line_idx}" # Ensure unique key
                            )
                            if completed != st.session_state.progress[item_key]:
                                st.session_state.progress[item_key] = completed
                                save_progress_to_active_roadmap()
                                st.rerun() # To update Gantt chart potentially
                        else:
                            st.markdown(content_line) # Non-task lines within a section

                st.markdown(f"## {line[2:].strip()}") # Display Phase Name
                checklist_current_section = None # Reset current module/section under this phase
                checklist_section_content = []
                temp_current_section_for_checklist = line[2:].strip() # For context if no module follows

            elif is_section_header: # This is a Module
                if checklist_current_section and checklist_section_content: # Process previous module's content
                    st.markdown(f"### {checklist_current_section}")
                    for content_line_idx, content_line in enumerate(checklist_section_content):
                        if content_line.startswith("*"):
                            item_key = f"{checklist_current_section}_{content_line}"
                            # ... (checkbox logic as above) ...
                            if item_key not in st.session_state.progress:
                                st.session_state.progress[item_key] = False
                            completed = st.checkbox(
                                f"{content_line[1:]}",
                                value=st.session_state.progress[item_key],
                                key=f"check_{checklist_current_section}_{i}_{content_line_idx}"
                            )
                            if completed != st.session_state.progress[item_key]:
                                st.session_state.progress[item_key] = completed
                                save_progress_to_active_roadmap()
                                st.rerun()
                        else:
                            st.markdown(content_line)

                checklist_current_section = line[2:-2].strip() # New module name
                checklist_section_content = []
                # No st.markdown(f"### {checklist_current_section}") here, done when section is processed or new one starts

            elif checklist_current_section: # This line is content for the current module
                checklist_section_content.append(line)
            elif temp_current_section_for_checklist and not is_phase_header and not is_section_header : # Content under a phase but not in a module yet
                 # This case might be rare if roadmap structure is Phase > Module > Task
                 # For now, treat as part of the phase or a general section
                if not checklist_section_content : st.markdown(f"### Tasks for {temp_current_section_for_checklist}")
                checklist_section_content.append(line)
                if checklist_current_section is None: checklist_current_section = temp_current_section_for_checklist # Assign phase as section if no module


        # Process the last section
        if checklist_current_section and checklist_section_content:
            st.markdown(f"### {checklist_current_section}")
            # Edit button for last section
            # if st.button("Edit Section", key=f"edit_checklist_last_{checklist_current_section.replace(' ','_')}"):
            #    st.session_state.editing_section = ...
            for content_line_idx, content_line in enumerate(checklist_section_content):
                if content_line.startswith("*"):
                    item_key = f"{checklist_current_section}_{content_line}"
                    if item_key not in st.session_state.progress:
                        st.session_state.progress[item_key] = False
                    completed = st.checkbox(
                        f"{content_line[1:]}",
                        value=st.session_state.progress[item_key],
                        key=f"check_last_{checklist_current_section}_{content_line_idx}" # Unique key for last items
                    )
                    if completed != st.session_state.progress[item_key]:
                        st.session_state.progress[item_key] = completed
                        save_progress_to_active_roadmap()
                        st.rerun()
                else:
                    st.markdown(content_line)

        # Fallback for content that might not be under any section (should be rare)
        elif not checklist_current_section and checklist_section_content:
             st.markdown(f"### Other Items")
             for content_line_idx, content_line in enumerate(checklist_section_content):
                if content_line.startswith("*"):
                    # Simplified key if no section
                    item_key = f"general_{content_line}"
                    if item_key not in st.session_state.progress:
                        st.session_state.progress[item_key] = False
                    completed = st.checkbox(
                        f"{content_line[1:]}",
                        value=st.session_state.progress[item_key],
                        key=f"check_other_{content_line_idx}"
                    )
                    if completed != st.session_state.progress[item_key]:
                        st.session_state.progress[item_key] = completed
                        save_progress_to_active_roadmap()
                        st.rerun()
                else:
                    st.markdown(content_line)



        st.subheader("❓ Ask About Your Roadmap")
        question = st.text_input("Enter your question (e.g., 'How long will SQL take?')")
        if st.button("Get Answer"):
            if question:
                if not st.session_state.gemini_api_key:
                    st.error("❌ Please enter a Gemini API key in the sidebar.")
                else:
                    try:
                        with st.spinner("Fetching answer..."):
                            genai.configure(api_key=st.session_state.gemini_api_key)
                            model = genai.GenerativeModel("gemini-1.5-flash")
                            response = model.generate_content(f"Roadmap: {st.session_state.roadmap}\nQuestion: {question}")
                            st.markdown(response.text)
                    except Exception as e:
                        st.error(f"❌ Error fetching answer: {e}")
            else:
                st.warning("⚠️ Please enter a question.")

        st.subheader("📥 Export Your Roadmap")
        st.download_button(
            label="📄 Download as TXT",
            data=st.session_state.roadmap,
            file_name="SkillWise_Roadmap.txt",
            mime="text/plain"
        )
        # PDF export with fixed formatting
        def clean_text(text):
            # First, handle special characters
            replacements = {
                "–": "-",  # En dash to hyphen
                "—": "-",  # Em dash to hyphen
                "’": "'",  # Right single quote to straight quote
                "‘": "'",  # Left single quote to straight quote
                """: '"',  # Left double quote to straight quote
                """: '"',  # Right double quote to straight quote
                "*": "",  # Remove residual Markdown stars
            }
            for unicode_char, ascii_char in replacements.items():
                text = text.replace(unicode_char, ascii_char)
            
            # Then, handle bullet points and formatting
            text = text.replace(". ", "- ")  # Standardize bullet points
            text = text.replace("•", "-")    # Convert bullet points to hyphens
            text = text.replace("◦", "-")    # Convert sub-bullets to hyphens
            
            # Convert hyphens to colons for better readability
            text = text.replace(" - ", ": ")
            text = text.replace(" -", ": ")
            
            # Clean up any double spaces
            text = " ".join(text.split())
            
            return text.encode("ascii", "ignore").decode("ascii")

        def generate_pdf():
            from io import BytesIO
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter

            # Enhanced margins and spacing
            left_margin = 1 * inch
            right_margin = 1 * inch
            top_margin = 1 * inch
            bottom_margin = 0.75 * inch
            content_width = width - left_margin - right_margin

            # Enhanced color scheme
            primary_color = HexColor("#4a69bd")    # Main blue
            accent_color = HexColor("#60a5fa")     # Light blue
            text_color = HexColor("#2d2d44")       # Dark gray
            highlight_color = HexColor("#e0e0e0")  # Light gray
            phase_color = HexColor("#1a1a2e")      # Dark blue for phases

            def draw_header():
                # Draw logo with enhanced positioning
                try:
                    logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "logo.png"))
                    logo_width = 1.5 * inch
                    logo_height = 0.5 * inch
                    logo_x = left_margin
                    logo_y = height - 0.7 * inch
                    c.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height, preserveAspectRatio=True)
                except Exception as e:
                    # If logo is missing, skip drawing it and print the attempted path
                    print(f"[PDF] Could not load logo at {logo_path}: {e}")
                    try:
                        c.drawImage("logo.png", logo_x, logo_y, width=logo_width, height=logo_height, preserveAspectRatio=True)
                    except Exception as e2:
                        print(f"[PDF] Fallback logo.png also failed: {e2}")
                    pass
                # Enhanced title styling
                c.setFont("Helvetica-Bold", 24)
                c.setFillColor(primary_color)
                title_x = left_margin + 1.5 * inch + 0.4 * inch
                title_y = height - 0.6 * inch
                c.drawString(title_x, title_y, "SkillWise Learning Roadmap")
                # Decorative line with gradient
                c.setStrokeColor(accent_color)
                c.setLineWidth(2)
                c.line(left_margin, height - 0.8 * inch, width - right_margin, height - 0.8 * inch)

            def draw_footer(page_num):
                # Enhanced footer design
                c.setFont("Helvetica", 8)
                c.setFillColor(text_color)
                footer_text = f"Generated by SkillWise | Page {page_num} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                c.drawCentredString(width / 2, bottom_margin + 0.1 * inch, footer_text)
                
                # Footer decorative line
                c.setStrokeColor(accent_color)
                c.setLineWidth(1)
                c.line(left_margin, bottom_margin + 0.3 * inch, width - right_margin, bottom_margin + 0.3 * inch)

            def draw_section_header(text, y_pos, is_phase=False):
                # Draw section header with enhanced styling
                if is_phase:
                    c.setFont("Helvetica-Bold", 20)
                    c.setFillColor(phase_color)
                    line_spacing = 24
                else:
                    c.setFont("Helvetica-Bold", 16)
                    c.setFillColor(primary_color)
                    line_spacing = 20
                
                # Draw decorative line before header
                c.setStrokeColor(accent_color)
                c.setLineWidth(1)
                c.line(left_margin, y_pos + 0.2 * inch, width - right_margin, y_pos + 0.2 * inch)
                
                # Draw header text
                y_pos = wrap_text(
                    c, text, left_margin, y_pos, content_width,
                    "Helvetica-Bold", 20 if is_phase else 16, line_spacing
                )
                
                # Draw decorative line after header
                c.setStrokeColor(accent_color)
                c.setLineWidth(1)
                c.line(left_margin, y_pos - 0.1 * inch, width - right_margin, y_pos - 0.1 * inch)
                
                return y_pos - 0.2 * inch

            def wrap_text(c, text, x, y, max_width, font_name, font_size, line_spacing=12):
                c.setFont(font_name, font_size)
                words = text.split()
                lines = []
                current_line = []
                current_width = 0

                for word in words:
                    word_width = c.stringWidth(word + " ", font_name, font_size)
                    if current_width + word_width <= max_width:
                        current_line.append(word)
                        current_width += word_width
                    else:
                        lines.append(" ".join(current_line))
                        current_line = [word]
                        current_width = word_width
                if current_line:
                    lines.append(" ".join(current_line))

                for line in lines:
                    c.drawString(x, y, line)
                    y -= line_spacing
                return y

            # Initialize variables
            y_position = height - top_margin
            page_num = 1

            # Draw first page header
            draw_header()
            y_position -= 0.5 * inch

            # Enhanced title section
            title_text = "Your Personalized Learning Roadmap"
            if st.session_state.get("focused_jd_roadmap"): # Check if it's a job-specific roadmap
                title_text = "Focused Learning Roadmap (Based on Job Description)"

            c.setFont("Helvetica-Bold", 28)
            c.setFillColor(primary_color)
            y_position = wrap_text(
                c, title_text, left_margin, y_position,
                content_width, "Helvetica-Bold", 28, line_spacing=32 # Increased line spacing for main title
            )
            y_position -= 0.3 * inch

            # Generation date with enhanced styling
            c.setFont("Helvetica", 12)
            c.setFillColor(text_color)
            y_position = wrap_text(
                c, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} for role: {effective_role}",
                left_margin, y_position, content_width, "Helvetica", 12, line_spacing=16
            )
            y_position -= 0.4 * inch

            # Add Job Fit Analysis if available
            if st.session_state.get("job_fit_analysis"):
                if y_position < bottom_margin + 3 * inch: # Check space
                    draw_footer(page_num)
                    c.showPage()
                    page_num += 1
                    draw_header()
                    y_position = height - top_margin - 0.5 * inch

                y_position = draw_section_header("Job Fit Analysis", y_position, is_phase=False)
                y_position -= 0.1 * inch # Small gap
                analysis_text = clean_text(st.session_state.job_fit_analysis)
                c.setFont("Helvetica", 10)
                c.setFillColor(text_color)
                y_position = wrap_text(c, analysis_text, left_margin + 0.2*inch, y_position, content_width - 0.2*inch, "Helvetica", 10, line_spacing=12)
                y_position -= 0.3 * inch


            # Add Smart AI Gap Analysis if available (and not a JD-focused roadmap, to avoid redundancy if similar)
            if st.session_state.get("smart_gap_analysis_result") and not st.session_state.get("job_fit_analysis"):
                if y_position < bottom_margin + 3 * inch: # Check space
                    draw_footer(page_num)
                    c.showPage()
                    page_num += 1
                    draw_header()
                    y_position = height - top_margin - 0.5 * inch

                y_position = draw_section_header("Smart AI Gap Analysis", y_position, is_phase=False)
                y_position -= 0.1 * inch # Small gap
                analysis_text = clean_text(st.session_state.smart_gap_analysis_result)
                c.setFont("Helvetica", 10)
                c.setFillColor(text_color)
                y_position = wrap_text(c, analysis_text, left_margin + 0.2*inch, y_position, content_width - 0.2*inch, "Helvetica", 10, line_spacing=12)
                y_position -= 0.3 * inch

            # Process roadmap content with enhanced styling
            lines = st.session_state.roadmap.splitlines()
            current_phase = None
            bullet_indent = left_margin + 0.3 * inch

            for line in lines:
                line = clean_text(line.strip())
                if not line:
                    continue

                if y_position < bottom_margin + 1.5 * inch:
                    draw_footer(page_num)
                    c.showPage()
                    page_num += 1
                    draw_header()
                    y_position = height - top_margin - 0.5 * inch

                if line.startswith("##"):
                    # Phase header
                    text = line[2:].strip()
                    y_position = draw_section_header(text, y_position, is_phase=True)
                    current_phase = text

                elif line.startswith("**") and line.endswith("**"):
                    # Subsection header
                    text = line[2:-2].strip()
                    if y_position < bottom_margin + 2 * inch:
                        draw_footer(page_num)
                        c.showPage()
                        page_num += 1
                        draw_header()
                        y_position = height - top_margin - 0.5 * inch

                    y_position = draw_section_header(text, y_position, is_phase=False)

                elif line.startswith("-"):
                    # Main bullet point
                    text = line[1:].strip()
                    
                    if ":" in text:
                        title, description = text.split(":", 1)
                        title = title.strip()
                        description = description.strip()
                        
                        # Draw bullet point with enhanced styling
                        c.setFont("Helvetica-Bold", 12)
                        c.setFillColor(primary_color)
                        y_position = wrap_text(
                            c, f"• {title}:", bullet_indent, y_position, 
                            content_width - 0.3 * inch, "Helvetica-Bold", 12, line_spacing=16
                        )
                        
                        # Draw description with enhanced styling
                        c.setFont("Helvetica", 11)
                        c.setFillColor(text_color)
                        y_position = wrap_text(
                            c, f"  {description}", bullet_indent + 0.2 * inch, y_position, 
                            content_width - 0.5 * inch, "Helvetica", 11, line_spacing=14
                        )
                    else:
                        # Regular bullet point with enhanced styling
                        c.setFont("Helvetica", 12)
                        c.setFillColor(text_color)
                        y_position = wrap_text(
                            c, f"• {text}", bullet_indent, y_position, 
                            content_width - 0.3 * inch, "Helvetica", 12, line_spacing=16
                        )

                elif line.startswith("  •"):
                    # Sub bullet point
                    text = line[3:].strip()
                    
                    if ":" in text:
                        title, description = text.split(":", 1)
                        title = title.strip()
                        description = description.strip()
                        
                        # Draw sub-bullet point with enhanced styling
                        c.setFont("Helvetica-Bold", 11)
                        c.setFillColor(accent_color)
                        y_position = wrap_text(
                            c, f"  ◦ {title}:", bullet_indent + 0.2 * inch, y_position, 
                            content_width - 0.5 * inch, "Helvetica-Bold", 11, line_spacing=14
                        )
                        
                        # Draw description with enhanced styling
                        c.setFont("Helvetica", 10)
                        c.setFillColor(text_color)
                        y_position = wrap_text(
                            c, f"    {description}", bullet_indent + 0.4 * inch, y_position, 
                            content_width - 0.7 * inch, "Helvetica", 10, line_spacing=12
                        )
                    else:
                        # Regular sub-bullet point with enhanced styling
                        c.setFont("Helvetica", 11)
                        c.setFillColor(text_color)
                        y_position = wrap_text(
                            c, f"  ◦ {text}", bullet_indent + 0.2 * inch, y_position, 
                            content_width - 0.5 * inch, "Helvetica", 11, line_spacing=14
                        )

                else:
                    # Regular text with enhanced styling
                    c.setFont("Helvetica", 11)
                    c.setFillColor(text_color)
                    y_position = wrap_text(
                        c, line, left_margin, y_position, content_width,
                        "Helvetica", 11, line_spacing=14
                    )

            draw_footer(page_num)
            c.save()
            pdf_bytes = buffer.getvalue()
            buffer.close()
            return pdf_bytes

        if st.button("📄 Download as PDF"):
            try:
                pdf_bytes = generate_pdf()
                st.download_button(
                    label="📄 Click to Download PDF",
                    data=pdf_bytes,
                    file_name="SkillWise_Roadmap.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"❌ Error generating PDF: {str(e)}")
        
        roadmap_data = {
            "resume": st.session_state.resume_text,
            "goal": st.session_state.goal,
            "role": effective_role,
            "roadmap": st.session_state.roadmap,
            "timestamp": datetime.now().isoformat()
        }
        st.download_button(
            label="💾 Download as JSON",
            data=json.dumps(roadmap_data, indent=2),
            file_name="SkillWise_Roadmap.json",
            mime="application/json"
        )
        


    else:
        st.info("🚧 Generate a roadmap in the Resume tab.")

# Footer
st.markdown("""
<div class="footer">
    <div class="social-icons">
        <a href="https://github.com/sizwinz/" target="_blank"><i class="fab fa-github"></i></a>
    </div>
    <p>© 2025 SkillWise. All rights reserved.</p>
    <p>
        <a href="https://linktr.ee/sahaj33">Contact Me</a>
    </p>
</div>
""", unsafe_allow_html=True)

ROADMAPS_DB_PATH = os.path.join(os.path.dirname(__file__), "roadmaps_db.json")

# --- Persistent Roadmap Management ---

# --- On App Start: Load and display previous roadmaps ---
if "roadmaps_db" not in st.session_state:
    st.session_state.roadmaps_db = load_roadmaps_db()

# Find active roadmap
active_roadmap = None
for r in st.session_state.roadmaps_db:
    if r.get("active"):
        active_roadmap = r
        break

# If no active roadmap, set the most recent as active
if not active_roadmap and st.session_state.roadmaps_db:
    st.session_state.roadmaps_db[0]["active"] = True
    active_roadmap = st.session_state.roadmaps_db[0]
    save_roadmaps_db(st.session_state.roadmaps_db)

# Load active roadmap into session
if active_roadmap:
    st.session_state.resume_text = active_roadmap["resume"]
    st.session_state.goal = active_roadmap["goal"]
    st.session_state.role = active_roadmap["role"]
    st.session_state.roadmap = active_roadmap["roadmap"]

# --- UI: Recent Roadmaps Sidebar ---
with st.sidebar:
    st.markdown("---", unsafe_allow_html=True)
    st.header("🗂️ Your Recent Roadmaps")
    # Search/filter box
    search_query = st.text_input("🔍 Search by role or goal", "")
    filtered_roadmaps = st.session_state.roadmaps_db
    if search_query.strip():
        sq = search_query.lower()
        filtered_roadmaps = [r for r in st.session_state.roadmaps_db if sq in r["role"].lower() or sq in r["goal"].lower()]
    # Export all button
    if filtered_roadmaps:
        st.download_button(
            "⬇️ Export All",
            data=json.dumps(filtered_roadmaps, indent=2),
            file_name="SkillWise_All_Roadmaps.json",
            mime="application/json",
            key="export_all_btn"
        )
    st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
    if filtered_roadmaps:
        for idx, r in enumerate(sorted(filtered_roadmaps, key=lambda x: x.get("last_accessed", x["timestamp"]), reverse=True)):
            is_active = r.get("active", False)
            with st.container():
                st.markdown(f"<div style='border:2px solid {'#60a5fa' if is_active else '#444'}; border-radius:10px; padding:10px; margin-bottom:10px; background-color:{'#23234a' if is_active else '#191932'}'>", unsafe_allow_html=True)
                st.markdown(f"**Role:** {r['role']}  ")
                st.markdown(f"**Goal:** {r['goal']}  ")
                st.markdown(f"**Date:** {r['timestamp'][:19].replace('T',' ')}  ")
                st.markdown(f"**ID:** `{r['id']}`")
                if is_active:
                    st.success("Active Roadmap")
                
                disabled = st.session_state.get("is_processing", False)

                # Continue Button
                if st.button("Continue", key=f"cont_{r['id']}", disabled=disabled):
                    for rr in st.session_state.roadmaps_db:
                        rr["active"] = (rr["id"] == r["id"])
                        if rr["active"]:
                            rr["last_accessed"] = datetime.now().isoformat()
                    save_roadmaps_db(st.session_state.roadmaps_db)
                    st.session_state.resume_text = r["resume"]
                    st.session_state.goal = r["goal"]
                    st.session_state.role = r["role"]
                    st.session_state.roadmap = r["roadmap"]
                    st.toast("Roadmap continued and set as active.")
                    st.rerun()

                # Delete Button
                if not st.session_state.get(f'confirm_delete_{r["id"]}'):
                    if st.button("Delete", key=f"del_{r['id']}", disabled=disabled):
                        st.session_state[f'confirm_delete_{r["id"]}'] = True
                        st.rerun()
                else:
                    st.warning(f"Delete '{r['goal']}'?")
                    col_confirm_yes, col_confirm_no = st.columns(2)
                    with col_confirm_yes:
                        if st.button("Yes", key=f"confirm_yes_{r['id']}"):
                            st.session_state.roadmaps_db = [rr for rr in st.session_state.roadmaps_db if rr["id"] != r["id"]]
                            save_roadmaps_db(st.session_state.roadmaps_db)
                            st.toast("Roadmap deleted.")
                            del st.session_state[f'confirm_delete_{r["id"]}']
                            st.rerun()
                    with col_confirm_no:
                        if st.button("No", key=f"confirm_no_{r['id']}"):
                            del st.session_state[f'confirm_delete_{r["id"]}']
                            st.rerun()

                # Export Button
                st.download_button("Export", data=json.dumps(r, indent=2), file_name=f"SkillWise_Roadmap_{r['id']}.json", mime="application/json", key=f"exp_{r['id']}", disabled=disabled)

                # Set Active Button
                if not is_active:
                    if st.button("⭐ Set Active", key=f"set_{r['id']}", disabled=disabled):
                        for rr in st.session_state.roadmaps_db:
                            rr["active"] = (rr["id"] == r["id"])
                            if rr["active"]:
                                rr["last_accessed"] = datetime.now().isoformat()
                        save_roadmaps_db(st.session_state.roadmaps_db)
                        st.session_state.resume_text = r["resume"]
                        st.session_state.goal = r["goal"]
                        st.session_state.role = r["role"]
                        st.session_state.roadmap = r["roadmap"]
                        st.toast("Roadmap set as active.")
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No saved roadmaps yet. Generate one to get started!")

# --- On New Roadmap Generation: Check for existing, else create new ---
# In the code where you generate a new roadmap (after parsing resume, role, goal):
# Before generating, check if exists
# (Insert this logic before calling generate_roadmap)
# ...
# Example (inside the button click handler):
#
# new_id = roadmap_id(st.session_state.resume_text, st.session_state.goal, effective_role)
# found = None
# for r in st.session_state.roadmaps_db:
#     if r["id"] == new_id:
#         found = r
#         break
# if found:
#     # Load existing
#     for rr in st.session_state.roadmaps_db:
#         rr["active"] = (rr["id"] == found["id"])
#         if rr["active"]:
#             rr["last_accessed"] = datetime.now().isoformat()
#     save_roadmaps_db(st.session_state.roadmaps_db)
#     st.session_state.resume_text = found["resume"]
#     st.session_state.goal = found["goal"]
#     st.session_state.role = found["role"]
#     st.session_state.roadmap = found["roadmap"]
#     st.success("Loaded existing roadmap for this resume/goal/role.")
#     st.rerun()
# else:
#     # Generate new, then save
#     # ... after generating roadmap ...
#     new_roadmap = {
#         "id": new_id,
#         "resume": st.session_state.resume_text,
#         "goal": st.session_state.goal,
#         "role": effective_role,
#         "roadmap": st.session_state.roadmap,
#         "timestamp": datetime.now().isoformat(),
#         "last_accessed": datetime.now().isoformat(),
#         "active": True
#     }
#     for rr in st.session_state.roadmaps_db:
#         rr["active"] = False
#     st.session_state.roadmaps_db.insert(0, new_roadmap)
#     save_roadmaps_db(st.session_state.roadmaps_db)
#     st.success("New roadmap saved and set as active.")
#     st.rerun()
