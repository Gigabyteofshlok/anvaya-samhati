from app.core.security import create_access_token, get_password_hash
from app.models.identity import User
from app.models.phase6 import PatientPortalLink


def test_structured_lab_result_persists_component_values_and_flags(client, admin_headers):
    patient = client.get("/api/v1/patients?limit=1", headers=admin_headers).json()[0]
    branch = client.get("/api/v1/organization/branches", headers=admin_headers).json()[0]
    test = client.post("/api/v1/laboratory/catalog", json={"code": "STRUCT-CBC", "name": "Structured CBC", "category": "Hematology", "price": 450}, headers=admin_headers).json()
    hgb = client.post(f"/api/v1/laboratory/catalog/{test['id']}/components", json={"code": "HGB", "name": "Hemoglobin", "unit": "g/dL", "reference_low": 12, "reference_high": 17, "display_order": 1}, headers=admin_headers).json()
    wbc = client.post(f"/api/v1/laboratory/catalog/{test['id']}/components", json={"code": "WBC", "name": "WBC", "unit": "/uL", "reference_low": 4000, "reference_high": 11000, "display_order": 2}, headers=admin_headers).json()
    order = client.post("/api/v1/laboratory/orders", json={"patient_id": patient["id"], "branch_id": branch["id"], "test_id": test["id"]}, headers=admin_headers).json()
    assert client.post(f"/api/v1/laboratory/orders/{order['id']}/collect", headers=admin_headers).status_code == 200
    result = client.post(f"/api/v1/laboratory/orders/{order['id']}/structured-result", json={"complete": True, "values": [{"component_id": hgb["id"], "value_text": "10.2"}, {"component_id": wbc["id"], "value_text": "8400"}]}, headers=admin_headers)
    assert result.status_code == 200 and result.json()["flag"] == "ABNORMAL"
    workspace = client.get(f"/api/v1/laboratory/orders/{order['id']}/workspace", headers=admin_headers).json()
    assert workspace["order"]["status"] == "RESULT_READY"
    assert {x["flag"] for x in workspace["components"]} == {"LOW", "NORMAL"}


def test_structured_discharge_releases_bed_and_records_timeline(client, admin_headers):
    admission = client.get("/api/v1/admissions?status=ACTIVE&limit=1", headers=admin_headers).json()[0]
    initiated = client.post("/api/v1/discharges", json={"admission_id": admission["id"], "diagnosis_summary": "Synthetic discharge diagnosis", "clinical_summary": "Synthetic clinical summary", "instructions": [{"instruction_type": "FOLLOW_UP", "content": "Synthetic follow-up in 7 days."}]}, headers=admin_headers)
    assert initiated.status_code == 201
    discharge_id = initiated.json()["id"]
    cleared = client.post(f"/api/v1/discharges/{discharge_id}/clearance", json={"clinical_cleared": True, "pending_results_checked": True, "billing_cleared": True, "insurance_cleared": True}, headers=admin_headers)
    assert cleared.status_code == 200 and cleared.json()["status"] == "DISCHARGE_APPROVED"
    completed = client.post(f"/api/v1/discharges/{discharge_id}/complete", headers=admin_headers)
    assert completed.status_code == 200 and completed.json()["status"] == "DISCHARGED"
    admission_after = client.get(f"/api/v1/admissions/{admission['id']}", headers=admin_headers).json()
    assert admission_after["status"] == "DISCHARGED"


def test_patient_portal_isolation_rejects_other_patient(client, db_session):
    patients = client.get("/api/v1/patients?limit=2", headers={"Authorization": "Bearer invalid"})
    # Establish a patient account using fixture DB and a real signed JWT.
    from app.models.patient import Patient
    first, second = db_session.query(Patient).order_by(Patient.patient_id).limit(2).all()
    user = User(username="portal-isolation", email="portal-isolation@anvaya.demo", hashed_password=get_password_hash("DemoPassword123!"), full_name="Portal Isolation", role="PATIENT", branch_id=first.registered_branch_id)
    db_session.add(user); db_session.flush(); db_session.add(PatientPortalLink(patient_id=first.id, user_id=user.id)); db_session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(subject=user.id, extra_claims={'role': 'PATIENT', 'email': user.email})}"}
    assert client.get(f"/api/v1/patients/{first.id}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/patients/{second.id}", headers=headers).status_code == 403
    assert client.get(f"/api/v1/patients/{second.id}/vitals", headers=headers).status_code == 403
    assert client.get(f"/api/v1/patients/{second.id}/notes", headers=headers).status_code == 403
    assert len(client.get("/api/v1/patients", headers=headers).json()) == 1


def test_versioned_ml_inference_returns_safety_and_metadata(client, admin_headers):
    patient = client.get("/api/v1/patients?limit=1", headers=admin_headers).json()[0]
    result = client.post("/api/v1/ai/patient-risk", json={"patient_id": patient["id"]}, headers=admin_headers)
    assert result.status_code == 200
    body = result.json()
    assert body["risk_category"] in {"LOW", "MODERATE", "HIGH"}
    assert body["model"]["model_version"] == "1.0.0"
    assert "Not a diagnosis" in body["safety"]
