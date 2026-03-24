from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.invite_codes import generate_unique_invite_code
from app.db.database import get_db
from app.models.models import Expense, ExpenseShare, Household, HouseholdMember, VoteStatus
from app.models.models import User as UserModel
from app.schemas.schemas import Expense as ExpenseSchema
from app.schemas.schemas import Household as HouseholdSchema
from app.schemas.schemas import HouseholdCreate, HouseholdMemberWithUser


class HouseholdJoin(BaseModel):
    household_name: str
    invite_code: str


router = APIRouter()


# This is a helper method, currently only used by the frontend to get the list of active household members for the current user, but could be useful for other purposes in the future as well
@router.get("/me/active-household-members")
def get_current_user_active_household_members(
    db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)
):
    # Find which household the current user is active in
    membership = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.user_id == current_user.id, HouseholdMember.left_at.is_(None))
        .first()
    )

    if not membership:
        raise HTTPException(status_code=404, detail="No active household found")

    # Fetch all users in that household
    users = (
        db.query(UserModel)
        .join(HouseholdMember, HouseholdMember.user_id == UserModel.id)
        .filter(
            HouseholdMember.household_id == membership.household_id,
            HouseholdMember.left_at.is_(None),
        )
        .all()
    )

    return {
        "household_id": membership.household_id,
        "current_user_id": current_user.id,
        "current_user_is_admin": membership.is_admin,
        "members": [
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "is_admin": any(
                    hm.user_id == u.id and hm.household_id == membership.household_id and hm.left_at is None and hm.is_admin
                    for hm in u.household_memberships
                ),
            }
            for user in users
        ],
    }


@router.get("/me", response_model=HouseholdSchema)
def get_my_household(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Return the current user's active household."""
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

    household = db.query(Household).filter(Household.id == membership.household_id).first()
    if household is None:
        # Handle potential orphaned membership where the household has been deleted
        raise HTTPException(status_code=404, detail="Household not found")
    return household


@router.post("/", response_model=HouseholdSchema, status_code=status.HTTP_201_CREATED)
def create_household(
    household_in: HouseholdCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Create a Household

    Rules:
    - User that creates the household is automatically set as the admin of this household
    - Have to make sure that household name doesnt previously exist
    - User that creates a new household should not be currently registered in a household
    """

    # Check for duplicate name
    existing_hh = db.query(Household).filter(Household.name == household_in.name).first()
    if existing_hh:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name already exists")

    # Check if user is already an active member elsewhere
    active_membership = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.user_id == current_user.id, HouseholdMember.left_at.is_(None))
        .first()
    )

    if active_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already registered as living in another household",
        )

    # Create the Household
    invite_code = generate_unique_invite_code(db)
    new_household = Household(
        name=household_in.name,
        description=household_in.description,
        address=household_in.address,
        invite_code=invite_code,
    )
    db.add(new_household)
    db.flush()

    # Create the Admin Binding
    new_member = HouseholdMember(
        user_id=current_user.id, household_id=new_household.id, is_admin=True
    )
    db.add(new_member)

    db.commit()
    db.refresh(new_household)

    return new_household


@router.get("/{household_id}/members", response_model=list[HouseholdMemberWithUser])
def get_household_members(
    household_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Return the list of members for a household.

    Rules:
    - The household must exist.
    - The requesting user must be an active member of that household.
    """
    # Check household exists
    household = db.query(Household).filter(Household.id == household_id).first()
    if household is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household not found",
        )

    # Check requesting user is a member
    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == current_user.id,
            HouseholdMember.left_at.is_(None),
        )
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this household",
        )

    # Return all active members of the household
    members = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.left_at.is_(None),
        )
        .all()
    )
    return members


