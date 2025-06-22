from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fpdf import FPDF
import os
import uuid
import traceback
import re


router = APIRouter()

TEMP_PDF_DIR = "generated_pdfs"
os.makedirs(TEMP_PDF_DIR, exist_ok=True)

class PDFRequest(BaseModel):
    summary: str

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "Video Summary", ln=1, align="C")
        self.ln(5)

    def chapter_title(self, title):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, title, ln=1)
        self.ln(2)

    def chapter_body(self, body):
        self.set_font("Arial", "", 12)
        self.multi_cell(0, 10, body)
        self.ln()

    def add_summary(self, summary_text):
        # Replace Unicode bullet points with ASCII dashes
        summary_text = summary_text.replace("•", "-")
        # Remove timestamps like [1:30]
        summary_text = re.sub(r'\[\d+:\d+\]', '', summary_text)
        summary_text = summary_text.encode("ascii", "ignore").decode("ascii")

        sections = summary_text.split("**")
        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                title = sections[i].strip(": \n")
                content = sections[i + 1].strip()
                if title and content:
                    self.chapter_title(title)
                    self.chapter_body(content)


@router.post("/download_summary_pdf")
async def download_summary_pdf(request: PDFRequest):
    try:
        print(f"Received PDF request with summary length: {len(request.summary)}")
        print(f"First 200 chars of summary: {request.summary[:200]}")
        
        pdf = PDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Add the summary
        pdf.add_summary(request.summary)

        # Generate unique filename
        filename = f"{uuid.uuid4().hex}.pdf"
        filepath = os.path.join(TEMP_PDF_DIR, filename)
        
        print(f"Attempting to save PDF to: {filepath}")
        
        # Output the PDF
        pdf.output(filepath)
        
        # Verify file was created
        if not os.path.exists(filepath):
            raise Exception(f"PDF file was not created at {filepath}")
        
        file_size = os.path.getsize(filepath)
        print(f"PDF created successfully. File size: {file_size} bytes")
        
        return FileResponse(
            path=filepath,
            filename="video_summary.pdf",
            media_type="application/pdf",
        )
        
    except UnicodeEncodeError as e:
        print(f"Unicode encoding error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to generate PDF due to character encoding issues. Try removing special characters."
        )
    except Exception as e:
        print(f"PDF generation error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")