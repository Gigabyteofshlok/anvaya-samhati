from fastapi import APIRouter
from app.api.v1 import (
    auth,
    users,
    organization,
    patients,
    encounters,
    admissions,
    beds,
    clinical,
    vitals,
    notes,
    dashboard,
    audit,
    laboratory,
    pharmacy,
    billing,
    insurance,
    discharge,
    portal,
    ai,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(organization.router)
api_router.include_router(patients.router)
api_router.include_router(encounters.router)
api_router.include_router(admissions.router)
api_router.include_router(beds.router)
api_router.include_router(clinical.router)
api_router.include_router(vitals.router)
api_router.include_router(notes.router)
api_router.include_router(dashboard.router)
api_router.include_router(audit.router)
api_router.include_router(laboratory.router)
api_router.include_router(pharmacy.router)
api_router.include_router(billing.router)
api_router.include_router(insurance.router)
api_router.include_router(discharge.router)
api_router.include_router(portal.router)
api_router.include_router(ai.router)
