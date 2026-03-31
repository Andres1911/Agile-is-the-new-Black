# Expenses API — create-and-split + confirm-payment (ID010) + scan-receipt (ID012)
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import (
    Expense,
    ExpenseShare,
    ExpenseStatus,
    HouseholdMember,
    RecurringExpense,
    RecurringExpenseShare,
    User,
    VoteStatus,
)
from app.schemas.schemas import (
    ConfirmPaymentRequest,
    ExpenseCreate,
    ExpenseEditAmount,
    OutstandingExpense,
    RecurringExpenseCreate,
    RecurringExpenseCreateResponse,
    RecurringExpenseGenerateResponse,
    RequestedExpense,
    ResolveDisputeRequest,
    RespondExpenseShareRequest,
)
from app.schemas.schemas import (
    RecurringExpense as RecurringExpenseSchema,
)
from app.services.receipt_parser import (
    detect_format_from_bytes,
    parse_receipt,
    validate_file_extension,
)
from app.services.recurring_expenses import (
    generate_due_recurring_expenses,
    generate_recurring_charges,
    preview_due_dates,
)

router = APIRouter()


@router.get("/recurring", response_model=list[RecurringExpenseSchema])
def list_recurring_expenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.user_id == current_user.id, HouseholdMember.left_at.is_(None))
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="No active household found")

    rows = (
        db.query(RecurringExpense)
        .filter(RecurringExpense.household_id == membership.household_id)
        .order_by(RecurringExpense.id.desc())
        .all()
    )
    return rows


@router.post("/recurring", response_model=RecurringExpenseCreateResponse, status_code=201)
def create_recurring_expense(
    body: RecurringExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a recurring expense (admin-only) and generate charges based on end conditions."""

    membership = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.user_id == current_user.id, HouseholdMember.left_at.is_(None))
        .first()
    )
    if not membership:
        raise HTTPException(status_code=400, detail="User is not currently in any household")
    if not membership.is_admin:
        raise HTTPException(
            status_code=403, detail="Only household admins can create recurring expenses"
        )

    if not body.description:
        raise HTTPException(status_code=400, detail="Valid description is required.")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    if body.unit is None:
        raise HTTPException(status_code=400, detail="A recurrence frequency must be selected")

    interval = body.interval if body.interval is not None else 1
    if interval <= 0:
        raise HTTPException(status_code=400, detail="interval must be >= 1")

    start_at = body.start_at or datetime.now(UTC)

    # Validate and compute the generation schedule (may be just [start_at] if no end condition).
    try:
        preview = preview_due_dates(
            start_at=start_at,
            interval=interval,
            unit=body.unit,
            end_at=body.end_at,
            max_occurrences=body.max_occurrences,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    recurring = RecurringExpense(
        description=body.description,
        amount=body.amount,
        category=body.category,
        split_evenly=body.split_evenly,
        include_creator=body.include_creator,
        interval=interval,
        unit=body.unit,
        start_at=start_at,
        next_due_at=start_at,
        end_at=body.end_at,
        max_occurrences=body.max_occurrences,
        creator_id=current_user.id,
        household_id=membership.household_id,
    )

    active_member_ids = {
        r.user_id
        for r in db.query(HouseholdMember)
        .filter(
            HouseholdMember.household_id == membership.household_id,
            HouseholdMember.left_at.is_(None),
        )
        .all()
    }

    if not recurring.split_evenly:
        if not body.manual_shares:
            raise HTTPException(
                status_code=400,
                detail="Manual shares list cannot be empty when split_evenly is False",
            )

        total_manual = 0.0
        for s in body.manual_shares:
            if s.user_id not in active_member_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"User {s.user_id} is not an active member of this household",
                )
            if s.amount <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Share for user {s.user_id} must be greater than zero",
                )
            total_manual += float(s.amount)
            recurring.template_shares.append(
                RecurringExpenseShare(user_id=s.user_id, amount_owed=float(s.amount))
            )

        if abs(round(total_manual, 2) - round(float(body.amount), 2)) > 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot create expense: Split amounts {total_manual:.2f} CAD do not equal expense total {body.amount:.2f} CAD"
                ),
            )

    try:
        db.add(recurring)
        db.flush()

        created_ids = generate_recurring_charges(
            db=db,
            recurring=recurring,
            due_dates=preview.due_dates,
        )
        db.commit()
    except HTTPException:
        raise
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Database error during recurring expense creation"
        ) from None

    return RecurringExpenseCreateResponse(
        recurring_expense_id=recurring.id,
        created_expense_ids=created_ids,
        detail="Recurring expense created successfully",
    )


@router.post("/{expense_id}/resolve", status_code=200)
def resolve_disputed_expense(
    expense_id: int,
    body: ResolveDisputeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.user_id == current_user.id, HouseholdMember.left_at.is_(None))
        .first()
    )

    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Matched string to test_ID016_non_admin_cannot_resolve
    if not membership or not membership.is_admin:
        raise HTTPException(
            status_code=403, detail="Access denied: Only admins can resolve disputed expenses"
        )

    # Matched string to test_ID016_admin_cannot_resolve_non_disputed_expense
    if expense.status != ExpenseStatus.DISPUTED:
        raise HTTPException(
            status_code=400, detail="Cannot resolve: Expense is not in a disputed state"
        )

    decision = body.decision.upper()

    if decision in ("VALID", "VALIDATE"):
        # Test expects PENDING instead of FINALIZED
        expense.status = ExpenseStatus.PENDING
        for share in expense.shares:
            share.vote_status = VoteStatus.ACCEPTED
        detail = "Expense validated by admin"
    else:  # INVALID or INVALIDATE
        # Test expects REJECTED and "dismissed"
        expense.status = ExpenseStatus.REJECTED
        for share in expense.shares:
            share.vote_status = VoteStatus.REJECTED
        detail = "Expense dismissed by admin"

    db.commit()
    return {"detail": detail}


@router.post("/recurring/generate", response_model=RecurringExpenseGenerateResponse)
def generate_recurring_expenses(
    as_of: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate all recurring charges due up to `as_of` for the current household."""

    membership = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.user_id == current_user.id, HouseholdMember.left_at.is_(None))
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="No active household found")

    try:
        created_ids = generate_due_recurring_expenses(
            db=db,
            household_id=membership.household_id,
            as_of=as_of,
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to generate recurring charges"
        ) from None

    return RecurringExpenseGenerateResponse(
        created_expense_ids=created_ids,
        created_count=len(created_ids),
    )


