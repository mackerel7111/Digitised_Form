import fitz
import pytest

from pdf_service import denormalize_rect, export_filled_pdf_file, format_date_value


def test_format_date_value_converts_html_date_to_pdf_date_boxes():
    result = format_date_value("2026-05-30", "DDMMYYYY")

    assert result == "30052026"


def test_denormalize_rect_converts_relative_coordinates_to_pdf_points():
    document = fitz.open()
    page = document.new_page(width=200, height=100)

    rect = denormalize_rect(
        {
            "x": 0.25,
            "y": 0.1,
            "w": 0.5,
            "h": 0.2,
        },
        page,
    )

    assert rect.x0 == pytest.approx(50)
    assert rect.y0 == pytest.approx(10)
    assert rect.x1 == pytest.approx(150)
    assert rect.y1 == pytest.approx(30)

    document.close()


def test_export_filled_pdf_writes_text_value(tmp_path):
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "output.pdf"

    document = fitz.open()
    document.new_page(width=300, height=200)
    document.save(input_pdf)
    document.close()

    fields = [
        {
            "id": "site_name",
            "label": "Site Name",
            "type": "text",
            "page": 1,
            "rect": {
                "x": 0.1,
                "y": 0.2,
                "w": 0.5,
                "h": 0.1,
            },
        }
    ]

    values = {
        "site_name": "River Site A",
    }

    export_filled_pdf_file(input_pdf, output_pdf, fields, values)

    assert output_pdf.exists()

    exported = fitz.open(output_pdf)
    text = exported[0].get_text()
    exported.close()

    assert "River Site A" in text