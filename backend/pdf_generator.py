from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from fpdf import FPDF
import os
import uuid

router = APIRouter()

TEMP_PDF_DIR = "generated_pdfs"
os.makedirs(TEMP_PDF_DIR, exist_ok=True)

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "Video Summary", ln=1, align="C")
        self.ln(5)

    def chapter_title(self, title):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, f"{title}", ln=1)
        self.ln(2)

    def chapter_body(self, body):
        self.set_font("Arial", "", 12)
        self.multi_cell(0, 10, body)
        self.ln()

    def add_summary(self, summary_text):
        sections = summary_text.split("**")
        for i in range(1, len(sections), 2):
            title = sections[i].strip(": \n")
            content = sections[i + 1].strip()
            self.chapter_title(title)
            self.chapter_body(content)

@router.get("/download_summary_pdf")
def download_summary_pdf(
    summary: str = Query(..., description="The video summary to include in the PDF")
):
    try:
        pdf = PDF()
        pdf.add_page()
        pdf.add_summary(summary)

        filename = f"{uuid.uuid4().hex}.pdf"
        filepath = os.path.join(TEMP_PDF_DIR, filename)
        pdf.output(filepath)

        return FileResponse(
            path=filepath,
            filename="video_summary.pdf",
            media_type="application/pdf",
        )
    except Exception as e:
        print(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF.")