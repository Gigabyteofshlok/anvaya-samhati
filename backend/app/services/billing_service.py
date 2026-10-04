from sqlalchemy.orm import Session

from app.models.phase5 import Invoice, InvoiceItem, PatientAccount


def _number(prefix: str, model, field: str, db: Session) -> str:
    return f"{prefix}-{db.query(model).count() + 1:06d}"


def add_event_charge(
    db: Session, *, patient_id: str, branch_id: str, charge_type: str, description: str,
    amount: float, source_entity_type: str, source_entity_id: str, encounter_id: str | None = None,
    admission_id: str | None = None,
) -> Invoice:
    """Append a source-linked charge to a patient's open invoice in the caller transaction."""
    account = db.query(PatientAccount).filter(PatientAccount.patient_id == patient_id).first()
    if not account:
        account = PatientAccount(patient_id=patient_id)
        db.add(account)
        db.flush()
    invoice = db.query(Invoice).filter(
        Invoice.patient_id == patient_id, Invoice.status == "OPEN", Invoice.branch_id == branch_id
    ).first()
    if not invoice:
        invoice = Invoice(
            invoice_number=_number("INV", Invoice, "invoice_number", db), patient_account_id=account.id,
            patient_id=patient_id, branch_id=branch_id, encounter_id=encounter_id, admission_id=admission_id,
        )
        db.add(invoice)
        db.flush()
    item = InvoiceItem(
        invoice_id=invoice.id, charge_type=charge_type, description=description,
        source_entity_type=source_entity_type, source_entity_id=source_entity_id,
        unit_price=amount, amount=amount,
    )
    db.add(item)
    invoice.subtotal = round(float(invoice.subtotal or 0) + amount, 2)
    invoice.total_amount = round(invoice.subtotal - float(invoice.discount_amount or 0) + float(invoice.tax_amount or 0), 2)
    account.balance = round(float(account.balance or 0) + amount, 2)
    return invoice
