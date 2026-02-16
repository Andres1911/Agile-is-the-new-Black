# Expenses API — placeholder
# Will be re-implemented with ExpenseShare / splitting / voting logic.
from fastapi import APIRouter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.models import *
from app.db.database import get_db
from app.api.auth import get_current_user
from app.schemas.schemas import ExpenseCreate

router = APIRouter()


@router.post("/create-and-split", status_code=201)
def create_and_split(
    expense_in: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    # --- 2. 身份校验：查找用户当前所在的有效家庭 ---
    membership = db.query(HouseholdMember).filter(
        HouseholdMember.user_id == current_user.id,
        HouseholdMember.left_at == None
    ).first()

    if not membership:
        raise HTTPException(
            status_code=400, 
            detail="User is not currently in any household"
        )
    
    roommates = db.query(HouseholdMember).filter(
        HouseholdMember.household_id == membership.household_id,
        HouseholdMember.user_id != current_user.id,
        HouseholdMember.left_at == None
    ).all()

    if not expense_in.include_creator:
        if not roommates:
            raise HTTPException(
                status_code=400, 
                detail="No other active members in the household to split with"
            )
    
    # --- 1. 基础校验：金额 ---
    if expense_in.amount <= 0:
        raise HTTPException(
            status_code=400, 
            detail="Cannot create expense: Amount must be greater than zero"
        )


    # --- 3. 初始化账单对象 ---
    new_expense = Expense(
        description=expense_in.description,
        amount=expense_in.amount,
        category=expense_in.category,
        creator_id=current_user.id,
        household_id=membership.household_id
    )

    # --- 4. 分摊逻辑处理 ---
    if expense_in.split_evenly:
        # A. 平均分逻辑
        split_members = []
        if expense_in.include_creator:
            split_members.append(current_user.id) # 包含自己
        
        for m in roommates:
            split_members.append(m.user_id)

        num = len(split_members)
        base_share = round(expense_in.amount / num, 2)
        sum_of_others = base_share * (num - 1)
        last_share = round(expense_in.amount - sum_of_others, 2)

        for i, user_id in enumerate(split_members):
            amt = base_share if i < (num - 1) else last_share
            
            is_creator = (user_id == current_user.id)
            status = VoteStatus.ACCEPTED if is_creator else VoteStatus.PENDING
            
            new_expense.shares.append(
                ExpenseShare(
                    user_id=user_id, 
                    amount_owed=amt,
                    vote_status=status  # 设置初始状态
                )
            )
    
    else:
        # B. 手动分摊逻辑：完全以列表为准
        if not expense_in.manual_shares:
            raise HTTPException(
                status_code=400, 
                detail="Manual shares list cannot be empty when split_evenly is False"
            )
        
        # 这里的 valid_ids 包含所有当前家庭成员 (已经在前面查好了)
        valid_ids = {m.user_id for m in roommates}
        valid_ids.add(current_user.id)

        total_manual = 0
        # 这里不再检查 has_creator_in_list 与 include_creator 的冲突
        for s in expense_in.manual_shares:
            # 1. 校验成员身份
            if s.user_id not in valid_ids:
                raise HTTPException(
                    status_code=400, 
                    detail=f"User {s.user_id} is not an active member of this household"
                )
            
            # 2. 校验单笔分摊金额
            if s.amount <= 0:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Share for user {s.user_id} must be greater than zero"
                )

            total_manual += s.amount
            
            is_creator = (s.user_id == current_user.id)
            status = VoteStatus.ACCEPTED if is_creator else VoteStatus.PENDING

            new_expense.shares.append(
                ExpenseShare(
                    user_id=s.user_id, 
                    amount_owed=s.amount,
                    vote_status=status  # 设置初始状态
                )
            )

        if abs(total_manual - expense_in.amount) > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot create expense: Split amounts {total_manual:.2f} CAD do not equal expense total {expense_in.amount:.2f} CAD"
            )

    # --- 5. 数据库提交 ---
    try:
        db.add(new_expense)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error during creation")

    return {"detail": "success"}