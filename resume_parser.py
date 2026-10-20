# resume_parser.py
import os
import re
import shutil
import fitz  # PyMuPDF
from PIL import Image
from typing import Dict, Any, Union

MAX_OCR_PAGES = 8


def is_valid_pdf(file_path: str) -> bool:
    """Check if file exists and is a valid, unlocked, readable PDF."""
    if not file_path or not os.path.exists(file_path):
        return False
    if not file_path.lower().endswith(".pdf"):
        return False
    try:
        with fitz.open(file_path) as doc:
            if doc.is_encrypted:
                return False
            return not doc.is_closed and len(doc) > 0
    except Exception:
        return False


def _ocr_single_page(page: fitz.Page, pytesseract_mod) -> str:
    """Render a single PDF page in 200 DPI grayscale and run Tesseract OCR."""
    pix = page.get_pixmap(dpi=200, colorspace=fitz.csGRAY)
    img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
    return pytesseract_mod.image_to_string(img).strip()


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract embedded text from PDF using PyMuPDF with layout sorting."""
    text_blocks = []
    try:
        with fitz.open(pdf_path) as doc:
            if doc.is_encrypted:
                raise ValueError("PDF is password-protected. Please upload an unlocked PDF.")
            for page in doc:
                page_text = page.get_text("text", sort=True)
                if page_text and page_text.strip():
                    text_blocks.append(page_text.strip())
        return "\n\n".join(text_blocks).strip()
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF: {str(e)}")


def extract_text_with_ocr(pdf_path: str) -> str:
    """Extract text from scanned PDF pages using OCR with graceful binary detection."""
    try:
        import pytesseract
    except ImportError:
        raise RuntimeError("pytesseract package is not installed.")

    if not shutil.which("tesseract"):
        raise RuntimeError(
            "Tesseract OCR binary is not installed or not in system PATH. "
            "Please paste your resume text directly into the text editor tab."
        )

    text_blocks = []
    try:
        with fitz.open(pdf_path) as doc:
            page_limit = min(len(doc), MAX_OCR_PAGES)
            for page_num in range(page_limit):
                page = doc.load_page(page_num)
                # Hybrid optimization: keep digital text if page already has rich text layer
                digital_page_text = page.get_text("text", sort=True).strip()
                if len(digital_page_text) >= 60:
                    text_blocks.append(digital_page_text)
                else:
                    ocr_page_text = _ocr_single_page(page, pytesseract)
                    if len(ocr_page_text) > len(digital_page_text):
                        text_blocks.append(ocr_page_text)
                    elif digital_page_text:
                        text_blocks.append(digital_page_text)
        return "\n\n".join(text_blocks).strip()
    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract OCR is not installed or not configured in system PATH. "
            "Please paste your resume text directly into the text editor tab."
        )
    except Exception as e:
        raise RuntimeError(f"OCR text extraction failed: {str(e)}")


def parse_resume(pdf_path: str) -> str:
    """
    Parse resume with multi-layer extraction, hybrid per-page OCR fallback, and validation.

    Args:
        pdf_path: Absolute or relative path to PDF file.

    Returns:
        str: Extracted resume text.
    """
    if not pdf_path or not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Resume file not found at: {pdf_path}")

    try:
        with fitz.open(pdf_path) as doc:
            if doc.is_encrypted:
                raise ValueError("The uploaded PDF is password-protected. Please upload an unlocked PDF.")
            if doc.is_closed or len(doc) == 0:
                raise ValueError("The provided PDF file is empty or unreadable.")
            page_count = len(doc)
    except ValueError:
        raise
    except Exception:
        raise ValueError("The provided file is not a valid or readable PDF format.")

    # Layer 1: Direct digital text extraction
    text = extract_text_from_pdf(pdf_path)

    # Layer 2: OCR fallback if overall text is sparse OR average text per page is suspiciously low
    avg_chars_per_page = len(text.strip()) / max(page_count, 1)
    if len(text.strip()) < 80 or (page_count > 1 and avg_chars_per_page < 60):
        try:
            ocr_text = extract_text_with_ocr(pdf_path)
            if len(ocr_text.strip()) > len(text.strip()):
                text = ocr_text
        except RuntimeError:
            if not text.strip():
                raise
        except Exception:
            if not text.strip():
                raise

    # Strip null bytes and non-printable control characters
    clean_text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text).strip()
    if not clean_text or len(clean_text) < 20:
        raise ValueError("Insufficient text content extracted from resume. Please paste text directly.")

    return clean_text


def parse_linkedin_json(json_data: Union[Dict[str, Any], list]) -> str:
    """
    Parses LinkedIn, JSON Resume, or general career profile JSON data into structured text.
    Resilient to multiple standard schema variations, nested date objects, and list exports.
    """
    if not json_data:
        return ""

    if isinstance(json_data, list):
        merged_text = []
        for item in json_data:
            if isinstance(item, dict):
                merged_text.append(parse_linkedin_json(item))
            elif isinstance(item, str):
                merged_text.append(item.strip())
        return "\n\n".join(filter(None, merged_text))

    if not isinstance(json_data, dict):
        return ""

    text_parts = []

    def get_safe(data, keys, default=""):
        """Safely traverse dictionary keys and extract primitive values."""
        curr = data
        for key in keys:
            if isinstance(curr, dict) and key in curr:
                curr = curr[key]
            elif isinstance(curr, list) and isinstance(key, int) and 0 <= key < len(curr):
                curr = curr[key]
            else:
                return default
        if isinstance(curr, (str, int, float)) and not isinstance(curr, bool):
            return str(curr).strip()
        return default

    def extract_date(entry: dict, field_name: str, default: str = "") -> str:
        """Extract date string whether stored as primitive, nested year, or timePeriod."""
        return (
            get_safe(entry, ["timePeriod", field_name, "year"])
            or get_safe(entry, [field_name, "year"])
            or get_safe(entry, [field_name])
            or default
        )

    # 1. Basic / Profile Section
    profile = json_data.get("profile", json_data.get("basics", json_data))
    if not isinstance(profile, dict):
        profile = json_data

    first_name = get_safe(profile, ["firstName"]) or get_safe(profile, ["first_name"]) or get_safe(profile, ["name"])
    last_name = get_safe(profile, ["lastName"]) or get_safe(profile, ["last_name"])
    headline = get_safe(profile, ["headline"]) or get_safe(profile, ["label"]) or get_safe(profile, ["title"])
    summary = get_safe(profile, ["summary"]) or get_safe(profile, ["about"]) or get_safe(profile, ["description"])
    email = get_safe(profile, ["email"])

    header_parts = []
    if first_name and last_name and last_name not in first_name:
        header_parts.append(f"Name: {first_name} {last_name}")
    elif first_name:
        header_parts.append(f"Name: {first_name}")
    if headline:
        header_parts.append(f"Headline/Role: {headline}")
    if email:
        header_parts.append(f"Email: {email}")
    if summary:
        header_parts.append(f"Summary:\n{summary}")
    if header_parts:
        text_parts.append("\n".join(header_parts))

    # 2. Experience Section
    experience = (
        json_data.get("experience")
        or json_data.get("positions")
        or json_data.get("workExperience")
        or json_data.get("work")
        or []
    )
    if isinstance(experience, list) and experience:
        exp_entries = []
        for entry in experience:
            if not isinstance(entry, dict):
                continue
            title = get_safe(entry, ["title"]) or get_safe(entry, ["position"]) or get_safe(entry, ["role"])
            company = get_safe(entry, ["companyName"]) or get_safe(entry, ["company"]) or get_safe(entry, ["name"])
            description = get_safe(entry, ["description"]) or get_safe(entry, ["summary"])
            highlights = entry.get("highlights", [])
            start = extract_date(entry, "startDate")
            end = extract_date(entry, "endDate", "Present") if start else extract_date(entry, "endDate")

            date_str = f" ({start} - {end or 'Present'})" if start else (f" ({end})" if end else "")
            item_lines = []
            if title and company:
                item_lines.append(f"{title} at {company}{date_str}")
            elif title or company:
                item_lines.append(f"{title or company}{date_str}")
            if description:
                item_lines.append(f"  {description}")
            if isinstance(highlights, list):
                for h in highlights:
                    if isinstance(h, str) and h.strip():
                        item_lines.append(f"  - {h.strip()}")
            if item_lines:
                exp_entries.append("- " + "\n".join(item_lines))
        if exp_entries:
            text_parts.append("Experience:\n" + "\n".join(exp_entries))

    # 3. Education Section
    education = json_data.get("education") or json_data.get("educationEntries") or []
    if isinstance(education, list) and education:
        edu_entries = []
        for entry in education:
            if not isinstance(entry, dict):
                continue
            school = get_safe(entry, ["schoolName"]) or get_safe(entry, ["institution"]) or get_safe(entry, ["school"])
            degree = get_safe(entry, ["degreeName"]) or get_safe(entry, ["studyType"]) or get_safe(entry, ["degree"])
            field = get_safe(entry, ["fieldOfStudy"]) or get_safe(entry, ["area"])
            start = extract_date(entry, "startDate")
            end = extract_date(entry, "endDate")

            line = f"{degree} in {field}" if (degree and field) else (degree or field or "Degree")
            if school:
                line += f" from {school}"
            if start or end:
                line += f" ({start} - {end})".replace("( - ", "(").replace(" - )", ")")
            edu_entries.append(f"- {line}")
        if edu_entries:
            text_parts.append("Education:\n" + "\n".join(edu_entries))

    # 4. Skills Section
    skills_sec = json_data.get("skills") or json_data.get("skillKeywords") or []
    if isinstance(skills_sec, list) and skills_sec:
        skill_names = []
        for s in skills_sec:
            if isinstance(s, dict):
                name = s.get("name") or s.get("skill")
                keywords = s.get("keywords", [])
                if name:
                    skill_names.append(str(name).strip())
                if isinstance(keywords, list):
                    skill_names.extend(str(k).strip() for k in keywords if k)
            elif isinstance(s, str) and s.strip():
                skill_names.append(s.strip())
        if skill_names:
            text_parts.append("Skills: " + ", ".join(dict.fromkeys(skill_names)))

    # 5. Projects Section
    projects = json_data.get("projects") or []
    if isinstance(projects, list) and projects:
        proj_entries = []
        for p in projects:
            if isinstance(p, dict):
                name = get_safe(p, ["name"]) or get_safe(p, ["title"])
                desc = get_safe(p, ["description"]) or get_safe(p, ["summary"])
                if name:
                    proj_line = f"- {name}" + (f": {desc}" if desc else "")
                    proj_entries.append(proj_line)
        if proj_entries:
            text_parts.append("Projects:\n" + "\n".join(proj_entries))

    # 6. Certifications Section
    certifications = json_data.get("certifications") or json_data.get("certificates") or []
    if isinstance(certifications, list) and certifications:
        cert_entries = []
        for c in certifications:
            if isinstance(c, dict):
                name = get_safe(c, ["name"]) or get_safe(c, ["title"])
                authority = get_safe(c, ["authority"]) or get_safe(c, ["issuer"])
                if name:
                    cert_line = f"- {name}" + (f" ({authority})" if authority else "")
                    cert_entries.append(cert_line)
        if cert_entries:
            text_parts.append("Certifications:\n" + "\n".join(cert_entries))

    return "\n\n".join(text_parts).strip()
