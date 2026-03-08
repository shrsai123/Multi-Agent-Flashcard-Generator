import re
from typing import List
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from models import FlashcardState
from vector_store import VectorStoreManager

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using PyPDF (with pdfplumber fallback)."""
    text = ""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
    except Exception:
        pass

    if len(text.strip()) < 100:
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
        except Exception:
            pass
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

    content_type = detect_content_type(pdf_content, llm=llm)
    chunks = chunk_content(pdf_content, content_type)
    vector_store.add_course_chunks(chunks, source_filename)

    return {"content_type": content_type, "chunks": chunks}