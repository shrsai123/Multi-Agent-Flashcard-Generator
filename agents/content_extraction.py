import re
from typing import List
from langchain_core.documents import Document
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from typing import Optional
from core.models import FlashcardState
from vector_store import VectorStoreManager

def extract_text_from_pdf(
    pdf_path: str,
    min_chars_threshold: int = 200,
    ocr_dpi: int = 200,
    max_ocr_pages: Optional[int] = None,
) -> str:
    """
    Extract text from a PDF using:
    1) pypdf
    2) pdfplumber fallback
    3) OCR fallback via pdf2image + pytesseract

    Args:
        pdf_path: path to the PDF file
        min_chars_threshold: if extracted text is shorter than this, try fallback(s)
        ocr_dpi: DPI for PDF-to-image conversion during OCR
        max_ocr_pages: optionally limit OCR to first N pages to control cost/time

    Returns:
        Extracted text as a single string.
    """
    text_parts = []

    # -------------------------
    # 1) Native extraction: pypdf
    # -------------------------
    try:
        from pypdf import PdfReader

        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    except Exception as e:
        print(f"[extract_text_from_pdf] pypdf failed: {e}")

    text = "\n\n".join(text_parts).strip()

    # -------------------------
    # 2) Fallback: pdfplumber
    # -------------------------
    if len(text) < min_chars_threshold:
        text_parts = []
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
        except Exception as e:
            print(f"[extract_text_from_pdf] pdfplumber failed: {e}")

        alt_text = "\n\n".join(text_parts).strip()
        if len(alt_text) > len(text):
            text = alt_text

    # -------------------------
    # 3) OCR fallback: scanned/image PDFs
    # -------------------------
    if len(text) < min_chars_threshold:
        ocr_parts = []
        try:
            from pdf2image import convert_from_path
            import pytesseract

            images = convert_from_path(
                pdf_path,
                dpi=ocr_dpi,
                first_page=1,
                last_page=max_ocr_pages,
            )

            for i, image in enumerate(images, start=1):
                try:
                    page_text = pytesseract.image_to_string(image)
                    if page_text and page_text.strip():
                        ocr_parts.append(page_text.strip())
                except Exception as page_err:
                    print(f"[extract_text_from_pdf] OCR failed on page {i}: {page_err}")

        except Exception as e:
            print(f"[extract_text_from_pdf] OCR fallback unavailable/failed: {e}")

        ocr_text = "\n\n".join(ocr_parts).strip()
        if len(ocr_text) > len(text):
            text = ocr_text

    return text.strip()


def detect_content_type(text: str, llm=None) -> str:
    """Classify content as 'theory', 'code', 'math', or 'mixed'."""
    code_indicators = len(re.findall(
        r'(def |class |import |function |var |let |const |for\s*\(|while\s*\(|return |print\()', text
    ))
    math_indicators = len(re.findall(
        r'(theorem|proof|lemma|∀|∃|∑|∫|equation|derivative|matrix)', text, re.IGNORECASE
    ))
    total_lines = max(len(text.split('\n')), 1)
    code_ratio = code_indicators / total_lines
    math_ratio = math_indicators / total_lines

    if code_ratio > 0.15:
        return "code"
    elif math_ratio > 0.1:
        return "math"
    elif code_ratio > 0.05 and math_ratio > 0.03:
        return "mixed"

    if llm:
        try:
            response = llm.invoke(
                f"Classify this content as exactly one of: theory, code, math, mixed.\n"
                f"Respond with ONLY the classification word.\n\nContent (first 500 chars):\n{text[:500]}"
            )
            content_type = response.content.strip().lower()
            if content_type in ("theory", "code", "math", "mixed"):
                return content_type
        except Exception:
            pass
    return "theory"


def chunk_content(text: str, content_type: str) -> List[Document]:
    """Apply content-type-aware chunking."""
    chunks = []
    if content_type == "code":
        pattern = r'((?:def |class |async def )\S+.*?)(?=\n(?:def |class |async def )|\Z)'
        matches = re.findall(pattern, text, re.DOTALL)
        if not matches:
            matches = [s for s in text.split("\n\n") if s.strip()]
        for i, match in enumerate(matches):
            chunks.append(Document(page_content=match.strip(), metadata={"chunk_index": i, "content_type": "code", "chunk_strategy": "function_boundary"}))
    elif content_type == "math":
        pattern = r'((?:Theorem|Definition|Lemma|Proof|Proposition|Example)\s*[\d.]*.*?)(?=\n(?:Theorem|Definition|Lemma|Proof|Proposition|Example)|\Z)'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        if not matches:
            splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80, separators=["\n\n", "\n"])
            matches = splitter.split_text(text)
        for i, match in enumerate(matches):
            chunks.append(Document(page_content=match.strip(), metadata={"chunk_index": i, "content_type": "math", "chunk_strategy": "concept_boundary"}))
    else:
        chunk_size = 800 if content_type == "theory" else 600
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=100, separators=["\n\n", "\n", ". ", " "])
        split_texts = splitter.split_text(text)
        for i, chunk_text in enumerate(split_texts):
            chunks.append(Document(page_content=chunk_text, metadata={"chunk_index": i, "content_type": content_type, "chunk_strategy": "recursive_character"}))
    return chunks

def content_extraction_node(state: FlashcardState, vector_store: VectorStoreManager, llm=None) -> dict:
    """LangGraph node: Extract content, detect type, chunk, store."""
    pdf_content = state.get("pdf_content", "")
    source_filename = state.get("source_filename", "unknown.pdf")

    if not pdf_content:
        return {"error": "No PDF content provided", "chunks": [], "content_type": "theory"}
    
    print("    → detect_content_type...", flush=True)
    content_type = detect_content_type(pdf_content, llm=llm)
    print(f"    → content_type = {content_type}", flush=True)

    print("    → chunking...", flush=True)
    chunks = chunk_content(pdf_content, content_type)
    print(f"    → {len(chunks)} chunks created", flush=True)

    print("    → embedding + storing in FAISS...", flush=True)
    vector_store.add_course_chunks(chunks, source_filename)
    print("    → done!", flush=True)

    return {"content_type": content_type, "chunks": chunks}