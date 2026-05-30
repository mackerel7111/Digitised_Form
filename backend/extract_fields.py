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

TABLE_MIN_COLUMNS = 2
TABLE_MIN_ROWS = 2
TABLE_LINE_TOLERANCE = 1.5
TABLE_POSITION_TOLERANCE = 2.0
TABLE_CELL_PADDING = 1.0


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

    if rect.height > 3:
        return False

    if rect.width < 40:
        return False

    return True


def is_full_width_line(rect, page):
    return rect.width >= page.rect.width * FULL_WIDTH_LINE_RATIO


def is_vertical_line(rect, page):
    if not in_body(rect, page):
        return False

    if rect.width > 3:
        return False
    if rect.height < 40:
        return False

    return True


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


def thin_rect_from_points(p1, p2, thickness=0.6):
    x0 = min(p1.x, p2.x)
    x1 = max(p1.x, p2.x)
    y0 = min(p1.y, p2.y)
    y1 = max(p1.y, p2.y)

    # Vertical line
    if abs(x1 - x0) < thickness:
        x0 -= thickness / 2
        x1 += thickness / 2

    # Horizontal line
    if abs(y1 - y0) < thickness:
        y0 -= thickness / 2
        y1 += thickness / 2

    return fitz.Rect(x0, y0, x1, y1)


def rect_to_border_lines(rect, thickness=0.6):
    return [
        fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + thickness),  # top
        fitz.Rect(rect.x0, rect.y1 - thickness, rect.x1, rect.y1),  # bottom
        fitz.Rect(rect.x0, rect.y0, rect.x0 + thickness, rect.y1),  # left
        fitz.Rect(rect.x1 - thickness, rect.y0, rect.x1, rect.y1),  # right
    ]


def extract_drawings(page):
    """
    Extract usable line rectangles from PDF vector drawings.

    Important:
    PyMuPDF drawing paths may contain many line/rectangle items.
    Using only drawing["rect"] loses the internal table grid structure.
    """
    lines = []

    for drawing in page.get_drawings():
        for item in drawing.get("items", []):
            operator = item[0]

            # Straight line item: ("l", point1, point2)
            if operator == "l":
                rect = thin_rect_from_points(item[1], item[2])

                if in_body(rect, page):
                    lines.append(rect)

            # Rectangle item: ("re", rect, orientation)
            elif operator == "re":
                rect = item[1]

                if not in_body(rect, page):
                    continue

                for border in rect_to_border_lines(rect):
                    if in_body(border, page):
                        lines.append(border)

    return lines


def extract_text_line_fields(page, words, drawings, used_ids, excluded_regions=None):
    fields = []

    for rect in drawings:
        if not is_horizontal_line(rect, page):
            continue

        if excluded_regions and any(rect_inside_region(rect, region) for region in excluded_regions):
            continue

        if is_full_width_line(rect, page):
            continue

        label = get_label_left_of_line(words, rect)

        if not label:
            continue

        # Put a little height above the physical line so text has room to render.
        input_rect = fitz.Rect(rect.x0, rect.y0 - 16, rect.x1, rect.y0)

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


def rect_center_x(rect):
    return rect.x0 + (rect.width / 2)


def rect_inside_region(rect, region, padding=1.5):
    return (
        rect.x0 >= region.x0 - padding
        and rect.x1 <= region.x1 + padding
        and rect.y0 >= region.y0 - padding
        and rect.y1 <= region.y1 + padding
    )


def lines_intersect(horizontal_rect, vertical_rect, tolerance=TABLE_LINE_TOLERANCE):
    line_y = rect_center_y(horizontal_rect)
    line_x = rect_center_x(vertical_rect)

    return (
        horizontal_rect.x0 - tolerance <= line_x <= horizontal_rect.x1 + tolerance
        and vertical_rect.y0 - tolerance <= line_y <= vertical_rect.y1 + tolerance
    )


