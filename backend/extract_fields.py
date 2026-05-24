from pathlib import Path
import json
import re
import sys

import fitz


HEADER_CUTOFF_Y = 100
FOOTER_CUTOFF_FROM_BOTTOM = 45

LABEL_MAX_VERTICAL_GAP = 8
LABEL_MAX_HORIZONTAL_GAP = 30

CHECKBOX_MIN_SIZE = 7
CHECKBOX_MAX_SIZE = 18

FULL_WIDTH_LINE_RATIO = 0.7


def normalize_rect(rect, page):
    return {
        "x": round(rect.x0 / page.rect.width, 4),
        "y": round(rect.y0 / page.rect.height, 4),
        "w": round(rect.width / page.rect.width, 4),
        "h": round(rect.height / page.rect.height, 4),
    }


def clean_label(text):
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = text.rstrip(":")

    parts = text.split()

    if len(parts) % 2 == 0:
        midpoint = len(parts) // 2
        if parts[:midpoint] == parts[midpoint:]:
            text = " ".join(parts[:midpoint])

    return text


def slugify(text):
    value = clean_label(text).lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = value.strip("_")
    return value or "field"


def word_dict(raw_word):
    x0, y0, x1, y1, text, block_no, line_no, word_no = raw_word

    return {
        "text": text,
        "rect": fitz.Rect(x0, y0, x1, y1),
        "block": block_no,
        "line": line_no,
        "word": word_no,
    }

