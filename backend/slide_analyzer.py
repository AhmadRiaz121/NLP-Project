"""
slide_analyzer.py — Mistral AI Slide Deck Analysis
Extracts text from PDF slide decks and analyzes them using Mistral-medium.
"""

import os
import json
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _slide_cache_key(filepath: str) -> str:
    """Cache key based on file path + last modified time + size."""
    try:
        stat = os.stat(filepath)
        safe_name = os.path.basename(filepath).replace(".", "_")
        return f"slides_analysis_{safe_name}_{int(stat.st_mtime)}_{stat.st_size}"
    except Exception:
        safe_name = os.path.basename(filepath).replace(".", "_")
        return f"slides_analysis_{safe_name}"


def _get_cached_slide_analysis(cache_key: str) -> Dict:
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _set_cached_slide_analysis(cache_key: str, data: Dict) -> None:
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        print(f"[slides] cache write error: {e}")


def _extract_pdf_text_with_pypdf(filepath: str) -> str:
    """Extract text with pypdf/PyPDF2."""
    try:
        try:
            from pypdf import PdfReader
        except Exception:
            from PyPDF2 import PdfReader

        reader = PdfReader(filepath)
        text_parts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- Slide {i + 1} ---\n{page_text}")
        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"[slides] pypdf extraction error: {e}")
        return ""


def _extract_pdf_text_with_pdfplumber(filepath: str) -> str:
    """Fallback extractor for some PDFs where pypdf fails."""
    try:
        import pdfplumber

        text_parts = []
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(f"--- Slide {i + 1} ---\n{page_text}")
        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"[slides] pdfplumber extraction error: {e}")
        return ""


def _extract_pdf_text_with_mistral_ocr(filepath: str, api_key: str) -> str:
    """
    OCR fallback for scanned/image-based slide decks.
    Uses Mistral OCR model via uploaded PDF.
    """
    if not api_key or api_key == "your_mistral_api_key_here":
        return ""

    try:
        from mistralai import Mistral
        from mistralai.models import File

        client = Mistral(api_key=api_key)

        with open(filepath, "rb") as f:
            upload = client.files.upload(
                file=File(
                    fileName=os.path.basename(filepath),
                    content=f,
                    content_type="application/pdf",
                ),
                purpose="ocr",
            )

        file_id = getattr(upload, "id", None)
        if not file_id:
            return ""

        signed = client.files.get_signed_url(file_id=file_id, expiry=1)
        signed_url = getattr(signed, "url", None)
        if not signed_url:
            return ""

        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "document_url", "document_url": signed_url},
        )

        pages = getattr(ocr_response, "pages", []) or []
        text_parts: List[str] = []
        for i, page in enumerate(pages, start=1):
            markdown = getattr(page, "markdown", "") or ""
            if markdown.strip():
                text_parts.append(f"--- Slide {i} ---\n{markdown}")

        return "\n\n".join(text_parts)
    except Exception as e:
        print(f"[slides] Mistral OCR extraction error: {e}")
        return ""


def extract_pdf_text(filepath: str) -> str:
    """Extract text from PDF using multiple strategies."""
    text = _extract_pdf_text_with_pypdf(filepath)
    if text.strip():
        return text

    text = _extract_pdf_text_with_pdfplumber(filepath)
    if text.strip():
        return text

    # Final fallback for scanned PDFs.
    return _extract_pdf_text_with_mistral_ocr(filepath, os.getenv("MISTRAL_API_KEY", ""))