def group_positions(values, tolerance=TABLE_POSITION_TOLERANCE):
    if not values:
        return []

    values = sorted(values)
    grouped = []
    bucket = [values[0]]

    for value in values[1:]:
        if abs(value - bucket[-1]) <= tolerance:
            bucket.append(value)
        else:
            grouped.append(sum(bucket) / len(bucket))
            bucket = [value]

    grouped.append(sum(bucket) / len(bucket))
    return grouped

def merge_horizontal_lines(lines, y_tolerance=2.0, gap_tolerance=4.0):
    lines = sorted(lines, key=lambda rect: (rect_center_y(rect), rect.x0))
    merged = []

    for rect in lines:
        if not merged:
            merged.append(rect)
            continue

        last = merged[-1]

        same_y = abs(rect_center_y(rect) - rect_center_y(last)) <= y_tolerance
        close_or_touching = rect.x0 - last.x1 <= gap_tolerance
        overlaps_x = rect.x0 <= last.x1 + gap_tolerance

        if same_y and (close_or_touching or overlaps_x):
            merged[-1] = fitz.Rect(
                min(last.x0, rect.x0),
                min(last.y0, rect.y0),
                max(last.x1, rect.x1),
                max(last.y1, rect.y1),
            )
        else:
            merged.append(rect)

    return merged

def merge_vertical_lines(lines, x_tolerance=2.0, gap_tolerance=4.0):
    lines = sorted(lines, key=lambda rect: (rect_center_x(rect), rect.y0))
    merged = []

    for rect in lines:
        if not merged:
            merged.append(rect)
            continue

        last = merged[-1]

        same_x = abs(rect_center_x(rect) - rect_center_x(last)) <= x_tolerance
        close_or_touching = rect.y0 - last.y1 <= gap_tolerance
        overlaps_y = rect.y0 <= last.y1 + gap_tolerance

        if same_x and (close_or_touching or overlaps_y):
            merged[-1] = fitz.Rect(
                min(last.x0, rect.x0),
                min(last.y0, rect.y0),
                max(last.x1, rect.x1),
                max(last.y1, rect.y1),
            )
        else:
            merged.append(rect)

    return merged

def get_words_in_rect(words, rect):
    return [word for word in words if word["rect"].intersects(rect)]


def get_cell_text(words, rect):
    cell_words = get_words_in_rect(words, rect)

    if not cell_words:
        return ""

    cell_words = sorted(cell_words, key=lambda word: word["rect"].x0)
    return clean_label(" ".join(word["text"] for word in cell_words))


def build_table_components(horizontal_lines, vertical_lines):
    adjacency = {}

    for index in range(len(horizontal_lines)):
        adjacency[("h", index)] = set()

    for index in range(len(vertical_lines)):
        adjacency[("v", index)] = set()

    for h_index, h_rect in enumerate(horizontal_lines):
        for v_index, v_rect in enumerate(vertical_lines):
            if lines_intersect(h_rect, v_rect):
                adjacency[("h", h_index)].add(("v", v_index))
                adjacency[("v", v_index)].add(("h", h_index))

    visited = set()
    components = []

    for node, neighbors in adjacency.items():
        if node in visited or not neighbors:
            continue

        queue = [node]
        visited.add(node)
        component_h = []
        component_v = []

        while queue:
            current = queue.pop(0)
            current_type, current_index = current

            if current_type == "h":
                component_h.append(horizontal_lines[current_index])
            else:
                component_v.append(vertical_lines[current_index])

            for neighbor in adjacency[current]:
                if neighbor in visited:
                    continue

                visited.add(neighbor)
                queue.append(neighbor)

        if component_h and component_v:
            components.append((component_h, component_v))

    return components


