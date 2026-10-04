def test_bed_state_machine_valid_and_invalid_transitions(client, admin_headers):
    # Fetch an available bed
    beds = client.get("/api/v1/beds?status=AVAILABLE", headers=admin_headers).json()
    assert len(beds) > 0
    bed = beds[0]
    bed_id = bed["id"]

    # 1. AVAILABLE -> MAINTENANCE is allowed
    res1 = client.post(f"/api/v1/beds/{bed_id}/status", json={"new_status": "MAINTENANCE", "notes": "Checking AC unit"}, headers=admin_headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "MAINTENANCE"

    # 2. MAINTENANCE -> OCCUPIED is NOT allowed (must return to AVAILABLE first)
    res2 = client.post(f"/api/v1/beds/{bed_id}/status", json={"new_status": "OCCUPIED"}, headers=admin_headers)
    assert res2.status_code == 400
    assert "Illegal bed status transition" in res2.json()["detail"]

    # 3. MAINTENANCE -> AVAILABLE is allowed
    res3 = client.post(f"/api/v1/beds/{bed_id}/status", json={"new_status": "AVAILABLE"}, headers=admin_headers)
    assert res3.status_code == 200
    assert res3.json()["status"] == "AVAILABLE"

def test_cleaning_to_available_transition(client, nurse_headers):
    # Fetch a bed in CLEANING
    beds = client.get("/api/v1/beds?status=CLEANING", headers=nurse_headers).json()
    assert len(beds) > 0
    bed_id = beds[0]["id"]

    # Nurse transitions CLEANING -> AVAILABLE
    res = client.post(f"/api/v1/beds/{bed_id}/status", json={"new_status": "AVAILABLE", "notes": "Sanitized and linens replaced."}, headers=nurse_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "AVAILABLE"
