from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import assert_patient_scope, require_permission
from app.core.database import get_db
from app.models.clinical import PatientEvent
from app.models.identity import User
from app.models.phase5 import Invoice, Payment, PatientAccount
from app.schemas.phase5 import PaymentCreate
from app.services.audit_service import log_audit

router = APIRouter(prefix="/billing", tags=["Billing"])


def invoice_out(invoice: Invoice) -> dict:
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "status": invoice.status,
        "patient_id": invoice.patient_id,
        "patient_name": (
            f"{invoice.patient.first_name} {invoice.patient.last_name}"
        ),
        "subtotal": invoice.subtotal,
        "discount_amount": invoice.discount_amount,
        "tax_amount": invoice.tax_amount,
        "total_amount": invoice.total_amount,
        "paid_amount": invoice.paid_amount,
        "outstanding_balance": round(
            invoice.total_amount - invoice.paid_amount,
            2,
        ),
        "created_at": invoice.created_at,
        "items": [
            {
                "id": row.id,
                "charge_type": row.charge_type,
                "description": row.description,
                "quantity": row.quantity,
                "unit_price": row.unit_price,
                "amount": row.amount,
            }
            for row in invoice.items
        ],
        "payments": [
            {
                "id": row.id,
                "amount": row.amount,
                "method": row.payment_method,
                "received_at": row.received_at,
            }
            for row in invoice.payments
        ],
    }


@router.get("/invoices")
def list_invoices(
    patient_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("billing.view")
    ),
):
    query = db.query(Invoice).options(
        joinedload(Invoice.patient),
        joinedload(Invoice.items),
        joinedload(Invoice.payments),
    )

    if patient_id:
        assert_patient_scope(
            db,
            current_user,
            patient_id,
        )
        query = query.filter(
            Invoice.patient_id == patient_id
        )

    elif current_user.role == "PATIENT":
        from app.models.phase6 import PatientPortalLink

        link = (
            db.query(PatientPortalLink)
            .filter(
                PatientPortalLink.user_id == current_user.id
            )
            .first()
        )

        if not link:
            return []

        query = query.filter(
            Invoice.patient_id == link.patient_id
        )

    return [
        invoice_out(row)
        for row in query
        .order_by(Invoice.created_at.desc())
        .limit(200)
        .all()
    ]


@router.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("billing.view")
    ),
):
    invoice = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.patient),
            joinedload(Invoice.items),
            joinedload(Invoice.payments),
        )
        .filter(Invoice.id == invoice_id)
        .first()
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found.",
        )

    assert_patient_scope(
        db,
        current_user,
        invoice.patient_id,
    )

    return invoice_out(invoice)


@router.post(
    "/invoices/{invoice_id}/payments",
    status_code=status.HTTP_201_CREATED,
)
def record_payment(
    invoice_id: str,
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("billing.manage")
    ),
):
    try:
        # ---------------------------------------------------------
        # 1. Lock ONLY the invoice row.
        #
        # Do NOT joinedload Invoice.account here.
        # PostgreSQL rejects:
        # LEFT OUTER JOIN + FOR UPDATE
        # ---------------------------------------------------------
        invoice = (
            db.query(Invoice)
            .filter(Invoice.id == invoice_id)
            .with_for_update()
            .first()
        )

        if not invoice:
            raise HTTPException(
                status_code=404,
                detail="Invoice not found.",
            )

        if invoice.status == "PAID":
            raise HTTPException(
                status_code=409,
                detail="Invoice is already fully paid.",
            )

        # ---------------------------------------------------------
        # 2. Validate payment amount
        # ---------------------------------------------------------
        due = round(
            float(invoice.total_amount)
            - float(invoice.paid_amount),
            2,
        )

        amount = round(float(data.amount), 2)

        if amount <= 0:
            raise HTTPException(
                status_code=422,
                detail="Payment amount must be greater than zero.",
            )

        if due <= 0:
            raise HTTPException(
                status_code=409,
                detail="Invoice has no outstanding balance.",
            )

        if amount > due:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Payment exceeds invoice balance. "
                    f"Outstanding balance is ₹{due:.2f}."
                ),
            )

        # ---------------------------------------------------------
        # 3. Lock PatientAccount separately.
        #
        # This avoids the PostgreSQL outer-join FOR UPDATE problem.
        # ---------------------------------------------------------
        account = (
            db.query(PatientAccount)
            .filter(
                PatientAccount.id
                == invoice.patient_account_id
            )
            .with_for_update()
            .first()
        )

        if not account:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Patient account not found for this invoice."
                ),
            )

        # ---------------------------------------------------------
        # 4. Create payment
        # ---------------------------------------------------------
        payment = Payment(
            invoice_id=invoice.id,
            received_by_id=current_user.id,
            amount=amount,
            payment_method=data.payment_method,
            reference_number=data.reference_number,
        )

        # ---------------------------------------------------------
        # 5. Update invoice
        # ---------------------------------------------------------
        new_paid_amount = round(
            float(invoice.paid_amount) + amount,
            2,
        )

        total_amount = round(
            float(invoice.total_amount),
            2,
        )

        # Protect against floating-point rounding.
        if new_paid_amount >= total_amount:
            new_paid_amount = total_amount
            invoice.status = "PAID"
        else:
            invoice.status = "OPEN"

        invoice.paid_amount = new_paid_amount

        # ---------------------------------------------------------
        # 6. Update patient account balance
        # ---------------------------------------------------------
        account.balance = round(
            float(account.balance) - amount,
            2,
        )

        # ---------------------------------------------------------
        # 7. Persist payment
        # ---------------------------------------------------------
        db.add(payment)

        # ---------------------------------------------------------
        # 8. Patient timeline event
        # ---------------------------------------------------------
        patient_event = PatientEvent(
            patient_id=invoice.patient_id,
            actor_id=current_user.id,
            event_type="PAYMENT_RECORDED",
            title="Payment recorded",
            description=(
                f"{data.payment_method}: ₹{amount:.2f}"
            ),
            source_module="BILLING",
        )

        db.add(patient_event)

        # ---------------------------------------------------------
        # 9. Flush first so payment.id exists before audit.
        # ---------------------------------------------------------
        db.flush()

        # ---------------------------------------------------------
        # 10. Audit log
        # ---------------------------------------------------------
        log_audit(
            db,
            action="PAYMENT_RECORDED",
            entity_type="PAYMENT",
            entity_id=payment.id,
            actor_id=current_user.id,
            actor_email=current_user.email,
            branch_id=invoice.branch_id,
        )

        # ---------------------------------------------------------
        # 11. Commit everything atomically
        # ---------------------------------------------------------
        db.commit()

        # ---------------------------------------------------------
        # 12. Return updated payment state
        # ---------------------------------------------------------
        outstanding = round(
            total_amount - new_paid_amount,
            2,
        )

        return {
            "id": payment.id,
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "invoice_status": invoice.status,
            "payment_amount": amount,
            "paid_amount": new_paid_amount,
            "outstanding_balance": outstanding,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("billing.view")
    ),
):
    invoices = db.query(Invoice).all()

    return {
        "invoices": len(invoices),
        "open_invoices": sum(
            1
            for item in invoices
            if item.status == "OPEN"
        ),
        "revenue": round(
            sum(
                float(item.paid_amount or 0)
                for item in invoices
            ),
            2,
        ),
        "outstanding": round(
            sum(
                float(item.total_amount or 0)
                - float(item.paid_amount or 0)
                for item in invoices
            ),
            2,
        ),
    }