def build_table_fields_from_lines(page, words, horizontal_lines, vertical_lines, used_ids, table_index):
    x_positions = group_positions([rect_center_x(rect) for rect in vertical_lines])
    y_positions = group_positions([rect_center_y(rect) for rect in horizontal_lines])

    if len(x_positions) < TABLE_MIN_COLUMNS + 1 or len(y_positions) < TABLE_MIN_ROWS + 1:
        return [], None

    row_count = len(y_positions) - 1
    column_count = len(x_positions) - 1

    cell_rects = []

    for row_index in range(row_count):
        row_rects = []
        for column_index in range(column_count):
            x0 = x_positions[column_index] + TABLE_CELL_PADDING
            x1 = x_positions[column_index + 1] - TABLE_CELL_PADDING
            y0 = y_positions[row_index] + TABLE_CELL_PADDING
            y1 = y_positions[row_index + 1] - TABLE_CELL_PADDING
            row_rects.append(fitz.Rect(x0, y0, x1, y1))
        cell_rects.append(row_rects)

    header_row_index = None
    header_texts = [""] * column_count

    if row_count > 0:
        header_texts = [
            get_cell_text(words, cell_rects[0][column_index])
            for column_index in range(column_count)
        ]

        if sum(1 for text in header_texts if text) >= 2:
            header_row_index = 0

    row_label_col_index = None
    row_label_texts = [""] * row_count

    if column_count > 0:
        row_label_texts = [
            get_cell_text(words, cell_rects[row_index][0])
            for row_index in range(row_count)
        ]

        label_texts = row_label_texts[1:] if header_row_index == 0 else row_label_texts

        if sum(1 for text in label_texts if text) >= 2:
            row_label_col_index = 0

    table_rect = fitz.Rect(
        min(rect.x0 for rect in vertical_lines),
        min(rect.y0 for rect in horizontal_lines),
        max(rect.x1 for rect in vertical_lines),
        max(rect.y1 for rect in horizontal_lines),
    )

    fields = []

    for row_index in range(row_count):
        if header_row_index is not None and row_index == header_row_index:
            continue

        for column_index in range(column_count):
            if row_label_col_index is not None and column_index == row_label_col_index:
                continue

            cell_rect = cell_rects[row_index][column_index]

            if get_words_in_rect(words, cell_rect):
                continue

            label_parts = []
            row_label = row_label_texts[row_index] if row_label_col_index == 0 else ""
            column_label = header_texts[column_index] if header_row_index == 0 else ""

            if row_label:
                label_parts.append(row_label)

            if column_label:
                label_parts.append(column_label)

            if label_parts:
                label = " - ".join(label_parts)
            else:
                label = f"Table {table_index} R{row_index + 1} C{column_index + 1}"

            field_id = make_unique_id(slugify(label), used_ids)

            fields.append(
                {
                    "id": field_id,
                    "label": label,
                    "type": field_type_from_label(label),
                    "page": page.number + 1,
                    "rect": normalize_rect(cell_rect, page),
                    "confidence": 0.58,
                    "reason": "table grid cell",

                    # Table grouping metadata for frontend display
                    "tableId": f"table_{page.number + 1}_{table_index}",
                    "tableName": f"Table {table_index}",
                    "tableRow": row_index + 1,
                    "tableColumn": column_index + 1,
                    "tableRows": row_count,
                    "tableColumns": column_count,
                }
            )

    return fields, table_rect

