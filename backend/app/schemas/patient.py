from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, EmailStr

# Contacts
class PatientContactIn(BaseModel):
    name: str
    relationship_type: str
    phone: str
    is_primary: bool = True

class PatientContactOut(PatientContactIn):
    id: str
    patient_id: str

    class Config:
        from_attributes = True

# Allergies
class PatientAllergyIn(BaseModel):
    allergen: str
    reaction: Optional[str] = None
    severity: str = "MODERATE"  # MILD, MODERATE, SEVERE, LIFE_THREATENING
    status: str = "ACTIVE"

class PatientAllergyOut(PatientAllergyIn):
    id: str
    patient_id: str
    recorded_at: datetime
    recorded_by: Optional[str] = None

    class Config:
        from_attributes = True

# Conditions
class PatientConditionIn(BaseModel):
    condition_name: str
    icd_code: Optional[str] = None
    status: str = "ACTIVE"
    onset_date: Optional[date] = None
    notes: Optional[str] = None

class PatientConditionOut(PatientConditionIn):
    id: str
    patient_id: str
    recorded_at: datetime
    recorded_by: Optional[str] = None

    class Config:
        from_attributes = True

# Medications
class PatientMedicationIn(BaseModel):
    medication_name: str
    dose: str
    route: str = "ORAL"
    frequency: str = "BID"
    status: str = "ACTIVE"
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PatientMedicationOut(PatientMedicationIn):
    id: str
    patient_id: str
    recorded_by: Optional[str] = None

    class Config:
        from_attributes = True

# These are deliberately narrow record-level update contracts.  They keep the
# clinical history model intact while allowing an authorised clinician to
# correct status, dose, and supporting details without a generic "edit all"
# endpoint.
class PatientAllergyUpdate(BaseModel):
    allergen: Optional[str] = None
    reaction: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None

class PatientConditionUpdate(BaseModel):
    condition_name: Optional[str] = None
    icd_code: Optional[str] = None
    status: Optional[str] = None
    onset_date: Optional[date] = None
    notes: Optional[str] = None

class PatientMedicationUpdate(BaseModel):
    medication_name: Optional[str] = None
    dose: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

# Patient Registration
class PatientCreate(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    date_of_birth: date
    gender: str
    blood_group: Optional[str] = None
    mobile: str
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    consent_status: str = "GRANTED"
    registered_branch_id: str

    # Optional initial clinical items
    emergency_contact: Optional[PatientContactIn] = None
    allergies: List[PatientAllergyIn] = []
    conditions: List[PatientConditionIn] = []
    medications: List[PatientMedicationIn] = []

class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    consent_status: Optional[str] = None

class PatientSummaryOut(BaseModel):
    id: str
    patient_id: str
    first_name: str
    last_name: str
    full_name: str
    date_of_birth: date
    age: int
    gender: str
    blood_group: Optional[str] = None
    mobile: str
    registered_branch_id: str
    registered_branch_name: Optional[str] = None
    current_status: str  # ADMITTED, OUTPATIENT, DISCHARGED
    current_admission_id: Optional[str] = None
    current_bed_number: Optional[str] = None
    current_ward_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PatientOut(BaseModel):
    id: str
    patient_id: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    full_name: str
    date_of_birth: date
    age: int
    gender: str
    blood_group: Optional[str] = None
    mobile: str
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    consent_status: str
    registered_branch_id: str
    registered_branch_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    contacts: List[PatientContactOut] = []
    allergies: List[PatientAllergyOut] = []
    conditions: List[PatientConditionOut] = []
    medications: List[PatientMedicationOut] = []
    
    # Active admission details if admitted
    active_admission: Optional[dict] = None

    class Config:
        from_attributes = True