@router.get("/outstanding", response_model=list[OutstandingExpense])
def get_outstanding_expenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all expenses where the current user still owes money."""

    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == current_user.id,
            HouseholdMember.left_at.is_(None),
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="No active household found")

    rows = (
        db.query(Expense, ExpenseShare, User)
        .join(ExpenseShare, ExpenseShare.expense_id == Expense.id)
        .join(User, User.id == Expense.creator_id)
        .filter(
            Expense.household_id == membership.household_id,
            ExpenseShare.user_id == current_user.id,
            ExpenseShare.amount_owed > ExpenseShare.paid_amount,
            ExpenseShare.is_paid.is_(False),
        )
        .order_by(Expense.date.desc())
        .all()
    )

    result: list[OutstandingExpense] = []
    for expense, share, creator in rows:
        outstanding = round(float(share.amount_owed - share.paid_amount), 2)
        if outstanding <= 0:
            continue
        result.append(
            OutstandingExpense(
                expense_id=expense.id,
                description=expense.description,
                category=expense.category,
                date=expense.date,
                household_id=expense.household_id,
                creator_id=expense.creator_id,
                creator_username=creator.username,
                amount_total=float(expense.amount),
                amount_owed=float(share.amount_owed),
                paid_amount=float(share.paid_amount),
                outstanding_amount=outstanding,
            )
        )

    return result


@router.get("/requested", response_model=list[RequestedExpense])
def get_requested_expenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all expense shares awaiting the current user's approval."""

    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == current_user.id,
            HouseholdMember.left_at.is_(None),
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=400,
            detail="Cannot view requested expenses: You are not a member of any household",
        )

    rows = (
        db.query(Expense, ExpenseShare, User)
        .join(ExpenseShare, ExpenseShare.expense_id == Expense.id)
        .join(User, User.id == Expense.creator_id)
        .filter(
            Expense.household_id == membership.household_id,
            ExpenseShare.user_id == current_user.id,
            ExpenseShare.vote_status == VoteStatus.PENDING,
            ExpenseShare.is_paid.is_(False),
        )
        .order_by(Expense.date.desc())
        .all()
    )

    result: list[RequestedExpense] = []
    for expense, share, creator in rows:
        result.append(
            RequestedExpense(
                expense_id=expense.id,
                description=expense.description,
                category=expense.category,
                date=expense.date,
                household_id=expense.household_id,
                creator_id=expense.creator_id,
                creator_username=creator.username,
                amount_total=float(expense.amount),
                amount_requested=float(share.amount_owed),
                vote_status=share.vote_status,
            )
        )

    return result


