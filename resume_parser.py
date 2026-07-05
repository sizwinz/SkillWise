import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import os
import tempfile
import json

def is_valid_pdf(file_path):
    """Check if file is a valid PDF."""
    try:
        # Fallback: Check file extension and try to open with PyMuPDF
        if not file_path.lower().endswith('.pdf'):
            return False
        try:
            doc = fitz.open(file_path)
            doc.close()
            return True
        except:
            return False
    except Exception:
        return False

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using PyMuPDF."""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def extract_text_with_ocr(pdf_path):
    """Extract text from PDF using OCR."""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text += pytesseract.image_to_string(img)
        doc.close()
        return text
    except pytesseract.TesseractNotFoundError:
        raise Exception(
            "Tesseract OCR binary not found on your system. "
            "Please install Tesseract OCR and ensure the binary path is correctly included "
            "in your system's environment variables (PATH)."
        )
    except Exception as e:
        raise Exception(f"Failed to perform OCR: {str(e)}")


def parse_resume(pdf_path):
    """Parse resume with improved error handling and validation."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Resume file not found: {pdf_path}")
    
    if not is_valid_pdf(pdf_path):
        raise ValueError("Invalid PDF file format")
    
    try:
        # First attempt: Direct text extraction
        text = extract_text_from_pdf(pdf_path)
        
        # If text extraction yields insufficient content, try OCR
        if len(text.strip()) < 100:
            text = extract_text_with_ocr(pdf_path)
            
        # Validate extracted text
        if not text.strip():
            raise ValueError("No text could be extracted from the resume")
            
        return text.strip()
        
    except Exception as e:
        raise Exception(f"Failed to parse resume: {str(e)}")
    finally:
        # Cleanup if file was created in temp directory
        if os.path.dirname(pdf_path) == tempfile.gettempdir():
            try:
                os.remove(pdf_path)
            except:
                pass

