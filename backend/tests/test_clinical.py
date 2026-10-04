def test_record_and_retrieve_vitals(client, nurse_headers, doctor_headers):
    # Get admitted patient
    patients = client.get("/api/v1/patients?status_filter=ADMITTED", headers=nurse_headers).json()
    assert len(patients) > 0
    p = patients[0]

    vital_payload = {
        "patient_id": p["id"],
        "heart_rate": 84,
        "bp_systolic": 122,
        "bp_diastolic": 78,
        "respiratory_rate": 18,
        "spo2": 99.0,
        "temperature": 98.6,
        "weight_kg": 72.0,
        "notes": "Patient resting comfortably"
    }

    # Record vitals as nurse
    post_res = client.post(f"/api/v1/patients/{p['id']}/vitals", json=vital_payload, headers=nurse_headers)
    assert post_res.status_code == 200
    vital_data = post_res.json()
    assert vital_data["heart_rate"] == 84
    assert vital_data["bp_systolic"] == 122

    # Doctor views vitals history
    get_res = client.get(f"/api/v1/patients/{p['id']}/vitals", headers=doctor_headers)
    assert get_res.status_code == 200
    vitals_list = get_res.json()
    assert len(vitals_list) >= 1
    assert any(v["heart_rate"] == 84 for v in vitals_list)

def test_create_and_view_clinical_note(client, doctor_headers):
    patients = client.get("/api/v1/patients?status_filter=ADMITTED", headers=doctor_headers).json()
    p = patients[0]

    note_payload = {
        "patient_id": p["id"],
        "note_type": "PROGRESS_NOTE",
        "title": "Evening Clinical Review",
        "content": "Patient reports significant symptom relief. ECG stable. Plan to maintain current pharmacotherapy."
    }

    note_res = client.post(f"/api/v1/patients/{p['id']}/notes", json=note_payload, headers=doctor_headers)
    assert note_res.status_code == 200
    note_data = note_res.json()
    assert note_data["title"] == "Evening Clinical Review"
    assert note_data["note_type"] == "PROGRESS_NOTE"

    # Verify note in patient notes list
    notes_list = client.get(f"/api/v1/patients/{p['id']}/notes", headers=doctor_headers).json()
    assert any(n["title"] == "Evening Clinical Review" for n in notes_list)

def test_command_center_metrics(client, admin_headers):
    # Real PostgreSQL-derived metrics
    res = client.get("/api/v1/dashboard/summary", headers=admin_headers)
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_beds"] > 0
    assert summary["occupied_beds"] > 0
    assert summary["available_beds"] >= 0
    assert summary["active_admissions"] > 0
    assert len(summary["branches"]) == 3
    assert len(summary["recent_admissions"]) > 0
