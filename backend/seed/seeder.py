"""Deterministic, synthetic demo data for ANVAYA SAṂHATI.

This module never creates or drops schema. Run migrations first, then call
seed_database only on an empty database.
"""

from datetime import date, datetime, timedelta
from random import Random

from app.core.database import SessionLocal
from app.core.permissions import ALL_PERMISSIONS, ROLE_PERMISSIONS, SystemRole
from app.core.security import get_password_hash
from app.models.admission import Admission
from app.models.audit import AuditLog
from app.models.bed import Bed, BedStatus
from app.models.clinical import ClinicalNote, PatientEvent, PatientVital
from app.models.encounter import Encounter
from app.models.identity import Permission, Role, User
from app.models.organization import Branch, Building, Department, Floor, HospitalGroup, Room, Ward
from app.models.patient import Patient, PatientAllergy, PatientCondition, PatientContact, PatientMedication
from app.models.phase5 import InventoryBatch, LabOrder, LabResult, LabTestCatalog, Medicine, Prescription, PrescriptionItem, StockMovement
from app.models.phase6 import Discharge, InsuranceClaim, InsuranceClaimItem, InsurancePolicy, InsuranceProvider, LabTestComponent, PatientPortalLink, PreAuthorization
from app.services.billing_service import add_event_charge

DEMO_PASSWORD = "DemoPassword123!"
PATIENT_COUNT = 200

FIRST_NAMES = ("Aarav", "Aditi", "Akash", "Ananya", "Arjun", "Bhavna", "Dev", "Divya", "Farhan", "Gauri", "Harish", "Isha", "Jai", "Kavya", "Manish", "Meera", "Neha", "Nikhil", "Pooja", "Pranav", "Riya", "Rohan", "Sahil", "Sana", "Tanvi", "Varun", "Vijay", "Yash", "Zoya", "Anil")
LAST_NAMES = ("Agarwal", "Bansal", "Chavan", "Desai", "Gupta", "Iyer", "Jadhav", "Joshi", "Kapoor", "Kulkarni", "Menon", "Mehta", "Naik", "Nair", "Patil", "Rao", "Shah", "Sharma", "Shetty", "Singh", "Sundaram", "Verma", "Yadav", "Zutshi")
DOCTOR_SPECIALTIES = ("Cardiology", "Internal Medicine", "Emergency Medicine", "Orthopaedics", "General Surgery", "Pediatrics", "Neurology", "Obstetrics & Gynecology")
DEPARTMENTS = (("EMERGENCY", "Emergency"), ("MEDICINE", "General Medicine"), ("CARDIOLOGY", "Cardiology"), ("SURGERY", "General Surgery"), ("ORTHOPEDICS", "Orthopedics"), ("PEDIATRICS", "Pediatrics"), ("RADIOLOGY", "Radiology"), ("PATHOLOGY", "Pathology"), ("PHARMACY", "Pharmacy"), ("BILLING", "Billing & Revenue"), ("INSURANCE", "Insurance & TPA"), ("ADMIN", "Administration"))
WARD_SPECS = (("Emergency Ward", "EMERGENCY", "UNISEX", "ER", 12, "EMERGENCY", 3500), ("Medical ICU", "ICU", "UNISEX", "MICU", 10, "ICU", 9500), ("Surgical Ward", "GENERAL", "UNISEX", "SURG", 12, "STANDARD", 2800), ("General Medicine", "GENERAL", "UNISEX", "GM", 14, "STANDARD", 1800), ("Private Suites", "PRIVATE", "UNISEX", "PVT", 8, "DELUXE", 6500))


def _display_name(index: int) -> str:
    return f"{FIRST_NAMES[index % len(FIRST_NAMES)]} {LAST_NAMES[(index * 7) % len(LAST_NAMES)]}"


def _assert_empty(db) -> None:
    if db.query(HospitalGroup.id).first() or db.query(User.id).first():
        raise RuntimeError("Refusing to seed a non-empty database. Use the explicit reset command only when you intend to replace all synthetic demo data.")


