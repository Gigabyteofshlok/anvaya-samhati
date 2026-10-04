import uuid

def test_register_patient_unique_id_and_structure(client, reception_headers):
    # Fetch branch id
    branches = client.get("/api/v1/organization/branches", headers=reception_headers).json()
    assert len(branches) > 0
    branch_id = branches[0]["id"]

    random_mobile = f"9988{uuid.uuid4().hex[:6]}"
    patient_payload = {
        "first_name": "Vikram",
        "middle_name": "R.",
        "last_name": "Bhatia",
        "date_of_birth": "1980-05-15",
        "gender": "MALE",
        "blood_group": "O+",
        "mobile": random_mobile,
        "email": f"vikram.{random_mobile[:5]}@example.com",
        "address": "404 High street",
        "city": "Mumbai",
        "state": "Maharashtra",
        "postal_code": "400001",
        "consent_status": "GRANTED",
        "registered_branch_id": branch_id,
        "emergency_contact": {
            "name": "Anjali Bhatia",
            "relationship_type": "Spouse",
            "phone": "9988112233",
            "is_primary": True
        },
        "allergies": [
            {
                "allergen": "Ciprofloxacin",
                "reaction": "Skin rash and hives",
                "severity": "MODERATE",
                "status": "ACTIVE"
            }
        ],
        "conditions": [
            {
                "condition_name": "Hypercholesterolemia",
                "icd_code": "E78.0",
                "status": "ACTIVE"
            }
        ]
    }

    response = client.post("/api/v1/patients", json=patient_payload, headers=reception_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["patient_id"].startswith("ANV-")
    assert data["first_name"] == "Vikram"
    assert len(data["allergies"]) == 1
    assert data["allergies"][0]["allergen"] == "Ciprofloxacin"
    assert len(data["conditions"]) == 1
    assert len(data["contacts"]) == 1

    # Verify duplicate mobile rejection
    dup_res = client.post("/api/v1/patients", json=patient_payload, headers=reception_headers)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

def test_patient_search(client, reception_headers):
    # Search by existing patient ANV-000001
    response = client.get("/api/v1/patients?q=ANV-000001", headers=reception_headers)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["patient_id"] == "ANV-000001"
    assert results[0]["first_name"] == "Rajesh"

def test_patient_360_timeline(client, reception_headers):
    # Get Patient 360
    p = client.get("/api/v1/patients?q=Rajesh", headers=reception_headers).json()[0]
    p360 = client.get(f"/api/v1/patients/{p['id']}", headers=reception_headers).json()
    assert p360["first_name"] == "Rajesh"
    assert len(p360["allergies"]) > 0

    # Get Timeline
    timeline = client.get(f"/api/v1/patients/{p['id']}/timeline", headers=reception_headers).json()
    assert len(timeline) > 0
    event_types = [e["event_type"] for e in timeline]
    assert "PATIENT_REGISTERED" in event_types
