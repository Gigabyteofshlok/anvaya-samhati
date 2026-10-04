def test_dashboard_summary_is_database_backed(client, admin_headers):
    response = client.get("/api/v1/dashboard/summary", headers=admin_headers)

    assert response.status_code == 200
    summary = response.json()
    assert summary["total_beds"] == sum([
        summary["occupied_beds"], summary["available_beds"], summary["reserved_beds"],
        summary["cleaning_beds"], summary["maintenance_beds"], summary["isolation_beds"],
    ])
    assert len(summary["admission_trend"]) == 7
    assert all({"date", "label", "admissions", "discharges"} <= set(day) for day in summary["admission_trend"])
    assert all(0 <= ward["occupancy_pct"] <= 100 for ward in summary["wards"])


def test_dashboard_summary_can_filter_by_branch(client, admin_headers):
    branches = client.get("/api/v1/organization/branches", headers=admin_headers).json()
    response = client.get(
        "/api/v1/dashboard/summary",
        params={"branch_id": branches[0]["id"]},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert all(branch["branch_id"] == branches[0]["id"] for branch in response.json()["branches"])