@router.get("/{household_id}/expenses", response_model=list[ExpenseSchema])
def get_household_expense_history(
    household_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Return the history of expenses for a household.

    Rules:
    - The household must exist.
    - The requesting user must be an active member of that household.
    - Return list sorted by date (newest first).
    """
    # Check household exists
    household = db.query(Household).filter(Household.id == household_id).first()
    if household is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household not found",
        )

    # check requesting user is an active member
    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == current_user.id,
            HouseholdMember.left_at.is_(None),
        )
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this household",
        )

    # Return all expenses for the household
    # .order_by(Expense.date.desc()) ensures the history view shows recent items first
    expenses = (
        db.query(Expense)
        .filter(Expense.household_id == household_id)
        .order_by(Expense.date.desc())
        .all()
    )

    return expenses


@router.post("/join")
def join_household(
    join_in: HouseholdJoin,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Join a household using an invite code.


    Rules:
    - The household must exist by name.
    - The invite code must match the household's code.
    - The user must not already be an active member of any household.
    """
    # 1. Look up the household by name
    household = db.query(Household).filter(Household.name == join_in.household_name).first()
    if not household:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household not found",
        )

    # 2. Verify invite code
    if household.invite_code != join_in.invite_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invite code",
        )

    # 3. Check if user is already in a household (left_at is None)
    active_membership = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.user_id == current_user.id, HouseholdMember.left_at.is_(None))
        .first()
    )
    if active_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already registered as living in another household",
        )

    # 4. Create new membership binding
    # (By default, left_at is None and is_admin is False)
    new_member = HouseholdMember(user_id=current_user.id, household_id=household.id, is_admin=False)
    db.add(new_member)
    db.commit()

    return {"message": "Success"}