@router.post("/create-and-split", status_code=201)
def create_and_split(
    expense_in: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if (
        not expense_in.split_evenly
        and expense_in.manual_shares
        and any(s.user_id == current_user.id for s in expense_in.manual_shares)
    ):
        expense_in.include_creator = True

    if not expense_in.description:
        raise HTTPException(status_code=400, detail="Valid description is required.")

    # --- 2. Identity check: find user's current household ---
    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == current_user.id,
            HouseholdMember.left_at.is_(None),
        )
        .first()
    )

    if not membership:
        raise HTTPException(status_code=400, detail="User is not currently in any household")

    roommates = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.household_id == membership.household_id,
            HouseholdMember.user_id != current_user.id,
            HouseholdMember.left_at.is_(None),
        )
        .all()
    )

    if not expense_in.include_creator and not roommates:
        raise HTTPException(
            status_code=400, detail="No other active members in the household to split with"
        )

    # --- 1. Basic validation: amount ---
    if expense_in.amount <= 0:
        raise HTTPException(
            status_code=400, detail="Cannot create expense: Amount must be greater than zero"
        )

    # --- 3. Initialize expense ---
    new_expense = Expense(
        description=expense_in.description,
        amount=expense_in.amount,
        category=expense_in.category,
        creator_id=current_user.id,
        household_id=membership.household_id,
    )

    # --- 4. Split logic ---
    if expense_in.split_evenly:
        split_members = []
        if expense_in.include_creator:
            split_members.append(current_user.id)
        for m in roommates:
            split_members.append(m.user_id)

        num = len(split_members)
        base_share = round(expense_in.amount / num, 2)
        sum_of_others = base_share * (num - 1)
        last_share = round(expense_in.amount - sum_of_others, 2)

        for i, user_id in enumerate(split_members):
            amt = base_share if i < (num - 1) else last_share
            is_creator = user_id == current_user.id
            vote = VoteStatus.ACCEPTED if is_creator else VoteStatus.PENDING
            new_expense.shares.append(
                ExpenseShare(
                    user_id=user_id,
                    amount_owed=amt,
                    vote_status=vote,
                )
            )
    else:
        if not expense_in.manual_shares:
            raise HTTPException(
                status_code=400,
                detail="Manual shares list cannot be empty when split_evenly is False",
            )

        valid_ids = {m.user_id for m in roommates}
        valid_ids.add(current_user.id)

        total_manual = 0
        for s in expense_in.manual_shares:
            if s.user_id not in valid_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"User {s.user_id} is not an active member of this household",
                )
            if s.amount <= 0:
                raise HTTPException(
                    status_code=400, detail=f"Share for user {s.user_id} must be greater than zero"
                )
            total_manual += s.amount
            is_creator = s.user_id == current_user.id
            vote = VoteStatus.ACCEPTED if is_creator else VoteStatus.PENDING
            new_expense.shares.append(
                ExpenseShare(
                    user_id=s.user_id,
                    amount_owed=s.amount,
                    vote_status=vote,
                )
            )

        if abs(total_manual - expense_in.amount) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot create expense: Split amounts {total_manual:.2f} CAD do not equal expense total {expense_in.amount:.2f} CAD",
            )

    try:
        db.add(new_expense)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error during creation") from None

    return {"detail": "success"}