def dedupe_words(words):
    deduped = []
    seen = set()

    for word in words:
        rect = word["rect"]
        key = (
            word["text"],
            round(rect.x0, 1),
            round(rect.y0, 1),
            round(rect.x1, 1),
            round(rect.y1, 1),
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(word)

    return deduped

def in_body(rect, page):
    return (
        rect.y0 >= HEADER_CUTOFF_Y
        and rect.y1 <= page.rect.height - FOOTER_CUTOFF_FROM_BOTTOM
        and rect.x0 >= 0
        and rect.x1 <= page.rect.width
    )


def is_horizontal_line(rect, page):
    if not in_body(rect, page):
        return False

    if rect.height > 1.5:
        return False

    if rect.width < 40:
        return False

    return True


def is_full_width_line(rect, page):
    return rect.width >= page.rect.width * FULL_WIDTH_LINE_RATIO


def is_checkbox(rect, page):
    if not in_body(rect, page):
        return False

    if rect.width <= 0 or rect.height <= 0:
        return False

    width_ok = CHECKBOX_MIN_SIZE <= rect.width <= CHECKBOX_MAX_SIZE
    height_ok = CHECKBOX_MIN_SIZE <= rect.height <= CHECKBOX_MAX_SIZE
    roughly_square = 0.65 <= rect.width / rect.height <= 1.35

    return width_ok and height_ok and roughly_square


def is_large_text_area(rect, page):
    if not in_body(rect, page):
        return False

    return rect.width > page.rect.width * 0.45 and rect.height > 40


def get_words_on_same_row(words, rect, side):
    row_words = []

    for word in words:
        word_rect = word["rect"]
        line_y = rect.y0
        vertically_close = word_rect.y0 - LABEL_MAX_VERTICAL_GAP <= line_y <= word_rect.y1 + LABEL_MAX_VERTICAL_GAP

        if not vertically_close:
            continue

        if side == "left" and word_rect.x1 <= rect.x0:
            row_words.append(word)

        if side == "right" and word_rect.x0 >= rect.x1:
            row_words.append(word)

    return sorted(row_words, key=lambda word: word["rect"].x0)


def get_label_left_of_line(words, line_rect):
    left_words = get_words_on_same_row(words, line_rect, "left")

    if not left_words:
        return None

    nearby_words = []

    for word in reversed(left_words):
        if not nearby_words:
            if line_rect.x0 - word["rect"].x1 <= LABEL_MAX_HORIZONTAL_GAP:
                nearby_words.append(word)
            continue

        previous_word = nearby_words[-1]
        if previous_word["rect"].x0 - word["rect"].x1 <= 12:
            nearby_words.append(word)
        else:
            break

    nearby_words = list(reversed(nearby_words))

    if not nearby_words:
        return None

    return clean_label(" ".join(word["text"] for word in nearby_words))


def get_option_label_right_of_checkbox(words, checkbox_rect):
    candidates = []
    checkbox_center_y = rect_center_y(checkbox_rect)

    for word in words:
        word_rect = word["rect"]
        word_center_y = rect_center_y(word_rect)

        vertically_close = abs(word_center_y - checkbox_center_y) <= 7

        if not vertically_close:
            continue

        if word_rect.x0 >= checkbox_rect.x1:
            gap = word_rect.x0 - checkbox_rect.x1

            if gap <= 35:
                candidates.append((gap, word))

    if not candidates:
        return None

    candidates = sorted(candidates, key=lambda item: item[0])
    first_word = candidates[0][1]
    label_words = [first_word]

    for _, word in candidates[1:]:
        previous = label_words[-1]

        if word["rect"].x0 - previous["rect"].x1 <= 8:
            label_words.append(word)
        else:
            break

    return clean_label(" ".join(word["text"] for word in label_words))

def get_group_label_left_of_checkbox(words, checkbox_rect):
    left_words = []

    for word in words:
        word_rect = word["rect"]

        vertically_close = (
            word_rect.y0 - 8 <= checkbox_rect.y0 <= word_rect.y1 + 8
            or checkbox_rect.y0 - 8 <= word_rect.y0 <= checkbox_rect.y1 + 8
        )

        if not vertically_close:
            continue

        if word_rect.x1 <= checkbox_rect.x0:
            left_words.append(word)

    if not left_words:
        return None

    left_words = sorted(left_words, key=lambda word: word["rect"].x0)

    # If a row has several checkbox options, use the text before the first checkbox as the group.
    group_words = []

    for word in left_words:
        group_words.append(word)

    if not group_words:
        return None

    return clean_label(" ".join(word["text"] for word in group_words))

def label_looks_like_date(label):
    label_lower = label.lower()

    return any(
        marker in label_lower
        for marker in ["date", "dd/mm/yyyy", "mm/yyyy", "month", "year"]
    )


def field_type_from_label(label):
    if label_looks_like_date(label):
        return "date"

    return "text"


def make_unique_id(base_id, used_ids):
    candidate = base_id
    counter = 2

    while candidate in used_ids:
        candidate = f"{base_id}_{counter}"
        counter += 1

    used_ids.add(candidate)
    return candidate


def extract_drawings(page):
    drawings = []

    for drawing in page.get_drawings():
        rect = drawing.get("rect")

        if rect is None:
            continue

        drawings.append(rect)

    return drawings


def extract_text_line_fields(page, words, drawings, used_ids):
    fields = []

    for rect in drawings:
        if not is_horizontal_line(rect, page):
            continue

        if is_full_width_line(rect, page):
            continue

        label = get_label_left_of_line(words, rect)

        if not label:
            continue

        # Put a little height above the physical line so text has room to render.
        input_rect = fitz.Rect(rect.x0, rect.y0 - 12, rect.x1, rect.y0 + 4)

        field_id = make_unique_id(slugify(label), used_ids)

        fields.append(
            {
                "id": field_id,
                "label": label,
                "type": field_type_from_label(label),
                "page": page.number + 1,
                "rect": normalize_rect(input_rect, page),
                "confidence": 0.82,
                "reason": "horizontal line with label on the left",
            }
        )

    return fields

def rect_center_y(rect):
    return rect.y0 + (rect.height / 2)

def checkbox_row_key(rect):
    return round(rect.y0 / 8)

def group_checkboxes_by_row(checkbox_rects):
    rows = {}

    for rect in checkbox_rects:
        key = checkbox_row_key(rect)
        rows.setdefault(key, []).append(rect)

    return rows

def get_words_left_of_x_on_checkbox_row(words, row_rect, x_limit):
    row_words = []
    row_center_y = rect_center_y(row_rect)

    for word in words:
        word_rect = word["rect"]
        word_center_y = rect_center_y(word_rect)

        vertically_close = abs(word_center_y - row_center_y) <= 7

        if not vertically_close:
            continue

        if word_rect.x1 <= x_limit:
            row_words.append(word)

    return sorted(row_words, key=lambda word: word["rect"].x0)

def extract_checkbox_fields(page, words, drawings, used_ids):
    fields = []

    checkbox_rects = [rect for rect in drawings if is_checkbox(rect, page)]
    checkbox_rows = group_checkboxes_by_row(checkbox_rects)

    for row_rects in checkbox_rows.values():
        row_rects = sorted(row_rects, key=lambda rect: rect.x0)
        leftmost_checkbox = row_rects[0]

        group_words = get_words_left_of_x_on_checkbox_row(
            words,
            leftmost_checkbox,
            leftmost_checkbox.x0,
        )

        group = clean_label(" ".join(word["text"] for word in group_words)) if group_words else None

        for rect in row_rects:
            label = get_option_label_right_of_checkbox(words, rect)

            if not label:
                continue

            # Avoid treating date character boxes as checkboxes.
            if re.fullmatch(r"[:/.-]+", label):
                continue

            if group:
                field_id_base = f"{group} {label}"
            else:
                field_id_base = label

            field_id = make_unique_id(slugify(field_id_base), used_ids)

            fields.append(
                {
                    "id": field_id,
                    "label": label,
                    "group": group,
                    "type": "checkbox",
                    "page": page.number + 1,
                    "rect": normalize_rect(rect, page),
                    "confidence": 0.72,
                    "reason": "small square with option label on the right",
                }
            )

    return fields


def find_nearby_heading_above(words, rect):
    candidates = []

    for word in words:
        word_rect = word["rect"]

        above = word_rect.y1 <= rect.y0
        close = rect.y0 - word_rect.y1 <= 30
        horizontally_near = word_rect.x0 <= rect.x1 and word_rect.x1 >= rect.x0

        if above and close and horizontally_near:
            candidates.append(word)

    if not candidates:
        return None

    candidates = sorted(candidates, key=lambda word: (word["rect"].y0, word["rect"].x0))
    return clean_label(" ".join(word["text"] for word in candidates))


def extract_multiline_fields(page, words, drawings, used_ids):
    fields = []

    for rect in drawings:
        if not is_large_text_area(rect, page):
            continue

        label = find_nearby_heading_above(words, rect)

        if not label:
            continue

        label_lower = label.lower()

        if not any(marker in label_lower for marker in ["note", "comment", "action", "follow"]):
            continue

        field_id = make_unique_id(slugify(label), used_ids)

        fields.append(
            {
                "id": field_id,
                "label": label,
                "type": "multiline",
                "page": page.number + 1,
                "rect": normalize_rect(rect, page),
                "confidence": 0.76,
                "reason": "large writable area below notes/comments label",
            }
        )

    return fields

def rects_are_close(rect_a, rect_b, tolerance=0.003):
    return (
        abs(rect_a["x"] - rect_b["x"]) <= tolerance
        and abs(rect_a["y"] - rect_b["y"]) <= tolerance
        and abs(rect_a["w"] - rect_b["w"]) <= tolerance
        and abs(rect_a["h"] - rect_b["h"]) <= tolerance
    )


def dedupe_fields(fields):
    deduped = []

    for field in fields:
        is_duplicate = False

        for existing in deduped:
            same_identity = (
                field["page"] == existing["page"]
                and field["type"] == existing["type"]
                and field["label"].lower() == existing["label"].lower()
            )

            if same_identity and rects_are_close(field["rect"], existing["rect"]):
                is_duplicate = True
                break

        if not is_duplicate:
            deduped.append(field)

    return sorted(
        deduped,
        key=lambda field: (
            field["page"],
            field["rect"]["y"],
            field["rect"]["x"],
            field["label"],
        ),
    )

def extract_fields(pdf_path):
    pdf_path = Path(pdf_path)
    all_fields = []
    used_ids = set()

    with fitz.open(pdf_path) as document:
        for page in document:
            words = dedupe_words([word_dict(raw_word) for raw_word in page.get_text("words")])
            drawings = extract_drawings(page)

            all_fields.extend(extract_text_line_fields(page, words, drawings, used_ids))
            all_fields.extend(extract_checkbox_fields(page, words, drawings, used_ids))
            all_fields.extend(extract_multiline_fields(page, words, drawings, used_ids))

    return {
        "source": str(pdf_path),
        "fields": dedupe_fields(all_fields),
    }


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print("  python backend/extract_fields.py path/to/form.pdf")
        raise SystemExit(1)

    result = extract_fields(sys.argv[1])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()