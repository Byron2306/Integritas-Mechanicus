#!/usr/bin/env python3
"""
Minimal document-evidence pipeline for protocol v1.1.

Stdlib-first on purpose:
- plain text / markdown / json / html extraction
- optional PDF extraction via `pdftotext` if available
- image/scan support through native Tesseract OCR or sidecar OCR text files

This does not pretend to be native vision. It prepares bounded OCR evidence
objects that the Presence runtime can reason over lawfully.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional

try:
    from PIL import Image, ImageOps
    import pytesseract
except Exception:  # pragma: no cover - optional OCR dependency
    Image = None  # type: ignore[assignment]
    ImageOps = None  # type: ignore[assignment]
    pytesseract = None  # type: ignore[assignment]


MAX_EXTRACTED_CHARS = 30000
MAX_SPANS = 24
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
SOURCE_TIER_RULES = [
    ("peer_reviewed_or_primary", 0.95, ("doi.org", "arxiv.org", "eric.ed.gov", "plato.stanford.edu", "openalex.org")),
    ("institutional_or_policy", 0.85, (".edu", ".gov", "unesco.org", "oecd.org")),
    ("local_evidence_fixture", 0.75, ("evidence/", "fixtures/", "phase5_", "matrix_gauntlet")),
    ("user_supplied_document", 0.60, ("/home/", "/tmp/")),
]


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        data = data.strip()
        if data:
            self.parts.append(data)

    def text(self) -> str:
        return "\n".join(self.parts)


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _truncate(text: str, max_chars: int = MAX_EXTRACTED_CHARS) -> str:
    text = _clean_text(text)
    if len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head - 40
    return (
        text[:head].rstrip()
        + "\n\n[... middle truncated for context budget ...]\n\n"
        + text[-tail:].lstrip()
    )


def _chunk_text(text: str, max_chars: int = 280) -> List[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    if not blocks:
        blocks = [text.strip()] if text.strip() else []
    chunks: List[str] = []
    for block in blocks:
        if len(block) <= max_chars:
            chunks.append(block)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", block)
        current = ""
        for sentence in sentences:
            candidate = f"{current} {sentence}".strip()
            if current and len(candidate) > max_chars:
                chunks.append(current)
                current = sentence.strip()
            else:
                current = candidate
        if current:
            chunks.append(current)
    return [chunk for chunk in chunks if chunk]


def _build_spans(text: str) -> List[Dict[str, object]]:
    page_parts = re.split(r"\f+", text or "")
    page_aware = len(page_parts) > 1
    candidates: List[Dict[str, object]] = []
    if page_aware:
        for page_index, page_text in enumerate(page_parts, start=1):
            for chunk in _chunk_text(page_text):
                candidates.append({"quote": chunk, "page": page_index, "page_number": page_index})
    else:
        candidates = [{"quote": chunk} for chunk in _chunk_text(text)]

    if len(candidates) > MAX_SPANS:
        head_n = max(6, MAX_SPANS // 3)
        tail_n = max(6, MAX_SPANS // 3)
        middle_n = MAX_SPANS - head_n - tail_n
        middle_start = max(head_n, (len(candidates) // 2) - (middle_n // 2))
        selected = candidates[:head_n] + candidates[middle_start:middle_start + middle_n] + candidates[-tail_n:]
    else:
        selected = candidates

    spans: List[Dict[str, object]] = []
    for index, item in enumerate(selected[:MAX_SPANS], start=1):
        quote = str(item.get("quote") or "").strip()
        if not quote:
            continue
        span: Dict[str, object] = {"span_id": f"S{index}", "quote": quote}
        if item.get("page") not in (None, ""):
            span["page"] = item["page"]
            span["page_number"] = item["page_number"]
            span["locator"] = f"p. {item['page']}"
        spans.append(span)
    return spans


def _uncertainty_notes(text: str) -> List[str]:
    notes: List[str] = []
    lowered = text.lower()
    if any(token in lowered for token in ("[unclear]", "[illegible]", "[missing]", "???")):
        notes.append("source_contains_unreadable_regions")
    if "blurry" in lowered or "blurred" in lowered:
        notes.append("source_mentions_blur_or_scan_loss")
    if "[truncated]" in text:
        notes.append("extraction_truncated_for_context_budget")
    return notes


def _document_quality(
    *,
    parser: str,
    modality: str,
    text: str,
    uncertainty: List[str],
) -> Dict[str, object]:
    """Classify evidence quality for multimodal/document reasoning."""
    text_len = len((text or "").strip())
    suffix = str(modality or "").lower()
    notes = set(uncertainty or [])
    if parser in {"unavailable", "upload_error"} or text_len == 0:
        return {
            "quality": "unreadable",
            "score": 0.0,
            "rationale": "No extractable text/OCR evidence was available.",
        }
    if "ocr_sidecar_missing" in notes:
        return {
            "quality": "image_without_ocr",
            "score": 0.1,
            "rationale": "Image-like evidence was supplied without OCR text; visual claims are unsupported.",
        }
    if any(note in notes for note in ("source_contains_unreadable_regions", "source_mentions_blur_or_scan_loss")):
        return {
            "quality": "partial_ocr",
            "score": 0.45,
            "rationale": "OCR/text contains unreadable or blurry regions; answer only from readable spans.",
        }
    if parser in {"native_tesseract_ocr", "sidecar_ocr", "sidecar_text"} or "ocr" in suffix:
        return {
            "quality": "ocr_supported",
            "score": 0.72 if parser != "native_tesseract_ocr" else 0.76,
            "rationale": "Evidence is mediated through OCR text; quote only readable spans.",
        }
    return {
        "quality": "readable_text",
        "score": 0.9,
        "rationale": "Text extraction produced readable spans.",
    }


def _source_provenance(path: Path, modality: str, text: str) -> Dict[str, object]:
    """Rank source provenance separately from OCR/readability quality."""
    haystack = f"{path.as_posix()} {modality} {text[:1000]}".lower()
    for tier, score, markers in SOURCE_TIER_RULES:
        if any(marker in haystack for marker in markers):
            return {
                "tier": tier,
                "score": score,
                "rationale": f"Matched provenance markers for {tier}.",
            }
    if re.search(r"https?://", haystack):
        return {
            "tier": "web_unknown",
            "score": 0.45,
            "rationale": "Web source present but not in approved high-trust markers.",
        }
    return {
        "tier": "unknown_or_unverified",
        "score": 0.35,
        "rationale": "No strong provenance marker was available.",
    }


def _cross_source_warnings(documents: List[Dict[str, object]]) -> List[str]:
    """Surface obvious conflicts across supplied documents without pretending full NLI."""
    warnings: List[str] = []
    text = "\n".join(str(doc.get("extracted_text") or "") for doc in documents).lower()
    numeric_claims = re.findall(r"\b\d+(?:\.\d+)?\s*(?:percent|%|c|hours|drafts|students)\b", text)
    if len(set(numeric_claims)) >= 3 and any(token in text for token in ("conflict", "disagree", "caption says", "user visual description says")):
        warnings.append("possible_numeric_or_caption_conflict")
    if "native pixel inspection is unavailable" in text or "native vision" in text:
        warnings.append("native_vision_not_available")
    if "ocr confidence is medium" in text or "caption conflicts" in text:
        warnings.append("ocr_caption_conflict_requires_verification")
    return warnings


def _extract_pdf_text(path: Path) -> tuple[str, List[str], str]:
    notes: List[str] = []
    if shutil.which("pdftotext"):
        proc = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout, notes, "pdftotext"
        notes.append("pdftotext_failed")
    else:
        notes.append("pdftotext_unavailable")

    sidecars = [
        path.with_suffix(path.suffix + ".txt"),
        path.with_suffix(".txt"),
        path.parent / f"{path.name}.ocr.txt",
    ]
    for sidecar in sidecars:
        if sidecar.exists():
            notes.append(f"used_sidecar:{sidecar.name}")
            return sidecar.read_text(encoding="utf-8"), notes, "sidecar_text"

    return "", notes, "unavailable"


def _extract_image_sidecar_text(path: Path) -> tuple[str, List[str], str]:
    notes: List[str] = []
    candidates = [
        path.with_suffix(path.suffix + ".ocr.txt"),
        path.with_suffix(path.suffix + ".txt"),
        path.with_suffix(".txt"),
        path.parent / f"{path.stem}.ocr.txt",
    ]
    for candidate in candidates:
        if candidate.exists():
            notes.append(f"used_sidecar:{candidate.name}")
            return candidate.read_text(encoding="utf-8"), notes, "sidecar_ocr"
    notes.append("ocr_sidecar_missing")
    return "", notes, "unavailable"


def _extract_image_ocr_text(path: Path) -> tuple[str, List[str], str]:
    """Extract bounded OCR text from an image, with sidecar fallback.

    OCR is evidence, not sight. Sophia may use readable spans, but must still
    mark uncertainty when OCR is sparse, blurry, or missing.
    """
    notes: List[str] = []
    if pytesseract is not None and Image is not None and ImageOps is not None and shutil.which("tesseract"):
        try:
            with Image.open(path) as image:
                normalized = ImageOps.exif_transpose(image).convert("L")
                text = pytesseract.image_to_string(normalized, lang="eng")
            if text.strip():
                notes.append("native_tesseract_ocr")
                return text, notes, "native_tesseract_ocr"
            notes.append("native_tesseract_empty")
        except Exception as exc:
            notes.append(f"native_tesseract_failed:{type(exc).__name__}")
    else:
        notes.append("native_tesseract_unavailable")

    sidecar_text, sidecar_notes, parser = _extract_image_sidecar_text(path)
    return sidecar_text, notes + sidecar_notes, parser


def _extract_text(path: Path) -> tuple[str, List[str], str]:
    suffix = path.suffix.lower()
    notes: List[str] = []
    if suffix in {".txt", ".md", ".rst", ".csv", ".tsv"}:
        return path.read_text(encoding="utf-8"), notes, "plain_text"
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return json.dumps(payload, indent=2), notes, "json_pretty"
    if suffix in {".html", ".htm"}:
        parser = _HTMLTextExtractor()
        parser.feed(path.read_text(encoding="utf-8"))
        return parser.text(), notes, "html_text"
    if suffix == ".pdf":
        return _extract_pdf_text(path)
    if suffix in IMAGE_SUFFIXES:
        return _extract_image_ocr_text(path)
    return path.read_text(encoding="utf-8"), notes, "fallback_text"


def extract_document_evidence(
    source_path: str | Path,
    *,
    modality: str = "text_only",
    task_label: Optional[str] = None,
    max_chars: int = MAX_EXTRACTED_CHARS,
) -> Dict[str, object]:
    path = Path(source_path)
    extracted_text, extraction_notes, parser = _extract_text(path)
    extracted_text = _truncate(extracted_text, max_chars=max_chars)
    uncertainty = extraction_notes + _uncertainty_notes(extracted_text)
    quality = _document_quality(
        parser=parser,
        modality=modality,
        text=extracted_text,
        uncertainty=uncertainty,
    )
    provenance = _source_provenance(path, modality, extracted_text)
    return {
        "source_path": str(path),
        "source_name": path.name,
        "modality": modality,
        "task_label": task_label,
        "parser": parser,
        "evidence_quality": quality,
        "source_provenance": provenance,
        "extracted_text": extracted_text,
        "spans": _build_spans(extracted_text),
        "uncertainty_notes": uncertainty,
    }


def build_document_evidence_bundle(
    sources: List[Dict[str, object]],
    *,
    evidence_task: Optional[str] = None,
) -> Dict[str, object]:
    documents: List[Dict[str, object]] = []
    for source in sources:
        documents.append(
            extract_document_evidence(
                source["source_path"],
                modality=str(source.get("modality") or "text_only"),
                task_label=str(source.get("task_label") or "") or None,
            )
        )
    return {
        "evidence_task": evidence_task,
        "documents": documents,
        "cross_source_warnings": _cross_source_warnings(documents),
    }


def render_document_evidence_context(bundle: Optional[Dict[str, object]]) -> str:
    if not bundle:
        return ""
    documents = bundle.get("documents") or []
    if not isinstance(documents, list) or not documents:
        return ""

    lines = [
        "[DOCUMENT EVIDENCE CONTRACT]",
        "Use only the provided source evidence unless you explicitly mark an inference.",
        "If the source is blurry, partial, unreadable, or unsupported, say so plainly.",
        "When asked for a quote, quote an exact local phrase from a span or say exact support is absent.",
    ]
    evidence_task = bundle.get("evidence_task")
    if evidence_task:
        lines.append(f"Evidence task: {evidence_task}")

    for index, document in enumerate(documents, start=1):
        lines.append("")
        lines.append(f"[SOURCE {index}] {document.get('source_name')}")
        lines.append(f"modality={document.get('modality')} parser={document.get('parser')}")
        quality = document.get("evidence_quality") or {}
        if quality:
            lines.append(
                f"quality={quality.get('quality')} score={quality.get('score')} rationale={quality.get('rationale')}"
            )
        provenance = document.get("source_provenance") or {}
        if provenance:
            lines.append(
                f"provenance_tier={provenance.get('tier')} provenance_score={provenance.get('score')} rationale={provenance.get('rationale')}"
            )
        uncertainty = document.get("uncertainty_notes") or []
        if uncertainty:
            lines.append("uncertainty=" + ", ".join(str(item) for item in uncertainty))
        warnings = bundle.get("cross_source_warnings") or []
        if warnings:
            lines.append("cross_source_warnings=" + ", ".join(str(item) for item in warnings))
        spans = document.get("spans") or []
        for span in spans:
            lines.append(f"{span.get('span_id')}: {span.get('quote')}")

    return "\n".join(lines)
