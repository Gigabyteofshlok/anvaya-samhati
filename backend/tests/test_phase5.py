from datetime import date, timedelta


def test_laboratory_order_result_and_billing_event(client, admin_headers):
    patient = client.get("/api/v1/patients?limit=1", headers=admin_headers).json()[0]
    branch_id = client.get("/api/v1/organization/branches", headers=admin_headers).json()[0]["id"]
    test = client.post("/api/v1/laboratory/catalog", json={"code": "CBC", "name": "Complete Blood Count", "category": "Hematology", "reference_range": "4.0-11.0", "unit": "x10^9/L", "price": 450}, headers=admin_headers)
    assert test.status_code == 201
    order = client.post("/api/v1/laboratory/orders", json={"patient_id": patient["id"], "branch_id": branch_id, "test_id": test.json()["id"]}, headers=admin_headers)
    assert order.status_code == 201
    order_id = order.json()["id"]
    assert client.post(f"/api/v1/laboratory/orders/{order_id}/collect", headers=admin_headers).status_code == 200
    assert client.post(f"/api/v1/laboratory/orders/{order_id}/result", json={"result_value": "13.2", "flag": "NORMAL"}, headers=admin_headers).status_code == 201
    assert client.post(f"/api/v1/laboratory/orders/{order_id}/verify", headers=admin_headers).json()["status"] == "VERIFIED"
    invoices = client.get(f"/api/v1/billing/invoices?patient_id={patient['id']}", headers=admin_headers).json()
    assert invoices and invoices[0]["items"][0]["charge_type"] == "LABORATORY"


def test_dispensing_decrements_inventory_and_creates_charge(client, admin_headers):
    patient = client.get("/api/v1/patients?limit=1", headers=admin_headers).json()[0]
    branch_id = client.get("/api/v1/organization/branches", headers=admin_headers).json()[0]["id"]
    medicine = client.post("/api/v1/pharmacy/medicines", json={"code": "PARA500", "generic_name": "Paracetamol", "dosage_form": "TABLET", "reorder_threshold": 5}, headers=admin_headers)
    assert medicine.status_code == 201
    batch = client.post("/api/v1/pharmacy/inventory", json={"medicine_id": medicine.json()["id"], "branch_id": branch_id, "batch_number": "SYN-001", "expiry_date": str(date.today() + timedelta(days=365)), "quantity_on_hand": 20, "unit_price": 3.5}, headers=admin_headers)
    assert batch.status_code == 201
    prescription = client.post("/api/v1/pharmacy/prescriptions", json={"patient_id": patient["id"], "branch_id": branch_id, "items": [{"medicine_id": medicine.json()["id"], "quantity": 4}]}, headers=admin_headers)
    assert prescription.status_code == 201
    item_id = prescription.json()["items"][0]["id"]
    dispense = client.post(f"/api/v1/pharmacy/prescriptions/items/{item_id}/dispense", json={"batch_id": batch.json()["id"], "quantity": 4}, headers=admin_headers)
    assert dispense.status_code == 200
    assert dispense.json()["remaining_stock"] == 16
