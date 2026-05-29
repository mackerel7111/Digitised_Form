import fitz


def render_page_png(pdf_path, page_number):
    with fitz.open(pdf_path) as document:
        if page_number > document.page_count:
            return None

        page = document[page_number - 1]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        return pixmap.tobytes("png")


def denormalize_rect(rect_data, page):
    page_width = page.rect.width
    page_height = page.rect.height

    x0 = rect_data["x"] * page_width
    y0 = rect_data["y"] * page_height
    x1 = (rect_data["x"] + rect_data["w"]) * page_width
    y1 = (rect_data["y"] + rect_data["h"]) * page_height

    return fitz.Rect(x0, y0, x1, y1)


def format_date_value(value, date_format):
    if not value:
        return ""

    value = str(value)

    if date_format == "DDMMYYYY" and len(value) == 10 and value[4] == "-" and value[7] == "-":
        year, month, day = value.split("-")
        return f"{day}{month}{year}"

    return value.replace("-", "")


def draw_date_boxes(page, rect, value, field):
    text = format_date_value(value, field.get("dateFormat", "DDMMYYYY"))
    box_count = int(field.get("boxCount", 8))
    gap_percent = float(field.get("boxGap", 0.4))
    gap = (gap_percent / 100) * page.rect.width

    if not text:
        return

    text = text[:box_count]
    total_gap = gap * (box_count - 1)
    box_width = (rect.width - total_gap) / box_count

    for index, char in enumerate(text):
        x0 = rect.x0 + index * (box_width + gap)
        slot = fitz.Rect(x0, rect.y0, x0 + box_width, rect.y1)

        page.insert_textbox(
            slot,
            char,
            fontsize=10,
            fontname="helv",
            align=fitz.TEXT_ALIGN_CENTER,
            color=(0, 0, 0),
        )


def draw_field_value(page, field, value):
    if value in (None, "", False):
        return

    rect = denormalize_rect(field["rect"], page)
    field_type = field.get("type", "text")

    if field_type == "date" and field.get("renderMode") == "date_boxes":
        draw_date_boxes(page, rect, value, field)
        return

    if field_type == "checkbox":
        page.insert_text(
            fitz.Point(rect.x0 + 2, rect.y1 - 2),
            "X",
            fontsize=10,
            fontname="helv",
            color=(0, 0, 0),
        )
        return

    if field_type == "multiline":
        page.insert_textbox(
            rect,
            str(value),
            fontsize=9,
            fontname="helv",
            align=fitz.TEXT_ALIGN_LEFT,
            color=(0, 0, 0),
        )
        return

    page.insert_text(
        fitz.Point(rect.x0, rect.y1 - 3),
        str(value),
        fontsize=10,
        fontname="helv",
        color=(0, 0, 0),
    )


def export_filled_pdf_file(pdf_path, output_path, fields, values):
    document = fitz.open(pdf_path)

    try:
        for field in fields:
            page_number = field.get("page", 1)
            page = document[page_number - 1]
            value = values.get(field["id"])
            draw_field_value(page, field, value)

        document.save(output_path, garbage=4, deflate=True)
    finally:
        document.close()
