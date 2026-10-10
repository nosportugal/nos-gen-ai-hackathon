
"""Reconstruct PDFs with compact groups of masked words."""

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import pymupdf

from anonymizer.extract import extract_text_from_bytes, page_textpage
from anonymizer.masker import mask_with_positions, runs
from anonymizer.spans import Span

OCR_PADDING = 1.5  # points around OCR word boxes
# Base-14 Courier Bold: its "*" sits at mid height and reads at small
# sizes; Helvetica's is thin and floats near the cap height.
MASK_FONT = "cobo"


@dataclass(frozen=True)
class _Glyph:
    """One character of a PDF word, with the style of its span."""

    char: str
    origin: pymupdf.Point
    bbox: pymupdf.Rect
    size: float
    color: int


@dataclass(frozen=True)
class _Word:
    """A word of page.get_text("words") and its characters.

    glyphs is None when the characters of the word could not be told
    apart; such a word can be kept, but not masked.
    """

    text: str
    box: pymupdf.Rect
    glyphs: Optional[Tuple[_Glyph, ...]]


@dataclass(frozen=True)
class _Mask:
    """The asterisks that replace one run, drawn after the redactions."""

    page: int
    origin: pymupdf.Point
    size: float
    color: int
    length: float  # room from origin to the run's end
    text: str


def _is_delimiter(char: str) -> bool:
    """What PyMuPDF's word extraction splits words on."""
    code = ord(char)
    return code <= 32 or code == 160 or 0x202A <= code <= 0x202E


def _line_words(line: dict) -> List[List[_Glyph]]:
    """The characters of each word of a rawdict line, in order."""
    words: List[List[_Glyph]] = []
    current: List[_Glyph] = []
    for span in line["spans"]:
        for char in span["chars"]:
            if _is_delimiter(char["c"]):
                if current:
                    words.append(current)
                current = []
                continue
            if not current and char["c"] == "\u200d":
                continue  # a zero width joiner cannot start a word
            current.append(_Glyph(
                char["c"], pymupdf.Point(char["origin"]),
                pymupdf.Rect(char["bbox"]), span["size"], span["color"],
            ))
    if current:
        words.append(current)
    return words


def _page_words(page: pymupdf.Page,
                textpage: Optional[pymupdf.TextPage]) -> List[_Word]:
    """Words in reading order, each with its characters.

    textpage: the OCR of a scanned page, or None for the page's own text.
    Words and characters are read from one text page, so the numbers of
    page.get_text("words") point into page.get_text("rawdict").
    """
    if textpage is None:
        textpage = page.get_textpage(flags=pymupdf.TEXTFLAGS_WORDS)
    lines = {}
    for block in page.get_text("rawdict", textpage=textpage)["blocks"]:
        if block["type"] != 0:
            continue
        for line_index, line in enumerate(block["lines"]):
            for word_index, glyphs in enumerate(_line_words(line)):
                lines[(block["number"], line_index, word_index)] = tuple(
                    glyphs
                )

    words = []
    for word in page.get_text("words", sort=False, textpage=textpage):
        glyphs = lines.get(tuple(word[5:8]))
        if glyphs is None or "".join(g.char for g in glyphs) != word[4]:
            glyphs = None
        words.append(_Word(word[4], pymupdf.Rect(word[:4]), glyphs))
    return words


def _run_length(glyphs: Sequence[_Glyph], origin: pymupdf.Point) -> float:
    """How far the run reaches to the right of `origin`."""
    return max(glyph.bbox.x1 for glyph in glyphs) - origin.x


def _insert_mask(page: pymupdf.Page, mask: _Mask) -> None:
    """Draw the asterisks where the value started, on its baseline.

    Same size and colour as the value, smaller only when the asterisks
    would not fit in the value's width.
    """
    font = pymupdf.Font(MASK_FONT)
    width = font.text_length(mask.text, fontsize=1)
    if mask.length <= 0 or width <= 0 or mask.size <= 0:
        raise ValueError("Invalid mask rectangle; manual review required.")
    fontsize = min(mask.size, mask.length / width)
    page.insert_text(
        mask.origin, mask.text, fontname=MASK_FONT, fontsize=fontsize,
        color=pymupdf.sRGB_to_pdf(mask.color),
    )


