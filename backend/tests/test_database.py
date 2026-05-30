import database


def setup_temp_database(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")

    database.init_db()


def test_create_and_update_form(monkeypatch, tmp_path):
    setup_temp_database(monkeypatch, tmp_path)

    fields = [
        {
            "id": "site_name",
            "label": "Site Name",
            "type": "text",
            "page": 1,
            "rect": {
                "x": 0.1,
                "y": 0.2,
                "w": 0.3,
                "h": 0.04,
            },
        }
    ]

    created = database.create_form("form-1", "sample.pdf", fields)

    assert created["id"] == "form-1"
    assert created["name"] == "sample.pdf"
    assert created["status"] == "Draft"
    assert created["fields"] == fields

    updated = database.update_form("form-1", fields, "Published")

    assert updated["status"] == "Published"


def test_create_and_list_submissions(monkeypatch, tmp_path):
    setup_temp_database(monkeypatch, tmp_path)

    database.create_form("form-1", "sample.pdf", [])

    submission = database.create_submission(
        "form-1",
        {
            "site_name": "River Site A",
            "weather_sunny": True,
        },
    )

    submissions = database.list_submissions("form-1")

    assert len(submissions) == 1
    assert submissions[0]["id"] == submission["id"]
    assert submissions[0]["formId"] == "form-1"
    assert submissions[0]["values"]["site_name"] == "River Site A"
    assert submissions[0]["values"]["weather_sunny"] is True