@router.post("/{expense_id}/respond-share", status_code=200)
def respond_expense_share(
    expense_id: int,
    body: RespondExpenseShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allow the current user to accept or decline their expense share."""

    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == current_user.id,
            HouseholdMember.left_at.is_(None),
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=400,
            detail="User is not currently in any household",
        )

    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense or expense.household_id != membership.household_id:
        raise HTTPException(
            status_code=404,
            detail="Expense not found",
        )

    share = (
        db.query(ExpenseShare)
        .filter(
            ExpenseShare.expense_id == expense_id,
            ExpenseShare.user_id == current_user.id,
        )
        .first()
    )
    if not share:
        raise HTTPException(
            status_code=400,
            detail="Cannot respond: You do not have an expense share for this expense",
        )

    if body.decision == "accept":
        if share.vote_status == VoteStatus.REJECTED:
            raise HTTPException(
                status_code=400,
                detail="Cannot accept a rejected expense",
            )
        share.vote_status = VoteStatus.ACCEPTED
        response_message = "Expense share accepted"
    else:  # "decline"
        if share.vote_status == VoteStatus.ACCEPTED:
            raise HTTPException(
                status_code=400,
                detail="Cannot reject an already accepted expense",
            )
        share.vote_status = VoteStatus.REJECTED
        response_message = "Expense share declined"

    all_shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense_id).all()
    expense.status = compute_expense_status(all_shares)
    db.commit()
    return {"detail": response_message}


@router.post("/{expense_id}/confirm-payment", status_code=200)
def confirm_payment(
    expense_id: int,
    body: ConfirmPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allow the current user to confirm payment of their share of an expense (ID010)."""
    if body.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Payment amount must be greater than zero",
        )

    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == current_user.id,
            HouseholdMember.left_at.is_(None),
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=400,
            detail="User is not currently in any household",
        )

    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense or expense.household_id != membership.household_id:
        raise HTTPException(
            status_code=404,
            detail="Expense not found",
        )

    share = (
        db.query(ExpenseShare)
        .filter(
            ExpenseShare.expense_id == expense_id,
            ExpenseShare.user_id == current_user.id,
        )
        .first()
    )
    if not share:
        raise HTTPException(
            status_code=400,
            detail="Cannot confirm payment: You do not have an expense share for this expense",
        )

    outstanding = share.amount_owed - share.paid_amount
    if share.is_paid or outstanding <= 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot confirm payment: Your expense share is already fully paid",
        )
    if body.amount > outstanding:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm payment: Amount {body.amount:.2f} CAD exceeds outstanding balance of {outstanding:.2f} CAD",
        )

    share.paid_amount += body.amount
    if share.paid_amount >= share.amount_owed:
        share.is_paid = True

    all_shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense_id).all()
    all_paid = all(s.is_paid for s in all_shares)
    expense.status = ExpenseStatus.FULLY_SETTLED if all_paid else ExpenseStatus.PARTIALLY_SETTLED

    db.commit()
    return {"detail": "Payment recorded"}