def seed_database() -> None:
    """Seed a migrated empty database with deterministic fictional data."""
    db = SessionLocal()
    Random(20260923)  # Marker for deterministic synthetic-data generation.
    now = datetime.now()
    try:
        _assert_empty(db)
        password_hash = get_password_hash(DEMO_PASSWORD)
        group = HospitalGroup(name="ANVAYA Healthcare Network", code="ANVAYA-NET", description="Synthetic academic demonstration network. Not for clinical use.")
        db.add(group)
        db.flush()

        branches = []
        for code, name, city, phone in (("CENTRAL", "ANVAYA Central Hospital", "Navi Mumbai", "+91 22 4100 1000"), ("CITY", "ANVAYA City Hospital", "Pune", "+91 20 4100 2000"), ("RIVERSIDE", "ANVAYA Riverside Hospital", "Mumbai", "+91 22 4100 3000")):
            branch = Branch(group_id=group.id, code=code, name=name, address=f"Synthetic Campus, {city}, Maharashtra", phone=phone, is_active=True)
            db.add(branch)
            branches.append(branch)
        db.flush()

        department_by_branch, all_beds = {}, []
        for branch_index, branch in enumerate(branches):
            departments = []
            for code, name in DEPARTMENTS:
                department = Department(branch_id=branch.id, code=f"{branch.code}-{code}", name=name, description=f"{name} at {branch.name}", is_active=True)
                db.add(department)
                departments.append(department)
            department_by_branch[branch.id] = departments
            building = Building(branch_id=branch.id, name=f"{branch.name} Clinical Tower", code=f"{branch.code}-CT")
            db.add(building)
            db.flush()
            floors = []
            for number, name in ((0, "Ground Floor"), (1, "First Floor"), (2, "Second Floor")):
                floor = Floor(building_id=building.id, floor_number=number, name=name)
                db.add(floor)
                floors.append(floor)
            db.flush()
            for ward_index, (name, ward_type, gender, prefix, count, bed_type, tariff) in enumerate(WARD_SPECS):
                ward = Ward(branch_id=branch.id, floor_id=floors[ward_index % len(floors)].id, name=f"{name} — {branch.code}", ward_type=ward_type, gender_spec=gender, is_active=True)
                db.add(ward)
                db.flush()
                for room_index in range((count + 3) // 4):
                    room = Room(ward_id=ward.id, room_number=f"{prefix}-{branch_index + 1}{room_index + 1:02d}", room_type="MULTI_BED" if count > 8 else "PRIVATE")
                    db.add(room)
                    db.flush()
                    for bed_offset in range(4):
                        bed_index = room_index * 4 + bed_offset + 1
                        if bed_index > count:
                            break
                        bed = Bed(branch_id=branch.id, ward_id=ward.id, room_id=room.id, bed_number=f"{prefix}-{branch_index + 1}-{bed_index:02d}", bed_type=bed_type, status=BedStatus.AVAILABLE.value, is_isolation=False, tariff_rate=float(tariff))
                        db.add(bed)
                        all_beds.append(bed)
        db.flush()

        permissions = {code: Permission(code=code, description=f"System permission: {code}") for code in sorted(ALL_PERMISSIONS)}
        db.add_all(permissions.values())
        roles = {}
        for system_role in SystemRole:
            role = Role(name=system_role.value, description=f"ANVAYA {system_role.value} role")
            role.permissions = [permissions[code] for code in ROLE_PERMISSIONS.get(system_role.value, set())]
            db.add(role)
            roles[system_role.value] = role
        db.flush()

        users_by_role: dict[str, list[User]] = {role.value: [] for role in SystemRole}

        def add_user(role: str, ordinal: int, branch: Branch, username: str | None = None, name: str | None = None) -> User:
            username = username or f"{role.lower().replace('_', '')}{ordinal:03d}"
            display = name or _display_name(ordinal + len(users_by_role[role]) * 3)
            if role == SystemRole.DOCTOR.value and not display.startswith("Dr."):
                display = f"Dr. {display}"
            email = "admin@anvaya.demo" if username == "superadmin" else f"{username}@anvaya.demo"
            user = User(username=username, email=email, hashed_password=password_hash, full_name=display, role=role, branch_id=branch.id, specialization=DOCTOR_SPECIALTIES[ordinal % len(DOCTOR_SPECIALTIES)] if role == SystemRole.DOCTOR.value else None, license_number=f"DEMO-{role[:3]}-{ordinal:04d}" if role in {SystemRole.DOCTOR.value, SystemRole.NURSE.value} else None, phone=f"+91 9000{ordinal:06d}", is_active=True)
            user.roles.append(roles[role])
            db.add(user)
            users_by_role[role].append(user)
            return user

        add_user(SystemRole.SUPER_ADMIN.value, 1, branches[0], "superadmin", "Vikramaditya Singhania")
        role_counts = {SystemRole.HOSPITAL_ADMIN.value: 4, SystemRole.DOCTOR.value: 24, SystemRole.NURSE.value: 50, SystemRole.LAB_TECHNICIAN.value: 12, SystemRole.RADIOLOGIST.value: 8, SystemRole.PHARMACIST.value: 10, SystemRole.RECEPTION.value: 10, SystemRole.BILLING.value: 10, SystemRole.INSURANCE_TPA.value: 8, SystemRole.OPERATIONS.value: 12, SystemRole.HOUSEKEEPING.value: 12, SystemRole.SECURITY.value: 8, SystemRole.TECHNICIAN.value: 8}
        for role, count in role_counts.items():
            for ordinal in range(1, count + 1):
                username, name = None, None
                if role == SystemRole.DOCTOR.value and ordinal == 1:
                    username, name = "drsharma", "Dr. Rajesh Sharma"
                elif role == SystemRole.NURSE.value and ordinal == 1:
                    username, name = "nursepriya", "Priya Nair"
                elif role == SystemRole.RECEPTION.value and ordinal == 1:
                    username, name = "reception", "Ramesh Patil"
                add_user(role, ordinal, branches[(ordinal - 1) % len(branches)], username, name)
        db.flush()
        doctors_by_branch = {branch.id: [user for user in users_by_role[SystemRole.DOCTOR.value] if user.branch_id == branch.id] for branch in branches}
        reception_by_branch = {branch.id: [user for user in users_by_role[SystemRole.RECEPTION.value] if user.branch_id == branch.id] for branch in branches}

        patients = []
        for index in range(1, PATIENT_COUNT + 1):
            branch = branches[(index - 1) % len(branches)]
            first_name = "Rajesh" if index == 1 else FIRST_NAMES[index % len(FIRST_NAMES)]
            last_name = "Patil" if index == 1 else LAST_NAMES[(index * 5) % len(LAST_NAMES)]
            patient = Patient(patient_id=f"ANV-{index:06d}", first_name=first_name, last_name=last_name, date_of_birth=date(1948 + (index % 55), (index % 12) + 1, (index % 27) + 1), gender="FEMALE" if index % 2 == 0 else "MALE", blood_group=("A+", "B+", "O+", "AB+", "O-")[index % 5], mobile=f"98{index:08d}", email=f"patient{index:03d}@anvaya.demo", address=f"{100 + index} Synthetic Residency", city=("Mumbai", "Pune", "Navi Mumbai")[index % 3], state="Maharashtra", postal_code=f"40{index % 1000:04d}", consent_status="GRANTED", registered_branch_id=branch.id, created_at=now - timedelta(days=index % 180))
            db.add(patient)
            db.flush()
            patients.append(patient)
            doctor = doctors_by_branch[branch.id][index % len(doctors_by_branch[branch.id])]
            db.add(PatientContact(patient_id=patient.id, name=f"{patient.last_name} Family Contact", relationship_type="Spouse" if index % 3 else "Parent", phone=f"97{index:08d}", is_primary=True))
            if index % 3 == 0:
                db.add(PatientCondition(patient_id=patient.id, condition_name=("Essential Hypertension", "Type 2 Diabetes Mellitus", "Acute Viral Fever")[index % 3], icd_code=("I10", "E11.9", "B34.9")[index % 3], status="ACTIVE", onset_date=date(2015 + index % 10, 1 + index % 12, 1 + index % 27), recorded_by=doctor.id))
            if index % 7 == 0:
                db.add(PatientAllergy(patient_id=patient.id, allergen=("Penicillin", "NSAIDs", "Latex")[index % 3], reaction="Synthetic recorded reaction", severity="MODERATE", status="ACTIVE", recorded_by=doctor.id))
            if index == 1:
                db.add(PatientAllergy(patient_id=patient.id, allergen="Penicillin", reaction="Synthetic recorded reaction", severity="SEVERE", status="ACTIVE", recorded_by=doctor.id))
            if index % 4 == 0:
                db.add(PatientMedication(patient_id=patient.id, medication_name=("Paracetamol", "Metformin", "Amlodipine")[index % 3], dose=("500 mg", "500 mg", "5 mg")[index % 3], route="ORAL", frequency="BID", status="ACTIVE", start_date=date.today() - timedelta(days=index % 90), recorded_by=doctor.id))
            db.add(PatientEvent(patient_id=patient.id, actor_id=doctor.id, event_type="PATIENT_REGISTERED", title="Patient Registered", description=f"Synthetic registration completed for {patient.patient_id}", source_module="REGISTRATION", timestamp=now - timedelta(days=index % 180)))
            department = department_by_branch[branch.id][index % len(department_by_branch[branch.id])]
            db.add(Encounter(patient_id=patient.id, branch_id=branch.id, department_id=department.id, encounter_type=("OPD", "FOLLOW_UP", "EMERGENCY")[index % 3], status="COMPLETED", started_at=now - timedelta(days=8 + index % 120), ended_at=now - timedelta(days=7 + index % 120), attending_doctor_id=doctor.id, reason="Synthetic prior clinical encounter"))

        db.flush()
        beds_by_branch = {branch.id: [bed for bed in all_beds if bed.branch_id == branch.id] for branch in branches}
        admission_counter, active_admissions = 1, []
        for index, patient in enumerate(patients[:82], start=1):
            branch = branches[(index - 1) % len(branches)]
            doctor = doctors_by_branch[branch.id][index % len(doctors_by_branch[branch.id])]
            receptionist = reception_by_branch[branch.id][index % len(reception_by_branch[branch.id])]
            department = department_by_branch[branch.id][index % len(department_by_branch[branch.id])]
            bed = next(item for item in beds_by_branch[branch.id] if item.status == BedStatus.AVAILABLE.value)
            admitted_at = now - timedelta(hours=4 + (index * 7) % 150)
            encounter = Encounter(patient_id=patient.id, branch_id=branch.id, department_id=department.id, encounter_type="EMERGENCY" if index % 3 == 0 else "IPD", status="ACTIVE", started_at=admitted_at, attending_doctor_id=doctor.id, reason=("Acute observation and stabilization", "Scheduled inpatient treatment", "Post-procedure monitoring")[index % 3])
            db.add(encounter)
            db.flush()
            admission = Admission(admission_number=f"ADM-{admission_counter:06d}", encounter_id=encounter.id, patient_id=patient.id, branch_id=branch.id, department_id=department.id, attending_doctor_id=doctor.id, assigned_bed_id=bed.id, admission_type="EMERGENCY" if index % 3 == 0 else "ELECTIVE", status="ACTIVE", reason=encounter.reason, admitted_at=admitted_at, admitted_by=receptionist.id)
            admission_counter += 1
            db.add(admission)
            db.flush()
            bed.status, bed.current_admission_id = BedStatus.OCCUPIED.value, admission.id
            active_admissions.append(admission)
            for event_type, title, description, event_at in (("ENCOUNTER_CREATED", "Inpatient Encounter Started", "Synthetic clinical encounter initiated.", admitted_at), ("PATIENT_ADMITTED", "Patient Admitted", f"Admission {admission.admission_number} confirmed.", admitted_at + timedelta(minutes=5)), ("BED_ASSIGNED", f"Bed Assigned: {bed.bed_number}", f"Assigned to {bed.ward.name}.", admitted_at + timedelta(minutes=10))):
                db.add(PatientEvent(patient_id=patient.id, encounter_id=encounter.id, actor_id=receptionist.id, event_type=event_type, title=title, description=description, source_module="ADMISSIONS", timestamp=event_at))
            for reading in range(3):
                recorded_at = max(admitted_at + timedelta(hours=reading * 5), now - timedelta(hours=2))
                nurse = users_by_role[SystemRole.NURSE.value][index % len(users_by_role[SystemRole.NURSE.value])]
                db.add(PatientVital(patient_id=patient.id, encounter_id=encounter.id, admission_id=admission.id, recorded_by=nurse.id, timestamp=recorded_at, heart_rate=72 + (index + reading) % 25, bp_systolic=112 + (index + reading) % 30, bp_diastolic=70 + (index + reading) % 18, respiratory_rate=16 + reading % 4, spo2=95.0 + (index % 5), temperature=98.0 + (reading * 0.2), weight_kg=52.0 + index % 35, notes="Synthetic nursing observation."))
                db.add(PatientEvent(patient_id=patient.id, encounter_id=encounter.id, actor_id=nurse.id, event_type="VITAL_RECORDED", title="Vitals Recorded", description="Synthetic routine vital signs recorded.", source_module="NURSING", timestamp=recorded_at))
            db.add(ClinicalNote(patient_id=patient.id, encounter_id=encounter.id, admission_id=admission.id, author_id=doctor.id, note_type="PROGRESS_NOTE", title="Daily Progress Review", content="Synthetic clinical progress note for academic demonstration only.", created_at=now - timedelta(hours=index % 12)))

        for index, patient in enumerate(patients[82:122], start=83):
            branch = branches[(index - 1) % len(branches)]
            doctor = doctors_by_branch[branch.id][index % len(doctors_by_branch[branch.id])]
            receptionist = reception_by_branch[branch.id][index % len(reception_by_branch[branch.id])]
            department = department_by_branch[branch.id][index % len(department_by_branch[branch.id])]
            admitted_at = now - timedelta(days=1 + index % 7, hours=index % 12)
            discharged_at = admitted_at + timedelta(hours=12 + index % 36)
            encounter = Encounter(patient_id=patient.id, branch_id=branch.id, department_id=department.id, encounter_type="IPD", status="COMPLETED", started_at=admitted_at, ended_at=discharged_at, attending_doctor_id=doctor.id, reason="Completed synthetic inpatient stay.")
            db.add(encounter)
            db.flush()
            db.add(Admission(admission_number=f"ADM-{admission_counter:06d}", encounter_id=encounter.id, patient_id=patient.id, branch_id=branch.id, department_id=department.id, attending_doctor_id=doctor.id, admission_type="ELECTIVE", status="DISCHARGED", reason=encounter.reason, admitted_at=admitted_at, discharged_at=discharged_at, admitted_by=receptionist.id))
            admission_counter += 1
            db.add(PatientEvent(patient_id=patient.id, encounter_id=encounter.id, actor_id=doctor.id, event_type="PATIENT_DISCHARGED", title="Patient Discharged", description="Synthetic inpatient discharge completed.", source_module="ADMISSIONS", timestamp=discharged_at))

        free_beds = [bed for bed in all_beds if bed.status == BedStatus.AVAILABLE.value]
        for bed in free_beds[:6]:
            bed.status = BedStatus.RESERVED.value
        for bed in free_beds[6:12]:
            bed.status, bed.maintenance_notes = BedStatus.CLEANING.value, "Synthetic turnover and sanitization in progress."
        for bed in free_beds[12:16]:
            bed.status, bed.maintenance_notes = BedStatus.MAINTENANCE.value, "Synthetic planned equipment maintenance."
        for bed in free_beds[16:20]:
            bed.status, bed.is_isolation = BedStatus.ISOLATION.value, True
        db.add(AuditLog(action="DEMO_DATA_SEEDED", entity_type="SYSTEM", actor_id=users_by_role[SystemRole.SUPER_ADMIN.value][0].id, actor_email="superadmin@anvaya.demo", branch_id=branches[0].id, notes="Synthetic demonstration data seeded through the controlled seed command."))
        db.commit()
        print(f"Seeded {PATIENT_COUNT} fictional patients, {len(all_beds)} beds, {sum(len(users) for users in users_by_role.values())} users, and {len(active_admissions)} active admissions.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed_phase5_demo_data() -> None:
    """Add only fictional Phase 5 data to an already seeded database.

    This intentionally never resets existing records and refuses a second run.
    """
    db = SessionLocal()
    try:
        if db.query(LabTestCatalog.id).first() or db.query(Medicine.id).first():
            raise RuntimeError("Phase 5 demo data already exists; refusing to duplicate it.")
        branches = db.query(Branch).order_by(Branch.code).all()
        patients = db.query(Patient).order_by(Patient.patient_id).limit(18).all()
        if not branches or not patients:
            raise RuntimeError("Base synthetic data is required before Phase 5 demo data can be added.")
        actor = db.query(User).filter(User.role == SystemRole.PHARMACIST.value).first() or db.query(User).filter(User.role == SystemRole.DOCTOR.value).first() or db.query(User).first()
        if not actor:
            raise RuntimeError("A synthetic staff user is required before Phase 5 demo data can be added.")
        tests = []
        for code, name, category, specimen, ref, unit, price in (
            ("CBC", "Complete Blood Count", "Hematology", "Whole blood", "4.0–11.0", "x10^9/L", 450.0),
            ("BMP", "Basic Metabolic Panel", "Biochemistry", "Serum", "70–110", "mg/dL", 650.0),
            ("CRP", "C-Reactive Protein", "Immunology", "Serum", "0–6", "mg/L", 520.0),
            ("LIPID", "Lipid Profile", "Biochemistry", "Serum", "< 200", "mg/dL", 700.0),
        ):
            row = LabTestCatalog(code=code, name=name, category=category, specimen_type=specimen, reference_range=ref, unit=unit, price=price)
            db.add(row); tests.append(row)
        medicines = []
        for code, generic, brand, category, strength, form, threshold in (
            ("PARA500", "Paracetamol", "Calpol", "Analgesic", "500 mg", "TABLET", 30),
            ("AMLO5", "Amlodipine", "Amlopres", "Cardiovascular", "5 mg", "TABLET", 20),
            ("MET500", "Metformin", "Glycomet", "Antidiabetic", "500 mg", "TABLET", 25),
            ("AMOX500", "Amoxicillin", "Mox", "Antibiotic", "500 mg", "CAPSULE", 20),
        ):
            row = Medicine(code=code, generic_name=generic, brand_name=brand, category=category, strength=strength, dosage_form=form, reorder_threshold=threshold)
            db.add(row); medicines.append(row)
        db.flush()
        for branch_index, branch in enumerate(branches):
            for med_index, medicine in enumerate(medicines):
                quantity = 12 if branch_index == 0 and med_index == 3 else 160 - med_index * 20
                batch = InventoryBatch(medicine_id=medicine.id, branch_id=branch.id, batch_number=f"SYN-{branch.code}-{med_index + 1:03d}", expiry_date=date.today() + timedelta(days=45 + med_index * 120), quantity_on_hand=quantity, unit_price=(3.5, 5.0, 2.5, 7.0)[med_index], supplier="ANVAYA Synthetic Supplies")
                db.add(batch)
        db.flush()
        for index, patient in enumerate(patients):
            branch = branches[index % len(branches)]
            test = tests[index % len(tests)]
            order = LabOrder(order_number=f"LAB-{index + 1:06d}", patient_id=patient.id, branch_id=branch.id, test_id=test.id, ordering_doctor_id=actor.id, assigned_technician_id=actor.id, priority="URGENT" if index % 7 == 0 else "ROUTINE", status="VERIFIED" if index % 3 == 0 else "RESULT_READY" if index % 3 == 1 else "SAMPLE_COLLECTED", sample_collected_at=datetime.now() - timedelta(hours=index + 1), sample_collected_by_id=actor.id)
            db.add(order); db.flush()
            add_event_charge(db, patient_id=patient.id, branch_id=branch.id, charge_type="LABORATORY", description=f"Laboratory test: {test.name}", amount=test.price, source_entity_type="LAB_ORDER", source_entity_id=order.id)
            db.add(PatientEvent(patient_id=patient.id, actor_id=actor.id, event_type="LAB_ORDERED", title=f"Lab ordered: {test.name}", description="Synthetic academic demonstration order.", source_module="LABORATORY"))
            if order.status in {"VERIFIED", "RESULT_READY"}:
                db.add(LabResult(order_id=order.id, result_value=str(8.2 + index / 10), unit=test.unit, reference_range=test.reference_range, flag="HIGH" if index % 7 == 0 else "NORMAL", entered_by_id=actor.id, verified_by_id=actor.id if order.status == "VERIFIED" else None, verified_at=datetime.now() if order.status == "VERIFIED" else None, report_status=order.status))
            if index < 12:
                medicine = medicines[index % len(medicines)]
                prescription = Prescription(prescription_number=f"RX-{index + 1:06d}", patient_id=patient.id, branch_id=branch.id, prescribed_by_id=actor.id, status="DISPENSED")
                db.add(prescription); db.flush()
                item = PrescriptionItem(prescription_id=prescription.id, medicine_id=medicine.id, quantity=10, dispensed_quantity=10, status="DISPENSED", dosage=medicine.strength, frequency="BID", duration_days=5)
                db.add(item); db.flush()
                batch = db.query(InventoryBatch).filter(InventoryBatch.branch_id == branch.id, InventoryBatch.medicine_id == medicine.id).first()
                batch.quantity_on_hand -= 10
                db.add(StockMovement(batch_id=batch.id, prescription_item_id=item.id, movement_type="DISPENSE", quantity=-10, performed_by_id=actor.id, notes="Synthetic academic demonstration dispensing."))
                add_event_charge(db, patient_id=patient.id, branch_id=branch.id, charge_type="PHARMACY", description=f"Medicine: {medicine.generic_name}", amount=batch.unit_price * 10, source_entity_type="PRESCRIPTION_ITEM", source_entity_id=item.id)
                db.add(PatientEvent(patient_id=patient.id, actor_id=actor.id, event_type="MEDICINE_DISPENSED", title=f"Medication dispensed: {medicine.generic_name}", description="Synthetic academic demonstration dispense.", source_module="PHARMACY"))
        db.add(AuditLog(action="PHASE5_DEMO_DATA_SEEDED", entity_type="SYSTEM", actor_id=actor.id, actor_email=actor.email, branch_id=branches[0].id, notes="Synthetic laboratory, pharmacy, and billing data added without resetting the base demo."))
        db.commit()
        print("Seeded synthetic Phase 5 laboratory, pharmacy, and billing demo data.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed_phase6_demo_data() -> None:
    """Add Phase 6 demo catalog and workflow records without resetting existing data.

    This is intentionally idempotent: it only supplies absent static catalog definitions,
    portal links, and a small number of synthetic insurance/discharge records.
    """
    db = SessionLocal()
    try:
        patients = db.query(Patient).order_by(Patient.patient_id).limit(8).all()
        branches = db.query(Branch).order_by(Branch.code).all()
        if not patients or not branches:
            raise RuntimeError("Base synthetic data is required before Phase 6 demo data can be added.")
        staff = db.query(User).filter(User.role.in_([SystemRole.HOSPITAL_ADMIN.value, SystemRole.SUPER_ADMIN.value, "ADMIN"])).first() or db.query(User).first()
        patient_role = db.query(Role).filter(Role.name == SystemRole.PATIENT.value).first()
        if not staff:
            raise RuntimeError("A synthetic user is required before Phase 6 data can be added.")
        tests = {
            "CBC": ("Complete Blood Count", "Hematology", "Whole blood", 450.0, (("HGB", "Hemoglobin", "g/dL", 12, 17), ("RBC", "RBC", "million/uL", 4.2, 5.8), ("WBC", "WBC", "/uL", 4000, 11000), ("PLT", "Platelets", "/uL", 150000, 450000), ("HCT", "Hematocrit", "%", 36, 50), ("MCV", "MCV", "fL", 80, 100), ("MCH", "MCH", "pg", 27, 33), ("MCHC", "MCHC", "g/dL", 32, 36))),
            "LFT": ("Liver Function Test", "Biochemistry", "Serum", 650.0, (("BILT", "Bilirubin Total", "mg/dL", .2, 1.2), ("BILD", "Bilirubin Direct", "mg/dL", 0, .3), ("AST", "SGOT / AST", "U/L", 10, 40), ("ALT", "SGPT / ALT", "U/L", 7, 56), ("ALP", "ALP", "U/L", 44, 147), ("ALB", "Albumin", "g/dL", 3.5, 5.0))),
            "KFT": ("Kidney Function Test", "Biochemistry", "Serum", 650.0, (("CREAT", "Creatinine", "mg/dL", .6, 1.3), ("UREA", "Blood Urea", "mg/dL", 7, 20), ("URIC", "Uric Acid", "mg/dL", 3.4, 7.0), ("NA", "Sodium", "mEq/L", 135, 145), ("K", "Potassium", "mEq/L", 3.5, 5.1))),
            "LIPID": ("Lipid Profile", "Biochemistry", "Serum", 700.0, (("TC", "Total Cholesterol", "mg/dL", 0, 200), ("HDL", "HDL", "mg/dL", 40, 100), ("LDL", "LDL", "mg/dL", 0, 100), ("TG", "Triglycerides", "mg/dL", 0, 150))),
        }
        catalog = {row.code: row for row in db.query(LabTestCatalog).all()}
        for code, (name, category, specimen, price, components) in tests.items():
            row = catalog.get(code)
            if not row:
                row = LabTestCatalog(code=code, name=name, category=category, specimen_type=specimen, price=price)
                db.add(row); db.flush(); catalog[code] = row
            existing = {component.code for component in db.query(LabTestComponent).filter(LabTestComponent.test_id == row.id).all()}
            for order, (component_code, component_name, unit, low, high) in enumerate(components, 1):
                if component_code not in existing:
                    db.add(LabTestComponent(test_id=row.id, code=component_code, name=component_name, unit=unit, reference_low=low, reference_high=high, reference_text=f"{low}–{high}", display_order=order))
        provider = db.query(InsuranceProvider).filter(InsuranceProvider.code == "SYNTH-TPA").first()
        if not provider:
            provider = InsuranceProvider(name="ANVAYA Synthetic Health Cover", code="SYNTH-TPA", tpa_name="ANVAYA Demo TPA", phone="+91 22 4000 0000", email="tpa@anvaya.demo")
            db.add(provider); db.flush()
        password_hash = get_password_hash("PatientPortal123!")
        for index, patient in enumerate(patients, 1):
            if not db.query(PatientPortalLink).filter(PatientPortalLink.patient_id == patient.id).first():
                username = f"portal{index:03d}"
                user = User(username=username, email=f"{username}@anvaya.demo", hashed_password=password_hash, full_name=f"{patient.first_name} {patient.last_name} Portal", role=SystemRole.PATIENT.value, branch_id=patient.registered_branch_id, is_active=True)
                if patient_role:
                    user.roles.append(patient_role)
                db.add(user); db.flush(); db.add(PatientPortalLink(patient_id=patient.id, user_id=user.id))
            policy = db.query(InsurancePolicy).filter(InsurancePolicy.patient_id == patient.id).first()
            if not policy:
                policy = InsurancePolicy(patient_id=patient.id, provider_id=provider.id, policy_number=f"SYN-POL-{index:05d}", member_id=f"SYN-MEM-{index:05d}", coverage_amount=250000, valid_from=date.today() - timedelta(days=30), valid_to=date.today() + timedelta(days=335))
                db.add(policy)
        active = db.query(Admission).filter(Admission.status == "ACTIVE").first()
        if active and not db.query(Discharge).filter(Discharge.admission_id == active.id).first():
            db.add(Discharge(admission_id=active.id, patient_id=active.patient_id, attending_doctor_id=active.attending_doctor_id, initiated_by_id=staff.id, status="CLEARANCE_PENDING", discharge_reason="Synthetic planned discharge", diagnosis_summary="Synthetic academic demonstration diagnosis.", clinical_summary="Synthetic discharge summary; human review required.", clinical_cleared=True, pending_results_checked=True))
        db.add(AuditLog(action="PHASE6_DEMO_DATA_SEEDED", entity_type="SYSTEM", actor_id=staff.id, actor_email=staff.email, branch_id=branches[0].id, notes="Synthetic Phase 6 catalogs, portal accounts, insurance policies and controlled discharge case added without reset."))
        db.commit()
        print("Seeded Phase 6 synthetic catalog, portal, insurance, and discharge demo data.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
