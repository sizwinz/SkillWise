# utils/pdf_exporter.py
import os
import re
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor


class PDFPageManager:
    """Manages canvas pagination, headers, and footers across dynamic multi-page documents."""

    def __init__(
        self,
        c: canvas.Canvas,
        width: float,
        height: float,
        left_margin: float,
        right_margin: float,
        top_margin: float,
        bottom_margin: float,
    ):
        self.c = c
        self.width = width
        self.height = height
        self.left_margin = left_margin
        self.right_margin = right_margin
        self.top_margin = top_margin
        self.bottom_margin = bottom_margin
        self.content_width = width - left_margin - right_margin
        self.page_num = 1
        self.primary_color = HexColor("#4a69bd")
        self.accent_color = HexColor("#60a5fa")
        self.text_color = HexColor("#2d2d44")
        self.phase_color = HexColor("#1a1a2e")
        self.y = height - top_margin - 0.5 * inch

    def draw_header(self):
        """Draw persistent top banner and branding."""
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SkillWise.png"))
        logo_width = 1.2 * inch
        logo_height = 0.4 * inch
        logo_x = self.left_margin
        logo_y = self.height - 0.65 * inch

        if os.path.exists(logo_path):
            try:
                self.c.drawImage(
                    logo_path,
                    logo_x,
                    logo_y,
                    width=logo_width,
                    height=logo_height,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass

        self.c.setFont("Helvetica-Bold", 16)
        self.c.setFillColor(self.primary_color)
        title_x = self.left_margin + 1.4 * inch
        title_y = self.height - 0.55 * inch
        self.c.drawString(title_x, title_y, "SkillWise Learning Roadmap")

        self.c.setStrokeColor(self.accent_color)
        self.c.setLineWidth(1.5)
        self.c.line(
            self.left_margin,
            self.height - 0.75 * inch,
            self.width - self.right_margin,
            self.height - 0.75 * inch,
        )

    def draw_footer(self):
        """Draw persistent footer with pagination and timestamp."""
        self.c.setFont("Helvetica", 8)
        self.c.setFillColor(self.text_color)
        footer_text = f"SkillWise | Page {self.page_num} | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        self.c.drawCentredString(self.width / 2, self.bottom_margin - 0.25 * inch, footer_text)

        self.c.setStrokeColor(self.accent_color)
        self.c.setLineWidth(0.8)
        self.c.line(
            self.left_margin,
            self.bottom_margin - 0.1 * inch,
            self.width - self.right_margin,
            self.bottom_margin - 0.1 * inch,
        )

    def ensure_space(self, required_height: float):
        """Check vertical room and automatically trigger page transition when needed."""
        if self.y - required_height < self.bottom_margin:
            self.draw_footer()
            self.c.showPage()
            self.page_num += 1
            self.draw_header()
            self.y = self.height - self.top_margin - 0.5 * inch

    def _split_overlong_word(self, word: str, max_width: float, font_name: str, font_size: float):
        """Split a single token (like a long URL) if it exceeds max_width."""
        chunks = []
        current = ""
        for ch in word:
            if self.c.stringWidth(current + ch, font_name, font_size) <= max_width:
                current += ch
            else:
                if current:
                    chunks.append(current)
                current = ch
        if current:
            chunks.append(current)
        return chunks or [word]

    def draw_wrapped_text(
        self,
        text: str,
        x: float,
        max_width: float,
        font_name: str,
        font_size: float,
        line_spacing: float,
        color=None,
    ):
        """Render text wrapped within margins with continuous page-break and overflow protection."""
        if color:
            self.c.setFillColor(color)
        self.c.setFont(font_name, font_size)

        raw_words = text.split()
        if not raw_words:
            return

        words = []
        for w in raw_words:
            if self.c.stringWidth(w + " ", font_name, font_size) > max_width:
                words.extend(self._split_overlong_word(w, max_width, font_name, font_size))
            else:
                words.append(w)

        lines = []
        current_line = []
        current_width = 0.0

        for word in words:
            word_width = self.c.stringWidth(word + " ", font_name, font_size)
            if current_width + word_width <= max_width or not current_line:
                current_line.append(word)
                current_width += word_width
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_width = word_width

        if current_line:
            lines.append(" ".join(current_line))

        for line in lines:
            self.ensure_space(line_spacing)
            self.c.drawString(x, self.y, line)
            self.y -= line_spacing


def sanitize_pdf_text(text: str) -> str:
    """Normalize typography and remove unprintable characters without losing sentence symbols."""
    if not text:
        return ""
    replacements = {
        "\u2014": "-",    # em-dash
        "\u2013": "-",    # en-dash
        "\u2212": "-",    # minus sign
        "\u2018": "'",    # left single smart quote
        "\u2019": "'",    # right single smart quote
        "\u201c": '"',    # left double smart quote
        "\u201d": '"',    # right double smart quote
        "\u2022": "-",    # bullet
        "\u2023": "-",    # triangular bullet
        "\u25aa": "-",    # black small square
        "\u2026": "...",  # ellipsis
        "\u2192": "->",   # right arrow
        "\u21d2": "=>",   # double right arrow
        "\u00a0": " ",    # non-breaking space
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return "".join(c if (ord(c) < 256 and c.isprintable()) or c in "\n\t " else " " for c in text)


def generate_pdf(
    roadmap: str,
    job_fit_analysis: str = None,
    smart_gap_analysis: str = None,
    effective_role: str = "",
) -> bytes:
    """Generate a high-grade, fully paginated PDF export of the learning roadmap and analyses."""
    buffer = BytesIO()
    width, height = letter
    c = canvas.Canvas(buffer, pagesize=letter)

    left_margin = 0.8 * inch
    right_margin = 0.8 * inch
    top_margin = 0.8 * inch
    bottom_margin = 0.8 * inch

    mgr = PDFPageManager(c, width, height, left_margin, right_margin, top_margin, bottom_margin)
    mgr.draw_header()

    # Document Title
    mgr.ensure_space(0.8 * inch)
    mgr.c.setFont("Helvetica-Bold", 22)
    mgr.c.setFillColor(mgr.primary_color)
    mgr.c.drawString(left_margin, mgr.y, "Personalized Learning Roadmap")
    mgr.y -= 0.3 * inch

    # Subtitle with role and timestamp
    mgr.c.setFont("Helvetica", 11)
    mgr.c.setFillColor(mgr.text_color)
    role_text = f"Target Role: {effective_role or 'Technology Professional'} | Date: {datetime.now().strftime('%B %d, %Y')}"
    mgr.c.drawString(left_margin, mgr.y, sanitize_pdf_text(role_text))
    mgr.y -= 0.4 * inch

    # Render Job Fit Analysis if present
    if job_fit_analysis:
        mgr.ensure_space(0.6 * inch)
        mgr.c.setFont("Helvetica-Bold", 14)
        mgr.c.setFillColor(mgr.primary_color)
        mgr.c.drawString(left_margin, mgr.y, "Job Description Fit Analysis")
        mgr.y -= 0.22 * inch

        clean_fit = sanitize_pdf_text(job_fit_analysis)
        for paragraph in clean_fit.split("\n"):
            para = paragraph.strip()
            if para:
                mgr.draw_wrapped_text(
                    para,
                    left_margin + 0.1 * inch,
                    mgr.content_width - 0.1 * inch,
                    "Helvetica",
                    9.5,
                    13,
                    mgr.text_color,
                )
        mgr.y -= 0.25 * inch

    # Render Smart AI Gap Analysis if present (no longer suppressed by job_fit_analysis)
    if smart_gap_analysis:
        mgr.ensure_space(0.6 * inch)
        mgr.c.setFont("Helvetica-Bold", 14)
        mgr.c.setFillColor(mgr.primary_color)
        mgr.c.drawString(left_margin, mgr.y, "Skill Gap Analysis")
        mgr.y -= 0.22 * inch

        clean_gap = sanitize_pdf_text(smart_gap_analysis)
        for paragraph in clean_gap.split("\n"):
            para = paragraph.strip()
            if para:
                mgr.draw_wrapped_text(
                    para,
                    left_margin + 0.1 * inch,
                    mgr.content_width - 0.1 * inch,
                    "Helvetica",
                    9.5,
                    13,
                    mgr.text_color,
                )
        mgr.y -= 0.25 * inch

    # Roadmap Header
    mgr.ensure_space(0.5 * inch)
    mgr.c.setFont("Helvetica-Bold", 15)
    mgr.c.setFillColor(mgr.primary_color)
    mgr.c.drawString(left_margin, mgr.y, "Curriculum & Action Plan")
    mgr.y -= 0.25 * inch

    lines = roadmap.splitlines() if roadmap else []
    for raw_line in lines:
        line = sanitize_pdf_text(raw_line.strip())
        if not line:
            mgr.y -= 0.08 * inch
            continue

        # Phase header: "## Phase 1"
        if line.startswith("##") and not line.startswith("###"):
            phase_text = line.lstrip("#").strip()
            mgr.ensure_space(0.45 * inch)
            mgr.c.setStrokeColor(mgr.accent_color)
            mgr.c.setLineWidth(0.8)
            mgr.c.line(left_margin, mgr.y + 0.1 * inch, width - right_margin, mgr.y + 0.1 * inch)
            mgr.draw_wrapped_text(
                phase_text, left_margin, mgr.content_width, "Helvetica-Bold", 13, 16, mgr.phase_color
            )
            mgr.y -= 0.05 * inch

        # Module header: "### Module 1" or "**Module 1**"
        elif line.startswith("###") or (line.startswith("**") and line.endswith("**") and len(line) > 4):
            module_text = line.lstrip("#*").rstrip("*").strip()
            mgr.ensure_space(0.35 * inch)
            mgr.draw_wrapped_text(
                module_text,
                left_margin + 0.15 * inch,
                mgr.content_width - 0.15 * inch,
                "Helvetica-Bold",
                11,
                14,
                mgr.primary_color,
            )
            mgr.y -= 0.04 * inch

        # Bulleted or numbered task item
        elif line.startswith(("-", "*", "+")) or re.match(r"^\d+[\.\)]\s+", line):
            cleaned_task = re.sub(r"^\s*(\d+[\.\)]|[-*+])\s*(\[[ xX]\])?\s*", "", line).strip()

            if ":" in cleaned_task:
                parts = cleaned_task.split(":", 1)
                task_title = parts[0].strip()
                task_desc = parts[1].strip()

                mgr.draw_wrapped_text(
                    f"- {task_title}:",
                    left_margin + 0.25 * inch,
                    mgr.content_width - 0.25 * inch,
                    "Helvetica-Bold",
                    10,
                    13,
                    mgr.text_color,
                )
                if task_desc:
                    mgr.draw_wrapped_text(
                        task_desc,
                        left_margin + 0.4 * inch,
                        mgr.content_width - 0.4 * inch,
                        "Helvetica",
                        9.5,
                        12.5,
                        mgr.text_color,
                    )
            else:
                mgr.draw_wrapped_text(
                    f"- {cleaned_task}",
                    left_margin + 0.25 * inch,
                    mgr.content_width - 0.25 * inch,
                    "Helvetica",
                    9.5,
                    13,
                    mgr.text_color,
                )

        else:
            mgr.draw_wrapped_text(
                line,
                left_margin + 0.1 * inch,
                mgr.content_width - 0.1 * inch,
                "Helvetica",
                9.5,
                13,
                mgr.text_color,
            )

    mgr.draw_footer()
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
