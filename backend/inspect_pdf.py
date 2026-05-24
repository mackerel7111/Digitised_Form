from pathlib import Path
import sys

import fitz


def print_page_summary(page, page_number):
    print("=" * 80)
    print(f"PAGE {page_number}")
    print(f"Size: width={page.rect.width:.2f}, height={page.rect.height:.2f}")
    print()


def print_words(page, limit=80):
    words = page.get_text("words")

    print(f"WORDS ({len(words)} found)")
    print("-" * 80)

    for word in words[:limit]:
        x0, y0, x1, y1, text, block_no, line_no, word_no = word
        print(
            f"text={text!r:<25} "
            f"x0={x0:>7.2f} y0={y0:>7.2f} "
            f"x1={x1:>7.2f} y1={y1:>7.2f} "
            f"block={block_no} line={line_no} word={word_no}"
        )

    if len(words) > limit:
        print(f"... {len(words) - limit} more words not shown")

    print()


def is_mostly_horizontal(rect):
    return rect.width > rect.height * 8 and rect.width > 20


def is_mostly_vertical(rect):
    return rect.height > rect.width * 8 and rect.height > 20


def looks_like_checkbox(rect):
    return 6 <= rect.width <= 30 and 6 <= rect.height <= 30


def print_drawings(page, limit=120):
    drawings = page.get_drawings()

    print(f"DRAWINGS ({len(drawings)} found)")
    print("-" * 80)

    interesting = []

    for drawing in drawings:
        rect = drawing.get("rect")

        if rect is None:
            continue

        kind = "shape"

        if looks_like_checkbox(rect):
            kind = "possible checkbox"
        elif is_mostly_horizontal(rect):
            kind = "possible horizontal line"
        elif is_mostly_vertical(rect):
            kind = "possible vertical line"

        interesting.append((kind, rect, drawing))

    for index, (kind, rect, drawing) in enumerate(interesting[:limit], start=1):
        print(
            f"{index:>3}. {kind:<24} "
            f"x0={rect.x0:>7.2f} y0={rect.y0:>7.2f} "
            f"x1={rect.x1:>7.2f} y1={rect.y1:>7.2f} "
            f"w={rect.width:>7.2f} h={rect.height:>7.2f} "
            f"type={drawing.get('type')}"
        )

    if len(interesting) > limit:
        print(f"... {len(interesting) - limit} more drawings not shown")

    print()


def inspect_pdf(pdf_path):
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Please provide a PDF file")

    with fitz.open(pdf_path) as document:
        print(f"PDF: {pdf_path}")
        print(f"Pages: {document.page_count}")
        print()

        for page_index, page in enumerate(document, start=1):
            print_page_summary(page, page_index)
            print_words(page)
            print_drawings(page)


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print("  python backend/inspect_pdf.py path/to/form.pdf")
        raise SystemExit(1)

    inspect_pdf(sys.argv[1])


if __name__ == "__main__":
    main()