def extract_table_fields_with_pymupdf(page, words, used_ids):
    """
    First-pass table extraction using PyMuPDF's built-in table finder.

    This is useful when tables are detected structurally by PyMuPDF,
    even if our custom vector-line detector misses them.
    """
    fields = []
    table_regions = []

    if not hasattr(page, "find_tables"):
        return [], []

    try:
        table_result = page.find_tables()
    except Exception:
        return [], []

    tables = getattr(table_result, "tables", [])

    for table_index, table in enumerate(tables, start=1):
        table_rect = fitz.Rect(table.bbox)
        table_regions.append(table_rect)

        cells = getattr(table, "cells", None)

        if not cells:
            continue

        # Compute grid positions once per table, before iterating cells.
        cell_rects = [fitz.Rect(cell) for cell in cells if cell is not None]
        x_positions = group_cell_positions([rect_center_x(rect) for rect in cell_rects])
        y_positions = group_cell_positions([rect_center_y(rect) for rect in cell_rects])
        column_count = len(x_positions)
        row_count = len(y_positions)

        for cell_index, cell in enumerate(cells, start=1):
            if cell is None:
                continue

            cell_rect = fitz.Rect(cell)

            if not in_body(cell_rect, page):
                continue

            # Skip cells that already contain printed text.
            if get_words_in_rect(words, cell_rect):
                continue

            # Find 1-based row/column index by closest position.
            cx = rect_center_x(cell_rect)
            cy = rect_center_y(cell_rect)
            column_index = min(range(len(x_positions)), key=lambda i: abs(x_positions[i] - cx)) + 1
            row_index = min(range(len(y_positions)), key=lambda i: abs(y_positions[i] - cy)) + 1

            field_id = make_unique_id(
                f"table_{table_index}_cell_{cell_index}",
                used_ids,
            )

            fields.append(
                {
                    "id": field_id,
                    "label": f"Table {table_index} R{row_index} C{column_index}",
                    "type": "text",
                    "page": page.number + 1,
                    "rect": normalize_rect(cell_rect, page),
                    "confidence": 0.7,
                    "reason": "PyMuPDF detected empty table cell",

                    # Table grouping metadata for frontend display
                    "tableId": f"table_{page.number + 1}_{table_index}",
                    "tableName": f"Table {table_index}",
                    "tableRow": row_index,
                    "tableColumn": column_index,
                    "tableRows": row_count,
                    "tableColumns": column_count,
                }
            )

    return fields, table_regions

def extract_table_fields(page, words, drawings, used_ids):
    # 1. Try PyMuPDF's built-in table detection first.
    pymupdf_fields, pymupdf_regions = extract_table_fields_with_pymupdf(
        page,
        words,
        used_ids,
    )

    if pymupdf_fields:
        return pymupdf_fields, pymupdf_regions

    # 2. Fallback to custom vector-line table detection.
    horizontal_lines = [rect for rect in drawings if is_horizontal_line(rect, page)]
    vertical_lines = [rect for rect in drawings if is_vertical_line(rect, page)]

    horizontal_lines = merge_horizontal_lines(horizontal_lines)
    vertical_lines = merge_vertical_lines(vertical_lines)

    if not horizontal_lines or not vertical_lines:
        return [], []

    components = build_table_components(horizontal_lines, vertical_lines)
    all_fields = []
    table_regions = []

    for table_index, (table_h, table_v) in enumerate(components, start=1):
        fields, table_rect = build_table_fields_from_lines(
            page,
            words,
            table_h,
            table_v,
            used_ids,
            table_index,
        )

        if fields and table_rect is not None:
            all_fields.extend(fields)
            table_regions.append(table_rect)

    return all_fields, table_regions

def group_cell_positions(values, tolerance=3.0):
    if not values:
        return []

    values = sorted(values)
    groups = [[values[0]]]

    for value in values[1:]:
        if abs(value - groups[-1][-1]) <= tolerance:
            groups[-1].append(value)
        else:
            groups.append([value])

    return [sum(group) / len(group) for group in groups]


def infer_table_cell_position(cell_rect, x_positions, y_positions):
    cell_center_x = rect_center_x(cell_rect)
    cell_center_y = rect_center_y(cell_rect)

    column_index = min(
        range(len(x_positions)),
        key=lambda index: abs(x_positions[index] - cell_center_x),
    ) + 1

    row_index = min(
        range(len(y_positions)),
        key=lambda index: abs(y_positions[index] - cell_center_y),
    ) + 1

    return row_index, column_index

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

            table_fields, table_regions = extract_table_fields(page, words, drawings, used_ids)

            all_fields.extend(table_fields)
            all_fields.extend(
                extract_text_line_fields(
                    page,
                    words,
                    drawings,
                    used_ids,
                    excluded_regions=table_regions,
                )
            )
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