def _save_pdf(document: pymupdf.Document) -> bytes:
    """Clear PDF metadata and export the document."""

    document.set_metadata({})
    document.del_xml_metadata()

    return document.tobytes(
        garbage=4,
        deflate=True,
    )


def reconstruct_pdf(
    pdf_data: bytes,
    spans: Sequence[Span],
) -> bytes:
    """Reconstruct a PDF and return its anonymized bytes."""

    pdf_bytes, _ = reconstruct_pdf_with_report(
        pdf_data,
        spans,
    )

    return pdf_bytes


def reconstruct_pdf_with_report(
    pdf_data: bytes,
    spans: Sequence[Span],
) -> Tuple[bytes, List[Span]]:
    """Redact matched words and report unmatched sensitive spans.

    Raise ValueError for ambiguous geometry that needs manual review.
    This does not audit sensitive data in annotations or attachments.
    """

    original_text = extract_text_from_bytes(pdf_data)
    result = mask_with_positions(original_text, spans)

    # A document without sensitive words is a valid case.
    # Still clear its metadata before exporting.
    if not result.words:
        with pymupdf.open(
            stream=pdf_data,
            filetype="pdf",
        ) as document:
            return _save_pdf(document), result.unmatched

    original_lines = original_text.split("\n")
    masked_lines = result.text.split("\n")

    if len(original_lines) != len(masked_lines):
        raise ValueError("Masking changed the line count.")

    masked_words = {
        (word.line, word.index): word
        for word in result.words
    }

    if len(masked_words) != len(result.words):
        raise ValueError("Duplicate masked word positions.")

    word_locations = {}
    page_word_locations = {}
    rotated_lines = {}
    ocr_pages = set()
    line_number = 0

    with pymupdf.open(
        stream=pdf_data,
        filetype="pdf",
    ) as document:

        # Step 1: Match text words to PDF coordinates.
        for page_index, page in enumerate(document):
            # Scanned pages: OCR words and their boxes, as extract saw them.
            ocr = page_textpage(page)
            if ocr is not None:
                ocr_pages.add(page_index)
            pdf_words = _page_words(page, ocr)
            word_cursor = 0
            page_word_locations[page_index] = []
            rotated_lines[page_index] = [
                pymupdf.Rect(line["bbox"])
                for block in page.get_text(
                    "dict", flags=(
                        pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
                    ), textpage=ocr,
                )["blocks"]
                if block["type"] == 0
                for line in block["lines"]
                if line["dir"] != (1.0, 0.0)
            ]

            # Same lines as extract_text(), which drops the trailing
            # space PyMuPDF leaves on Word PDFs (#14).
            page_lines = [
                line.rstrip()
                for line in page.get_text(
                    "text", sort=False, textpage=ocr,
                ).split("\n")
                if line.strip()
            ]

            for line in page_lines:
                line_number += 1

                if (
                    line_number > len(original_lines)
                    or line != original_lines[line_number - 1]
                ):
                    raise ValueError("PDF line alignment failed.")

                original_tokens = re.findall(r"\S+", line)

                masked_tokens = re.findall(
                    r"\S+",
                    masked_lines[line_number - 1],
                )

                if len(original_tokens) != len(masked_tokens):
                    raise ValueError("Masking changed the word count.")

                for index, (original, masked) in enumerate(
                    zip(original_tokens, masked_tokens)
                ):
                    if word_cursor >= len(pdf_words):
                        raise ValueError("PDF word alignment failed.")

                    pdf_word = pdf_words[word_cursor]
                    word_cursor += 1

                    if pdf_word.text != original:
                        raise ValueError("PDF text position mismatch.")

                    key = (line_number, index)
                    page_word_locations[page_index].append((key, pdf_word))

                    if key in masked_words:
                        if masked_words[key].word != original:
                            raise ValueError("Masked word mismatch.")

                        word_locations[key] = (
                            page_index,
                            pdf_word,
                        )

                    elif original != masked:
                        raise ValueError("Unexpected text modification.")

            if word_cursor != len(pdf_words):
                raise ValueError("PDF word alignment incomplete.")

        if (
            line_number != len(original_lines)
            or set(word_locations) != set(masked_words)
        ):
            raise ValueError("Not all masked words were located.")

        # Step 2: Group consecutive sensitive words.
        changed_pages = set()
        masks = []

        for run in runs(result.words):
            positions = [
                word_locations[(run.line, index)]
                for index in range(run.first, run.last + 1)
            ]

            page_indexes = {
                page_index for page_index, _ in positions
            }

            if len(page_indexes) != 1:
                raise ValueError("Masked run crosses PDF pages.")

            page_index = positions[0][0]
            words = [word for _, word in positions]
            if any(word.glyphs is None for word in words):
                raise ValueError(
                    "Masked text has no clear position on page "
                    f"{page_index + 1}; manual review required."
                )
            glyphs = [glyph for word in words for glyph in word.glyphs]

            # One rectangle covers the entire sensitive run.
            rect = pymupdf.Rect(words[0].box)

            for word in words[1:]:
                rect |= word.box

            # OCR boxes hug the glyphs; pad them so no sliver of a
            # letter is left in the scanned image.
            if page_index in ocr_pages:
                rect = pymupdf.Rect(
                    rect.x0 - OCR_PADDING, rect.y0 - OCR_PADDING,
                    rect.x1 + OCR_PADDING, rect.y1 + OCR_PADDING,
                )

            # MuPDF removes every character whose box overlaps this area.
            # Reject ambiguous geometry before returning a damaged document.
            if any(
                key not in masked_words and rect.intersects(word.box)
                for key, word in page_word_locations[page_index]
            ):
                raise ValueError(
                    "Redaction overlaps unmarked text on page "
                    f"{page_index + 1}; manual review required."
                )
            if any(rect.intersects(box)
                   for box in rotated_lines[page_index]):
                raise ValueError(
                    "Rotated sensitive text requires manual review."
                )
            if any(document[page_index].annots(
                types=[pymupdf.PDF_ANNOT_REDACT],
            )) and page_index not in changed_pages:
                raise ValueError(
                    "Existing redaction annotations require manual review."
                )

            masked_tokens = re.findall(
                r"\S+",
                masked_lines[run.line - 1],
            )

            replacement = " ".join(
                masked_tokens[run.first:run.last + 1]
            )

            # Remove text first; insert masks after all redactions are applied.
            # fill=False keeps the area transparent, so cell colours and
            # table lines underneath stay; apply_redactions() still deletes
            # the text. (fill=None would mean white in PyMuPDF.)
            document[page_index].add_redact_annot(
                rect,
                fill=False,
                cross_out=False,
            )

            changed_pages.add(page_index)
            origin = glyphs[0].origin
            masks.append(_Mask(
                page_index, origin, glyphs[0].size,
                # OCR text has no colour of its own: the scan is erased
                # to white, so draw black.
                0 if page_index in ocr_pages else glyphs[0].color,
                _run_length(glyphs, origin), replacement,
            ))

        # Step 3: Apply redactions to the affected pages.
        for page_index in changed_pages:
            # images: on scanned pages the words are pixels, so the
            # pixels under each masked run are erased from the image.
            document[page_index].apply_redactions(
                images=pymupdf.PDF_REDACT_IMAGE_PIXELS, graphics=0,
            )

        for mask in masks:
            _insert_mask(document[mask.page], mask)

        # Step 4: Clear metadata and export the PDF.
        return _save_pdf(document), result.unmatched
