# Expenses API — create-and-split + confirm-payment (ID010)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import (
    Expense,
    ExpenseShare,
    ExpenseStatus,
    HouseholdMember,
    User,
    VoteStatus,
)
from app.schemas.schemas import (
    ConfirmPaymentRequest,
    ExpenseCreate,
    OutstandingExpense,
    RequestedExpense,
    RespondExpenseShareRequest,
)

router = APIRouter()


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
        share.vote_status = VoteStatus.ACCEPTED
        response_message = "Expense share accepted"
    else:  # "decline"
        share.vote_status = VoteStatus.REJECTED
        response_message = "Expense share declined"

    all_shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense_id).all()

    if any(s.vote_status == VoteStatus.REJECTED for s in all_shares):
        expense.status = ExpenseStatus.DISPUTED
    elif all(s.vote_status == VoteStatus.ACCEPTED for s in all_shares):
        expense.status = ExpenseStatus.FINALIZED
    else:
        expense.status = ExpenseStatus.PENDING

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
