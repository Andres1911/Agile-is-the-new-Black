import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from app.models.models import User, Household, HouseholdMember, Expense, ExpenseStatus, ExpenseShare, VoteStatus

# --- 显式从 conftest 导入助手函数 ---
# 这样你就不用在每个 step 函数的参数列表里写这些名字了
from ..conftest import register as register_user
from ..conftest import auth_header as get_auth_header
from ..conftest import create_expense as api_create_expense

# 1. 绑定 Feature 文件
scenarios("features/ID007_Create_Split_Expense.feature")

@pytest.fixture()
def context():
    """共享上下文"""
    return {
        "manual_shares": [],
        "include_creator": True,
        "split_evenly": True
    }

# ── 辅助函数 ──────────────────────────────────────────────────────────────

def get_table_dicts(datatable):
    """将列表格式的表格转换为字典列表"""
    keys = datatable[0]
    return [dict(zip(keys, row)) for row in datatable[1:]]

# ── GIVEN steps ───────────────────────────────────────────────────────────

@given(parsers.parse('household "{household_name}" exists with members'))
def given_household_with_members(client, db, household_name):
    # 注意：这里去掉了参数里的 register，直接使用导入的函数
    names = ["Alice", "Bob", "Cara"]
    user_objects = []

    for name in names:
        # 直接调用导入的助手函数
        register_user(
            client, 
            email=f"{name.lower()}@test.com", 
            username=name, 
            password="Password123!", 
            full_name=name
        )
        user = db.query(User).filter(User.username == name).first()
        user_objects.append(user)

    alice, bob, cara = user_objects

    new_household = Household(
        name=household_name,
        invite_code="MAPLE123",
        description="Test Household"
    )
    db.add(new_household)
    db.flush() 

    db.add(HouseholdMember(user_id=alice.id, household_id=new_household.id, is_admin=True))
    db.add(HouseholdMember(user_id=bob.id, household_id=new_household.id, is_admin=False))
    db.add(HouseholdMember(user_id=cara.id, household_id=new_household.id, is_admin=False))
    db.commit()

@given(parsers.parse('user "{username}" is authenticated as a household member'), target_fixture="context")
def given_user_authenticated(client, username, context):
    # 直接调用导入的助手函数获取 Header
    context["auth_headers"] = get_auth_header(client, username=username, password="Password123!")
    context["current_user"] = username
    return context

# ── WHEN steps ────────────────────────────────────────────────────────────

@when(parsers.parse('"{username}" specifies an expense with the following details'), target_fixture="context")
def when_set_expense_base_details(username, datatable, context):
    # 获取表格的第一行
    data = get_table_dicts(datatable)[0]
    
    # 必填项
    context["description"] = data["description"]
    context["amount"] = float(data["amountCAD"])
    
    # 可选项：如果表格里没这一列，或者值为空字符串，则设为 None (数据库里的 NULL)
    category_val = data.get("category")
    context["category"] = category_val if category_val else None
    
    return context

@when(parsers.parse('"{username}" creates and splits the expense among the following members'), target_fixture="context")
def when_split_manual(client, db, username, datatable, context):
    # 去掉了参数里的 create_expense
    context["split_evenly"] = False
    context["manual_shares"] = []
    
    users = db.query(User).all()
    name_to_id = {u.username: u.id for u in users}
    
    table_rows = get_table_dicts(datatable)
    for row in table_rows:
        payer_name = row["payer"]
        if payer_name in name_to_id:
            context["manual_shares"].append({
                "user_id": name_to_id[payer_name],
                "amount": float(row["shareCAD"])
            })
            
    include_creator = any(share["user_id"] == name_to_id[username] for share in context["manual_shares"])
    context["include_creator"] = include_creator

    payload = {
        "description": context.get("description"),
        "amount": context.get("amount"),
        "category": context.get("category"),
        "split_evenly": context["split_evenly"],
        "include_creator": context.get("include_creator"),
        "manual_shares": context["manual_shares"]
    }
    
    # 直接使用导入的 API 助手
    context["response"] = api_create_expense(client, context["auth_headers"], payload)
    return context

@when(parsers.parse('"{username}" creates and splits the expense equally with include_self="{is_inclusive}"'), target_fixture="context")
def when_split_equally(client, username, is_inclusive, context):
    """
    Handles equal split by sending the boolean flags to the backend.
    No manual calculation or manual_shares list required.
    """
    # 1. Parse the boolean from the string parameter
    include_creator = is_inclusive.lower() == "true"
    
    # 2. Update context for later validation if needed
    context["split_evenly"] = True
    context["include_creator"] = include_creator

    # 3. Assemble the minimal payload for equal split
    payload = {
        "description": context.get("description"),
        "amount": context.get("amount"),
        "category": context.get("category"),
        "split_evenly": True,
        "include_creator": include_creator
        # No manual_shares sent here as the backend handles the logic
    }

    # 4. Use the helper from conftest to hit the endpoint
    context["response"] = api_create_expense(client, context["auth_headers"], payload)
    
    return context

