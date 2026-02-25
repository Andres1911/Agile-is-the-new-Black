from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import Expense, ExpenseShare, HouseholdMember, User as UserModel, VoteStatus

router = APIRouter()


@router.get("/me/balances")
def get_user_balances(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get outstanding balances for the current user across all their households.
    
    Returns:
    {
        "households": [
            {
                "id": <int>,
                "name": <str>,
                "owed_by_me": <float>,  # Sum of amount_owed where user is payer, vote_status=ACCEPTED, is_paid=False
                "owed_to_me": <float>,  # Sum of amount_owed where user is payee, vote_status=ACCEPTED, is_paid=False
            }
        ],
        "shares": [
            {
                "id": <int>,
                "expense_id": <int>,
                "expense_description": <str>,
                "payer": <str>,  # username
                "payee": <str>,  # username
                "amount_owed": <float>,
                "vote_status": <str>,
                "is_paid": <bool>,
            }
        ]
    }
    """
    # Get all households the user is a member of (not left)
    household_memberships = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.user_id == current_user.id, HouseholdMember.left_at.is_(None))
        .all()
    )

    if not household_memberships:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot view expenses: You are not a member of any household",
        )

    household_ids = [m.household_id for m in household_memberships]

    # Build household summaries
    households_data = []
    for hm in household_memberships:
        hh = hm.household
        
        # Get shares where user owes money (is payer)
        owed_by_me = (
            db.query(ExpenseShare)
            .join(Expense, ExpenseShare.expense_id == Expense.id)
            .filter(
                Expense.household_id == hh.id,
                ExpenseShare.user_id == current_user.id,
                ExpenseShare.vote_status == VoteStatus.ACCEPTED,
                ExpenseShare.is_paid == False,
            )
            .with_entities(func.sum(ExpenseShare.amount_owed))
            .scalar()
        ) or 0.0

        # Get shares where user is owed (is payee, i.e., expense creator)
        owed_to_me = (
            db.query(ExpenseShare)
            .join(Expense, ExpenseShare.expense_id == Expense.id)
            .filter(
                Expense.household_id == hh.id,
                Expense.creator_id == current_user.id,
                ExpenseShare.vote_status == VoteStatus.ACCEPTED,
                ExpenseShare.is_paid == False,
            )
            .with_entities(func.sum(ExpenseShare.amount_owed))
            .scalar()
        ) or 0.0

        households_data.append({
            "id": hh.id,
            "name": hh.name,
            "owed_by_me": float(owed_by_me),
            "owed_to_me": float(owed_to_me),
        })

    # Get all unpaid, accepted shares for the user across all their households
    # (both as payer and payee)
    shares_as_payer = (
        db.query(ExpenseShare, Expense)
        .join(Expense, ExpenseShare.expense_id == Expense.id)
        .filter(
            Expense.household_id.in_(household_ids),
            ExpenseShare.user_id == current_user.id,
            ExpenseShare.vote_status == VoteStatus.ACCEPTED,
            ExpenseShare.is_paid == False,
        )
        .all()
    )

    shares_as_payee = (
        db.query(ExpenseShare, Expense)
        .join(Expense, ExpenseShare.expense_id == Expense.id)
        .filter(
            Expense.household_id.in_(household_ids),
            Expense.creator_id == current_user.id,
            ExpenseShare.vote_status == VoteStatus.ACCEPTED,
            ExpenseShare.is_paid == False,
        )
        .all()
    )

    shares_data = []
    
    # Add shares where user owes money
    for share, expense in shares_as_payer:
        payee = db.query(UserModel).filter(UserModel.id == expense.creator_id).first()
        shares_data.append({
            "id": share.id,
            "expense_id": expense.id,
            "expense_description": expense.description,
            "payer": current_user.username,
            "payee": payee.username if payee else "Unknown",
            "amount_owed": float(share.amount_owed),
            "vote_status": share.vote_status.value,
            "is_paid": share.is_paid,
        })

    # Add shares where user is owed money
    for share, expense in shares_as_payee:
        payer = db.query(UserModel).filter(UserModel.id == share.user_id).first()
        shares_data.append({
            "id": share.id,
            "expense_id": expense.id,
            "expense_description": expense.description,
            "payer": payer.username if payer else "Unknown",
            "payee": current_user.username,
            "amount_owed": float(share.amount_owed),
            "vote_status": share.vote_status.value,
            "is_paid": share.is_paid,
        })

    # Check if there are any outstanding balances
    has_outstanding = any(
        h["owed_by_me"] > 0.01 or h["owed_to_me"] > 0.01 for h in households_data
    )
    
    response = {
        "households": households_data,
        "shares": shares_data,
    }
    
    # Add message if no outstanding balances
    if not has_outstanding:
        response["detail"] = "No outstanding balances"

    return response
