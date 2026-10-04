from enum import Enum
from typing import Dict, List, Set

class SystemRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    HOSPITAL_ADMIN = "HOSPITAL_ADMIN"
    DOCTOR = "DOCTOR"
    NURSE = "NURSE"
    RECEPTION = "RECEPTION"
    PATIENT = "PATIENT"
    LAB_TECHNICIAN = "LAB_TECHNICIAN"
    RADIOLOGIST = "RADIOLOGIST"
    PHARMACIST = "PHARMACIST"
    BILLING = "BILLING"
    INSURANCE_TPA = "INSURANCE_TPA"
    OPERATIONS = "OPERATIONS"
    HOUSEKEEPING = "HOUSEKEEPING"
    SECURITY = "SECURITY"
    TECHNICIAN = "TECHNICIAN"

ALL_PERMISSIONS = {
    "patient.view",
    "patient.create",
    "patient.update",
    "encounter.view",
    "encounter.create",
    "encounter.update",
    "admission.view",
    "admission.create",
    "admission.update",
    "admission.discharge",
    "bed.view",
    "bed.assign",
    "bed.release",
    "bed.clean",
    "bed.manage",
    "clinical.view",
    "clinical.write",
    "vitals.view",
    "vitals.write",
    "user.view",
    "user.manage",
    "organization.view",
    "organization.manage",
    "audit.view",
    "dashboard.view",
    "lab.view", "lab.manage", "pharmacy.view", "pharmacy.manage", "billing.view", "billing.manage", "insurance.view", "insurance.manage", "discharge.view", "discharge.manage", "ai.view"
}

ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    SystemRole.SUPER_ADMIN.value: ALL_PERMISSIONS,
    SystemRole.HOSPITAL_ADMIN.value: {
        "patient.view", "patient.create", "patient.update",
        "encounter.view", "encounter.create", "encounter.update",
        "admission.view", "admission.create", "admission.update", "admission.discharge",
        "bed.view", "bed.assign", "bed.release", "bed.clean", "bed.manage",
        "clinical.view", "vitals.view",
        "user.view", "user.manage",
        "organization.view", "organization.manage",
        "audit.view", "dashboard.view", "lab.view", "lab.manage", "pharmacy.view", "pharmacy.manage", "billing.view", "billing.manage", "insurance.view", "insurance.manage", "discharge.view", "discharge.manage", "ai.view"
    },
    SystemRole.DOCTOR.value: {
        "patient.view",
        "encounter.view", "encounter.create", "encounter.update",
        "admission.view", "admission.discharge",
        "bed.view",
        "clinical.view", "clinical.write",
        "vitals.view", "vitals.write",
        "dashboard.view", "lab.view", "lab.manage", "pharmacy.view", "pharmacy.manage", "billing.view", "insurance.view", "discharge.view", "discharge.manage", "ai.view"
    },
    SystemRole.NURSE.value: {
        "patient.view",
        "encounter.view",
        "admission.view",
        "bed.view", "bed.clean",
        "clinical.view", "clinical.write",
        "vitals.view", "vitals.write",
        "dashboard.view"
    },
    SystemRole.RECEPTION.value: {
        "patient.view", "patient.create", "patient.update",
        "encounter.view", "encounter.create",
        "admission.view", "admission.create",
        "bed.view", "bed.assign",
        "dashboard.view"
    },
    SystemRole.PATIENT.value: {
        "patient.view",
        "encounter.view",
        "clinical.view",
        "vitals.view", "lab.view", "pharmacy.view", "billing.view", "insurance.view", "discharge.view", "ai.view"
    },
    SystemRole.LAB_TECHNICIAN.value: {
        "patient.view", "clinical.view", "lab.view", "lab.manage"
    },
    SystemRole.RADIOLOGIST.value: {
        "patient.view", "clinical.view"
    },
    SystemRole.PHARMACIST.value: {
        "patient.view", "clinical.view", "pharmacy.view", "pharmacy.manage"
    },
    SystemRole.BILLING.value: {
        "patient.view", "admission.view", "dashboard.view", "billing.view", "billing.manage"
    },
    SystemRole.INSURANCE_TPA.value: {
        "patient.view", "admission.view", "insurance.view", "insurance.manage"
    },
    SystemRole.OPERATIONS.value: {
        "bed.view", "admission.view", "dashboard.view"
    },
    SystemRole.HOUSEKEEPING.value: {
        "bed.view", "bed.clean"
    },
    SystemRole.SECURITY.value: set(),
    SystemRole.TECHNICIAN.value: {
        "bed.view", "bed.manage"
    }
}
