def test_doctor_cannot_manage_users(client, doctor_headers):
    response = client.post(
        "/api/v1/users",
        json={
            "username": "unauthorizeduser",
            "email": "unauth@hospital.com",
            "password": "Password123!",
            "full_name": "Test User",
            "role": "DOCTOR"
        },
        headers=doctor_headers
    )
    assert response.status_code == 403
    assert "user.manage" in response.json()["detail"]

def test_reception_cannot_write_clinical_notes(client, reception_headers):
    # Reception does not have clinical.write permission
    response = client.post(
        "/api/v1/patients/some-id/notes",
        json={
            "patient_id": "some-id",
            "note_type": "PROGRESS_NOTE",
            "title": "Unauthorized Note",
            "content": "This note should be rejected."
        },
        headers=reception_headers
    )
    assert response.status_code == 403
    assert "clinical.write" in response.json()["detail"]

def test_admin_has_user_manage(client, admin_headers):
    # Admin can list users
    response = client.get("/api/v1/users", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) > 0