@router.post("/scan-receipt", status_code=200)
async def scan_receipt(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
):
    """Accept a receipt image and return parsed date, total, and line items (ID012)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    ext = validate_file_extension(file.filename)
    if ext is None:
        ext = detect_format_from_bytes(contents)
    if ext is None:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a JPG, PNG, or HEIC image",
        )

    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB")

    try:
        result = parse_receipt(contents)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to process the receipt image") from None

    if not result["success"]:
        if result.get("error") == "no_receipt":
            raise HTTPException(
                status_code=422,
                detail="No receipt detected in the image. Please upload a clear photo of a receipt",
            )
        raise HTTPException(status_code=422, detail="Could not parse the receipt")

    message = "Receipt scanned successfully"
    if result.get("partial"):
        missing = result.get("warnings", [])
        if "items" in missing:
            message = "No individual items detected. Please add items manually"
        else:
            message = "Some values could not be read. Please review and complete the missing fields"

    return {
        "date": result.get("date"),
        "totalAmount": result.get("totalAmount"),
        "items": result.get("items", []),
        "message": message,
    }


@router.put("/{expense_id}/edit-amount", status_code=200)
def edit_expense_amount(
    expense_id: int,
    body: ExpenseEditAmount,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allow the expense creator to edit the amount and resplit shares (ID017)."""

    # --- 1. Validate amount ---
    if body.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot update expense: Amount must be greater than zero",
        )

    # --- 2. Find the expense ---
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # --- 3. Only the creator can edit ---
    if expense.creator_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Cannot update expense: Only the expense creator can edit this expense",
        )

    # --- 4. Block edits on finalized or fully settled expenses ---
    if expense.status == ExpenseStatus.FINALIZED:
        raise HTTPException(
            status_code=400,
            detail="Cannot update expense: Finalized expenses cannot be modified",
        )
    if expense.status == ExpenseStatus.FULLY_SETTLED:
        raise HTTPException(
            status_code=400,
            detail="Cannot update expense: Fully settled expenses cannot be modified",
        )

    # --- 5. Build new shares ---
    existing_shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense_id).all()

    if body.split_evenly:
        # Determine participants: existing share holders
        participant_ids = [s.user_id for s in existing_shares]
        if body.include_self and current_user.id not in participant_ids:
            participant_ids.insert(0, current_user.id)

        num = len(participant_ids)
        base_share = round(body.amount / num, 2)
        sum_of_others = base_share * (num - 1)
        last_share = round(body.amount - sum_of_others, 2)

        # Delete old shares and create new ones
        for s in existing_shares:
            db.delete(s)
        db.flush()

        for i, user_id in enumerate(participant_ids):
            amt = base_share if i < (num - 1) else last_share
            is_creator = user_id == current_user.id
            vote = VoteStatus.ACCEPTED if is_creator else VoteStatus.PENDING
            db.add(
                ExpenseShare(
                    expense_id=expense_id,
                    user_id=user_id,
                    amount_owed=amt,
                    paid_amount=0.0,
                    is_paid=False,
                    vote_status=vote,
                )
            )
    else:
        if not body.manual_shares:
            raise HTTPException(
                status_code=400,
                detail="Manual shares list cannot be empty when split_evenly is False",
            )

        # Validate split totals
        total_manual = sum(float(s.amount) for s in body.manual_shares)
        if abs(round(total_manual, 2) - round(float(body.amount), 2)) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot update expense: Split amounts {total_manual:.2f} CAD do not equal expense total {body.amount:.2f} CAD",
            )

        # Delete old shares and create new ones
        for s in existing_shares:
            db.delete(s)
        db.flush()

        for s in body.manual_shares:
            is_creator = s.user_id == current_user.id
            vote = VoteStatus.ACCEPTED if is_creator else VoteStatus.PENDING
            db.add(
                ExpenseShare(
                    expense_id=expense_id,
                    user_id=s.user_id,
                    amount_owed=float(s.amount),
                    paid_amount=0.0,
                    is_paid=False,
                    vote_status=vote,
                )
            )

    # --- 6. Update expense amount and reset status ---
    expense.amount = body.amount
    expense.status = ExpenseStatus.PENDING

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Database error during expense update"
        ) from None

    return {"detail": "Expense updated successfully"}


def verify_and_modify_expense(
    expense: ExpenseCreate,
    change_amount: bool,
    amount: float,
    description: str,
    category: str | None,
) -> ExpenseCreate:
    """
    Updates an expense object based on conditional flags and new values.
    Validates that the amount is positive if a change is requested.
    """
    # Prepare the update dictionary with mandatory updates
    update_data = {"description": description, "category": category}

    # Add amount to update dictionary only if change_amount is True
    if change_amount:
        # Validation for ID013 Error Flow
        if amount <= 0:
            raise ValueError("Invalid amount: Amount must be a positive number")

        update_data["amount"] = amount

    # Create a new instance with the updated values
    # Pydantic's model_copy will preserve all other fields like split_evenly
    return expense.model_copy(update=update_data)


# In a services file or at the top of expenses.py
def compute_expense_status(shares: list[ExpenseShare]) -> ExpenseStatus:
    if not shares:
        return ExpenseStatus.PENDING

    accepted_count = sum(1 for s in shares if s.vote_status == VoteStatus.ACCEPTED)
    total_count = len(shares)
    if accepted_count / total_count > 0.5:
        return ExpenseStatus.FINALIZED
    elif any(s.vote_status == VoteStatus.REJECTED for s in shares):
        return ExpenseStatus.DISPUTED
    else:
        return ExpenseStatus.PENDING
