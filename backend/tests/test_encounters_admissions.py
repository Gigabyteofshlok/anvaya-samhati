def test_admission_and_bed_transactional_workflow(client, reception_headers, doctor_headers):
    # 1. Get an available bed in Branch 1
    branches = client.get("/api/v1/organization/branches", headers=reception_headers).json()
    b1_id = branches[0]["id"]

    beds = client.get(f"/api/v1/beds?branch_id={b1_id}&status=AVAILABLE", headers=reception_headers).json()
    assert len(beds) > 0
    test_bed = beds[0]

    # 2. Pick an unadmitted patient
    patients = client.get(f"/api/v1/patients?status_filter=OUTPATIENT", headers=reception_headers).json()
    assert len(patients) > 0
    test_patient = patients[0]

    # 3. Get doctor id
    doctors = client.get("/api/v1/users?role=DOCTOR", headers=reception_headers).json()
    assert len(doctors) > 0
    doc_id = doctors[0]["id"]

    # 4. Create admission
    adm_payload = {
        "patient_id": test_patient["id"],
        "branch_id": b1_id,
        "attending_doctor_id": doc_id,
        "assigned_bed_id": test_bed["id"],
        "admission_type": "EMERGENCY",
        "reason": "Test acute admission",
        "diagnosis_notes": "Diagnostic notes for verification"
    }

    adm_res = client.post("/api/v1/admissions", json=adm_payload, headers=reception_headers)
    assert adm_res.status_code == 200
    admission = adm_res.json()
    assert admission["admission_number"].startswith("ADM-")
    assert admission["status"] == "ACTIVE"

    # 5. Verify bed status transitioned to OCCUPIED
    updated_bed = client.get(f"/api/v1/beds/{test_bed['id']}", headers=reception_headers).json()
    assert updated_bed["status"] == "OCCUPIED"
    assert updated_bed["current_admission_id"] == admission["id"]

    # 6. Verify cannot assign already occupied bed
    another_patient = patients[1]
    conflict_payload = {
        "patient_id": another_patient["id"],
        "branch_id": b1_id,
        "attending_doctor_id": doc_id,
        "assigned_bed_id": test_bed["id"],
        "admission_type": "EMERGENCY",
        "reason": "Conflict test"
    }
    conflict_res = client.post("/api/v1/admissions", json=conflict_payload, headers=reception_headers)
    assert conflict_res.status_code == 400
    assert "cannot be assigned" in conflict_res.json()["detail"]

    # 7. Discharge admission and verify bed moves to CLEANING
    discharge_res = client.post(
        f"/api/v1/admissions/{admission['id']}/discharge",
        json={"discharge_notes": "Discharged in stable condition."},
        headers=doctor_headers
    )
    assert discharge_res.status_code == 200
    assert discharge_res.json()["status"] == "DISCHARGED"

    cleaning_bed = client.get(f"/api/v1/beds/{test_bed['id']}", headers=reception_headers).json()
    assert cleaning_bed["status"] == "CLEANING"
    assert cleaning_bed["current_admission_id"] is None