def analyze_slides_with_mistral(pdf_text: str, company_name: str, quarter: str) -> Dict:
    """Analyze slide deck content using Mistral AI."""
    api_key = os.getenv("MISTRAL_API_KEY", "")

    if not api_key or api_key == "your_mistral_api_key_here":
        return _fallback_analysis(pdf_text, company_name, quarter)

    try:
        from mistralai import Mistral

        client = Mistral(api_key=api_key)

        prompt = f"""You are a senior financial analyst. Analyze the following earnings call slide deck for {company_name} ({quarter}).

Provide a structured analysis with the following sections:
1. **Key Financial Metrics**: Extract all important numbers (revenue, profit, margins, growth rates)
2. **Strategic Highlights**: Main strategic themes and initiatives mentioned
3. **Growth Drivers**: Key growth areas and their performance
4. **Risk Factors**: Any risks, challenges, or concerns mentioned
5. **Forward Guidance**: Any forward-looking statements or guidance
6. **Sentiment Assessment**: Overall tone of the slides (bullish/neutral/bearish) with reasoning
7. **Signal vs Noise**: What is actionable information vs generic corporate speak
8. **Key Takeaways**: Top 5 most important points for investors

Slide Deck Content:
{pdf_text[:8000]}
"""

        response = client.chat.complete(
            model="mistral-medium-latest",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000,
        )

        analysis_text = response.choices[0].message.content

        return {
            "status": "success",
            "model": "mistral-medium",
            "analysis": analysis_text,
            "slide_count": pdf_text.count("--- Slide"),
            "total_chars": len(pdf_text),
        }

    except Exception as e:
        print(f"[slides] Mistral analysis error: {e}")
        return _fallback_analysis(pdf_text, company_name, quarter)


def _fallback_analysis(pdf_text: str, company_name: str, quarter: str) -> Dict:
    """Fallback analysis when Mistral API is not available."""
    if not pdf_text:
        return {
            "status": "no_slides",
            "analysis": "No slide deck available for this earnings call.",
            "slide_count": 0,
        }

    # Basic text analysis
    lines = pdf_text.split("\n")
    slide_count = pdf_text.count("--- Slide")

    # Extract numbers (potential financial metrics)
    import re
    numbers = re.findall(r'\$[\d,]+\.?\d*\s*(?:billion|million|B|M)?', pdf_text, re.IGNORECASE)
    percentages = re.findall(r'[\d.]+%', pdf_text)

    # Key financial terms
    financial_terms = ["revenue", "profit", "margin", "growth", "earnings",
                       "cash flow", "guidance", "outlook", "dividend", "buyback"]
    found_terms = [t for t in financial_terms if t.lower() in pdf_text.lower()]

    analysis = f"""## Slide Deck Analysis for {company_name} ({quarter})
*Note: Using basic text analysis. Set MISTRAL_API_KEY for AI-powered analysis.*

### Overview
- **Total Slides**: {slide_count}
- **Content Length**: {len(pdf_text):,} characters

### Financial Figures Detected
{chr(10).join(f'- {n}' for n in numbers[:15]) if numbers else '- No specific dollar amounts detected'}

### Percentages Mentioned
{chr(10).join(f'- {p}' for p in percentages[:15]) if percentages else '- No percentages detected'}

### Key Topics Covered
{chr(10).join(f'- {t.title()}' for t in found_terms) if found_terms else '- No key financial terms detected'}

### Raw Content Preview
{pdf_text[:1500]}...
"""

    return {
        "status": "fallback",
        "model": "text-extraction",
        "analysis": analysis,
        "slide_count": slide_count,
        "total_chars": len(pdf_text),
        "numbers_found": numbers[:15],
        "percentages_found": percentages[:15],
        "topics": found_terms,
    }


def analyze_slide_deck(filepath: str, company_name: str, quarter: str) -> Dict:
    """Full pipeline: extract text → analyze with Mistral."""
    if not filepath or not os.path.exists(filepath):
        return {"status": "no_file", "analysis": "Slide deck file not found."}

    cache_key = _slide_cache_key(filepath)
    cached = _get_cached_slide_analysis(cache_key)
    if cached:
        cached["cached"] = True
        return cached

    pdf_text = extract_pdf_text(filepath)
    if not pdf_text:
        result = {
            "status": "empty",
            "analysis": (
                "Could not extract text from slide deck PDF. "
                "This file may be image-based and OCR was unavailable."
            ),
        }
        _set_cached_slide_analysis(cache_key, result)
        return result

    result = analyze_slides_with_mistral(pdf_text, company_name, quarter)
    result["cached"] = False
    _set_cached_slide_analysis(cache_key, result)
    return result