@when(parsers.parse('"{username}" assigns the expense only to herself'), target_fixture="context")
def when_assign_to_self(client, username, context):
    context["split_evenly"] = True
    context["include_creator"] = True
    payload = {
        "description": context["description"],
        "amount": context["amount"],
        "category": "Personal",
        "split_evenly": context["split_evenly"],
        "include_creator": context["include_creator"],
        "manual_shares": []
    }
    context["response"] = api_create_expense(client, context["auth_headers"], payload)
    return context

# ── THEN steps ────────────────────────────────────────────────────────────

@then(parsers.parse('the system records an expense for "{username}" in "{h_name}" with amount "{amount}", description "{desc}", category "{cat}", and status "{status}"'))
def then_verify_full_expense_attributes(db, context, username, h_name, amount, desc, cat, status):
    # 1. 基础响应检查
    assert context["response"].status_code == 201
    assert context["response"].json().get("detail") == "success"

    # 2. 准备对比数据
    user = db.query(User).filter(User.username == username).first()
    household = db.query(Household).filter(Household.name == h_name).first()

    # 3. 从数据库抓取记录
    expense = db.query(Expense).filter(
        Expense.creator_id == user.id,
        Expense.household_id == household.id
    ).order_by(Expense.id.desc()).first()

    assert expense is not None, "Expense record not found in database"

    # --- 开始全属性校验 ---

    # A. 金额校验
    assert abs(expense.amount - float(amount)) == 0

    # B. 描述校验
    assert expense.description == desc

    # C. 分类校验 (重点：处理 None)
    # 如果 Gherkin 里写的是 "None"，则预期数据库里是 None (NULL)
    expected_category = None if cat == "None" else cat
    assert expense.category == expected_category, f"Expected category {expected_category}, but got {expense.category}"

    # D. 状态校验
    expected_status = ExpenseStatus[status.upper()]
    assert expense.status == expected_status

    # 存入上下文供后续 ExpenseShare 校验使用
    context["last_expense"] = expense

@then('the expense has the following expense shares')
def then_verify_expense_shares_all_attributes(db, context, datatable):
    # 1. Ensure the parent Expense object exists in the test context
    expense = context.get("last_expense")
    assert expense is not None, "Expense object not found in context. Check if the previous creation step succeeded."

    # 2. Convert Gherkin DataTable to a list of dictionaries
    expected_shares = get_table_dicts(datatable)

    # 3. Query all split records associated with this expense from the database
    actual_shares = db.query(ExpenseShare).filter(
        ExpenseShare.expense_id == expense.id
    ).all()

    # 4. Verify the count of shares
    assert len(actual_shares) == len(expected_shares), \
        f"Share count mismatch: Expected {len(expected_shares)}, but found {len(actual_shares)} in database."

    # 5. Iterate through the table and verify every database attribute
    for expected in expected_shares:
        # A. Retrieve user object to verify user_id (foreign key)
        user = db.query(User).filter(User.username == expected["user"]).first()
        assert user is not None, f"Test data error: User '{expected['user']}' does not exist in the database."

        # B. Match the corresponding ExpenseShare record from the actual results
        actual = next((s for s in actual_shares if s.user_id == user.id), None)
        assert actual is not None, f"No ExpenseShare record found for user: {user.username}."

        # --- Comprehensive Attributes Validation ---

        # Verify expense_id (Foreign Key linkage)
        assert actual.expense_id == expense.id, f"Linkage error: expense_id mismatch for {user.username}."

        # Verify amount_owed (Float comparison with tolerance)
        expected_owed = float(expected["amount_owed"])
        assert abs(actual.amount_owed - expected_owed) == 0, \
            f"amount_owed mismatch for {user.username}: Expected {expected_owed}, got {actual.amount_owed}."

        # Verify paid_amount (Float comparison with tolerance)
        expected_paid = float(expected["paid_amount"])
        assert abs(actual.paid_amount - expected_paid) == 0, \
            f"paid_amount mismatch for {user.username}: Expected {expected_paid}, got {actual.paid_amount}."

        # Verify is_paid (Boolean conversion)
        expected_is_paid = expected["is_paid"].strip().lower() == "true"
        assert actual.is_paid == expected_is_paid, \
            f"is_paid status mismatch for {user.username}: Expected {expected_is_paid}, got {actual.is_paid}."

        # Verify vote_status (Enum mapping)
        try:
            expected_vote = VoteStatus[expected["vote_status"].upper()]
        except KeyError:
            pytest.fail(f"Invalid VoteStatus provided in Feature file: {expected['vote_status']}")
        
        assert actual.vote_status == expected_vote, \
            f"vote_status mismatch for {user.username}: Expected {expected_vote}, got {actual.vote_status}."

    print(f"Successfully verified all attributes for {len(actual_shares)} ExpenseShare records.")

@then(parsers.parse('the system rejects the expense creation'))
def then_check_rejection(context):
    assert context["response"].status_code == 400

@then(parsers.parse('the system displays error message "{error_msg}"'))
def then_check_error_message(context, error_msg):
    detail = context["response"].json()["detail"]
    assert error_msg.lower() in detail.lower()