def parse_linkedin_json(json_data):
    """
    Parses LinkedIn profile data from a JSON object and extracts relevant text.
    This function makes educated guesses about the JSON structure.
    """
    text_parts = []

    def get_safe(data, keys, default=""):
        """Safely access nested dictionary keys."""
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            elif isinstance(data, list) and isinstance(key, int) and key < len(data):
                data = data[key]
            else:
                return default
        return data if isinstance(data, (str, int, float)) else default

    # Profile / Basic Info
    # Common top-level keys for profile information might be 'profile', 'basics', 'info'
    # For this example, let's assume a structure like:
    # { "profile": { "firstName": "...", "lastName": "...", "headline": "...", "summary": "..." } }
    # Or sometimes it's directly at the root if the JSON is just the profile.

    profile_section = json_data.get("profile", json_data) # Check for 'profile' key or use root

    first_name = get_safe(profile_section, ["firstName"]) or get_safe(profile_section, ["first_name"])
    last_name = get_safe(profile_section, ["lastName"]) or get_safe(profile_section, ["last_name"])
    headline = get_safe(profile_section, ["headline"])
    summary = get_safe(profile_section, ["summary"]) or get_safe(profile_section, ["about"])

    if first_name and last_name:
        text_parts.append(f"Name: {first_name} {last_name}")
    if headline:
        text_parts.append(f"Headline: {headline}")
    if summary:
        text_parts.append(f"Summary:\n{summary}")

    # Experience
    # Common keys: 'experience', 'positions', 'workExperience'
    # Structure: [{ "title": "...", "companyName": "...", "description": "...", "startDate": "...", "endDate": "..."}]
    experience_entries = json_data.get("experience", json_data.get("positions", json_data.get("workExperience", [])))
    if isinstance(experience_entries, list) and experience_entries:
        text_parts.append("\nExperience:")
        for entry in experience_entries:
            title = get_safe(entry, ["title"])
            company = get_safe(entry, ["companyName"]) or get_safe(entry, ["company"])
            description = get_safe(entry, ["description"])
            location = get_safe(entry, ["locationName"]) or get_safe(entry,["location"])
            start_date = get_safe(entry, ["timePeriod", "startDate", "year"]) or get_safe(entry, ["startDate", "year"])
            end_date = get_safe(entry, ["timePeriod", "endDate", "year"]) or get_safe(entry, ["endDate", "year"])

            entry_text = []
            if title: entry_text.append(f"Title: {title}")
            if company: entry_text.append(f"Company: {company}")
            if location: entry_text.append(f"Location: {location}")
            if start_date and end_date:
                entry_text.append(f"Dates: {start_date} - {end_date or 'Present'}")
            elif start_date:
                 entry_text.append(f"Dates: {start_date} - Present")
            if description: entry_text.append(f"Description:\n{description}")

            if entry_text:
                text_parts.append("- " + "\n  ".join(entry_text))

    # Education
    # Common keys: 'education', 'educationEntries'
    # Structure: [{ "schoolName": "...", "degreeName": "...", "fieldOfStudy": "...", "startDate": "...", "endDate": "..."}]
    education_entries = json_data.get("education", json_data.get("educationEntries", []))
    if isinstance(education_entries, list) and education_entries:
        text_parts.append("\nEducation:")
        for entry in education_entries:
            school = get_safe(entry, ["schoolName"]) or get_safe(entry, ["school"])
            degree = get_safe(entry, ["degreeName"]) or get_safe(entry, ["degree"])
            field = get_safe(entry, ["fieldOfStudy"])
            start_date = get_safe(entry, ["timePeriod", "startDate", "year"]) or get_safe(entry, ["startDate", "year"])
            end_date = get_safe(entry, ["timePeriod", "endDate", "year"]) or get_safe(entry, ["endDate", "year"])

            entry_text = []
            if school: entry_text.append(f"School: {school}")
            if degree: entry_text.append(f"Degree: {degree}")
            if field: entry_text.append(f"Field of Study: {field}")
            if start_date and end_date:
                entry_text.append(f"Dates: {start_date} - {end_date or 'Present'}")
            elif start_date:
                entry_text.append(f"Dates: {start_date} - Present")

            if entry_text:
                text_parts.append("- " + "\n  ".join(entry_text))

    # Skills
    # Common keys: 'skills', 'skillKeywords'
    # Structure: [{ "name": "..." }] or ["skill1", "skill2"]
    skills_section = json_data.get("skills", json_data.get("skillKeywords", []))
    if isinstance(skills_section, list) and skills_section:
        text_parts.append("\nSkills:")
        parsed_skills = []
        for skill_entry in skills_section:
            if isinstance(skill_entry, dict):
                skill_name = get_safe(skill_entry, ["name"])
                if skill_name: parsed_skills.append(skill_name)
            elif isinstance(skill_entry, str):
                parsed_skills.append(skill_entry)
        if parsed_skills:
            text_parts.append(", ".join(parsed_skills))

    # Projects
    # Common keys: 'projects'
    # Structure: [{ "title": "...", "description": "..."}]
    project_entries = json_data.get("projects", [])
    if isinstance(project_entries, list) and project_entries:
        text_parts.append("\nProjects:")
        for entry in project_entries:
            title = get_safe(entry, ["title"])
            description = get_safe(entry, ["description"])
            entry_text = []
            if title: entry_text.append(f"Title: {title}")
            if description: entry_text.append(f"Description:\n{description}")
            if entry_text:
                text_parts.append("- " + "\n  ".join(entry_text))

    # Certifications
    # Common keys: 'certifications'
    # Structure: [{"name": "...", "authority": "...", "url": "..."}]
    certification_entries = json_data.get("certifications", [])
    if isinstance(certification_entries, list) and certification_entries:
        text_parts.append("\nCertifications:")
        for entry in certification_entries:
            name = get_safe(entry, ["name"])
            authority = get_safe(entry, ["authority"])
            url = get_safe(entry, ["url"])
            entry_text = []
            if name: entry_text.append(f"Name: {name}")
            if authority: entry_text.append(f"Authority: {authority}")
            if url: entry_text.append(f"URL: {url}")
            if entry_text:
                text_parts.append("- " + "\n  ".join(entry_text))

    return "\n\n".join(text_parts)