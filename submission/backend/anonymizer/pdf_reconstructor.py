
"""Reconstruct PDFs with compact groups of masked words."""

import re
from typing import Sequence

import pymupdf

from anonymizer.extract import extract_text_from_bytes
from anonymizer.masker import mask_with_positions, runs
from anonymizer.spans import Span


def reconstruct_pdf(pdf_data: bytes, spans: Sequence[Span]) -> bytes:
    """Redact sensitive words and draw compact asterisk groups."""

    original_text = extract_text_from_bytes(pdf_data)
    result = mask_with_positions(original_text, spans)

    if result.unmatched:
        raise ValueError("Some sensitive spans could not be matched.")

    if not result.words:
        raise ValueError("No sensitive words found to redact.")

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
    line_number = 0

    with pymupdf.open(
        stream=pdf_data,
        filetype="pdf"
    ) as document:

        # Step 1: Match text words to their PDF coordinates.
        for page_index, page in enumerate(document):
            pdf_words = page.get_text("words", sort=False)
            word_cursor = 0

            page_lines = [
                line
                for line in page.get_text(
                    "text", sort=False
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
                    r"\S+", masked_lines[line_number - 1]
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

                    if pdf_word[4] != original:
                        raise ValueError("PDF text position mismatch.")

                    key = (line_number, index)

                    if key in masked_words:
                        if masked_words[key].word != original:
                            raise ValueError("Masked word mismatch.")

                        word_locations[key] = (
                            page_index,
                            pymupdf.Rect(pdf_word[:4])
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

            # One rectangle covers all words in the run.
            rect = pymupdf.Rect(positions[0][1])

            for _, box in positions[1:]:
                rect |= box

            masked_tokens = re.findall(
                r"\S+", masked_lines[run.line - 1]
            )

            replacement = " ".join(
                masked_tokens[run.first:run.last + 1]
            )

            # Redact the entire run, then insert compact masks.
            document[page_index].add_redact_annot(
                rect,
                text=replacement,
                fontname="helv",
                fontsize=13,
                align=0,
                fill=(1, 1, 1),
                cross_out=False,
            )

            changed_pages.add(page_index)

        # Step 3: Apply redactions and export the PDF.
        for page_index in changed_pages:
            document[page_index].apply_redactions(graphics=0)

        return document.tobytes(
            garbage=4,
            deflate=True
        )