@router.post("/{household_name}/debts/simplify")
def simplify_household_debts(
    household_name: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Simplify inter-member debts by:
    1. Calculating net balances between members
    2. Identifying and removing circular debts
    3. Identifying and simplifying linear chains

    Returns the list of debts that were simplified and remaining debts.
    """
    # 1. Verify user is a member of the household
    household = db.query(Household).filter(Household.name == household_name).first()
    if not household:
        raise HTTPException(status_code=404, detail="Household not found")

    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == current_user.id,
            HouseholdMember.household_id == household.id,
            HouseholdMember.left_at.is_(None),
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: Only household members can simplify debts",
        )

    # 2. Get all unpaid, accepted shares (debts) in this household
    shares = (
        db.query(ExpenseShare, Expense, UserModel)
        .join(Expense, ExpenseShare.expense_id == Expense.id)
        .join(UserModel, ExpenseShare.user_id == UserModel.id)
        .filter(
            Expense.household_id == household.id,
            ExpenseShare.vote_status == VoteStatus.ACCEPTED,
            ExpenseShare.is_paid.is_(False),
        )
        .all()
    )

    if not shares:
        return {
            "message": "No outstanding debts to simplify",
            "simplified": [],
            "remaining": [],
        }

    # 3. Build net balance graph: {(debtor_id, creditor_id): amount}
    # Start by calculating gross debts
    gross_debts = {}
    debt_to_share = {}  # Track which share corresponds to each debt for later

    for share, expense, _ in shares:
        debtor_id = share.user_id
        creditor_id = expense.creator_id
        amount = float(share.amount_owed)

        key = (debtor_id, creditor_id)
        if key not in gross_debts:
            gross_debts[key] = 0
            debt_to_share[key] = []

        gross_debts[key] += amount
        debt_to_share[key].append(share)

    # 4. Calculate net debts by offsetting
    # For each pair of users, calculate net flow
    all_users = set()
    for debtor_id, creditor_id in gross_debts:
        all_users.add(debtor_id)
        all_users.add(creditor_id)

    net_debts = {}
    for (debtor_id, creditor_id), amount in gross_debts.items():
        reverse_key = (creditor_id, debtor_id)

        if reverse_key in gross_debts:
            # Both directions exist - net them out
            reverse_amount = gross_debts[reverse_key]
            if amount > reverse_amount:
                net_debts[(debtor_id, creditor_id)] = amount - reverse_amount
            elif reverse_amount > amount:
                net_debts[(creditor_id, debtor_id)] = reverse_amount - amount
            # If equal, they cancel out - no entry needed
        else:
            # Only one direction - include it
            net_debts[(debtor_id, creditor_id)] = amount

    # 5. Simplify circular debts and track which debts are simplified away
    simplified_debts = []
    offset_total = 0.0
    remaining_debts = dict(net_debts)
    debts_fully_simplified = set()  # Track which gross debts were completely removed

    # Record the original amounts before simplification
    original_remaining = dict(remaining_debts)

    # Find circular debts of form A->B->C->A and reduce them
    # Use a simpler approach: repeatedly find and remove cycles
    def find_and_remove_one_cycle():
        """Find one cycle in remaining debts and reduce it. Return True if a cycle was found."""
        nonlocal offset_total, remaining_debts, simplified_debts
        # Build adjacency for DFS
        adj = {}
        for debtor, creditor in remaining_debts:
            if debtor not in adj:
                adj[debtor] = []
            adj[debtor].append(creditor)

        # Try to find a cycle using DFS from each node
        def find_cycle_from(start):
            """Use DFS to find a cycle starting from 'start'."""
            stack = [(start, [start])]  # (current_node, path)

            while stack:
                node, path = stack.pop()

                if node in adj:
                    for neighbor in adj[node]:
                        if neighbor == start and len(path) > 1:
                            # Found a cycle!
                            return [*path, start]
                        elif neighbor not in path:
                            stack.append((neighbor, [*path, neighbor]))

            return None

        # Try to find a cycle from each node
        for start_node in adj:
            cycle = find_cycle_from(start_node)
            if cycle:
                # Found a cycle [A, B, C, A, ...]
                # Remove the duplicate last element
                cycle = cycle[:-1]

                # Calculate minimum amount in this cycle
                min_amount = float("inf")
                for i in range(len(cycle)):
                    u1 = cycle[i]
                    u2 = cycle[(i + 1) % len(cycle)]
                    if (u1, u2) in remaining_debts:
                        min_amount = min(min_amount, remaining_debts[(u1, u2)])

                if min_amount > 0:
                    # Reduce all edges in the cycle by min_amount
                    for i in range(len(cycle)):
                        u1 = cycle[i]
                        u2 = cycle[(i + 1) % len(cycle)]
                        key = (u1, u2)

                        remaining_debts[key] -= min_amount
                        if remaining_debts[key] <= 0.001:
                            del remaining_debts[key]

                        simplified_debts.append(
                            {
                                "debtor_id": u1,
                                "creditor_id": u2,
                                "amount": min_amount,
                            }
                        )

                    offset_total += min_amount
                    return True

        return False

    # Keep finding and removing cycles until none remain
    while find_and_remove_one_cycle():
        pass

    # 5b. Simplify linear chains (A→B→C can become A→C)
    # Find chains where A owes B and B owes C the same amount
    chain_changed = True
    while chain_changed:
        chain_changed = False
        debts_to_remove = []
        debts_to_add = {}

        # For each debt A→B
        for (a, b), amount_ab in list(remaining_debts.items()):
            # Check if B has an outgoing debt to C with the same amount
            for (b2, c), amount_bc in remaining_debts.items():
                if b == b2 and abs(amount_ab - amount_bc) < 0.001:
                    # Found a chain: A→B→C with same amount
                    # Create direct debt A→C
                    direct_key = (a, c)

                    if direct_key not in remaining_debts and direct_key not in debts_to_add:
                        # Mark intermediate debts for removal
                        debts_to_remove.append((a, b))
                        debts_to_remove.append((b, c))

                        # Add direct debt
                        debts_to_add[direct_key] = amount_ab
                        chain_changed = True

        # Apply the changes
        for key in debts_to_remove:
            if key in remaining_debts:
                del remaining_debts[key]
                # Track this as a simplified debt
                debts_fully_simplified.add(key)

        for key, amount in debts_to_add.items():
            remaining_debts[key] = amount
            # Record this as a new debt created by simplification
            debtor_id, creditor_id = key
            simplified_debts.append(
                {
                    "debtor_id": debtor_id,
                    "creditor_id": creditor_id,
                    "amount": amount,
                }
            )

    # Now determine which debts were fully simplified by comparing original vs remaining
    for debt_key in original_remaining:
        if debt_key not in remaining_debts:
            # This debt was completely removed
            debts_fully_simplified.add(debt_key)

    # 6. Update the database: mark shares as paid and update amounts as needed
    # For each debt, check if its amount changed
    debt_changes = {}  # {(debtor_id, creditor_id): (original_amount, remaining_amount)}

    for debt_key, original_amount in original_remaining.items():
        remaining_amount = remaining_debts.get(debt_key, 0)
        if remaining_amount != original_amount:
            debt_changes[debt_key] = (original_amount, remaining_amount)

    # For each debt that changed, mark old shares as paid and create new ones if needed
    for debt_key, (_original_amount, remaining_amount) in debt_changes.items():
        debtor_id, creditor_id = debt_key

        # Find all shares for this debt and mark them as paid
        shares_to_mark = (
            db.query(ExpenseShare)
            .join(Expense, Expense.id == ExpenseShare.expense_id)
            .filter(
                Expense.household_id == household.id,
                Expense.creator_id == creditor_id,
                ExpenseShare.user_id == debtor_id,
                ExpenseShare.is_paid.is_(False),
            )
            .all()
        )
        for share in shares_to_mark:
            share.is_paid = True
            share.paid_amount = share.amount_owed

        # If there's a remaining amount, create a new share for it
        if remaining_amount > 0.001:
            payer = db.query(UserModel).filter(UserModel.id == debtor_id).first()
            payee = db.query(UserModel).filter(UserModel.id == creditor_id).first()

            new_expense = Expense(
                household_id=household.id,
                creator_id=creditor_id,
                amount=remaining_amount,
                description=f"Simplified debt: {payer.username} → {payee.username}",
            )
            db.add(new_expense)
            db.flush()

            new_share = ExpenseShare(
                expense_id=new_expense.id,
                user_id=debtor_id,
                amount_owed=remaining_amount,
                paid_amount=0,
                is_paid=False,
                vote_status=VoteStatus.ACCEPTED,
            )
            db.add(new_share)

    # Handle any remaining debts that are new (created by chain simplification)
    for (debtor_id, creditor_id), amount in remaining_debts.items():
        if (debtor_id, creditor_id) not in original_remaining:
            # This is a new debt created by simplification (e.g., chain reduction)
            payer = db.query(UserModel).filter(UserModel.id == debtor_id).first()
            payee = db.query(UserModel).filter(UserModel.id == creditor_id).first()

            new_expense = Expense(
                household_id=household.id,
                creator_id=creditor_id,
                amount=amount,
                description=f"Simplified debt: {payer.username} → {payee.username}",
            )
            db.add(new_expense)
            db.flush()

            new_share = ExpenseShare(
                expense_id=new_expense.id,
                user_id=debtor_id,
                amount_owed=amount,
                paid_amount=0,
                is_paid=False,
                vote_status=VoteStatus.ACCEPTED,
            )
            db.add(new_share)

    db.commit()

    # Determine message
    if offset_total > 0 and not remaining_debts:
        message = "All circular debts have been simplified"
    elif offset_total > 0:
        message = "Household debts simplified successfully"
    elif simplified_debts:
        message = "Debts simplified to minimize transactions"
    else:
        message = "No simplifications available"

    return {
        "message": message,
        "offset_amount": offset_total,
        "simplifications_applied": len(simplified_debts),
        "simplified": simplified_debts,
        "remaining": [
            {
                "debtor_id": debtor_id,
                "creditor_id": creditor_id,
                "amount": amount,
            }
            for (debtor_id, creditor_id), amount in remaining_debts.items()
        ],
    }
