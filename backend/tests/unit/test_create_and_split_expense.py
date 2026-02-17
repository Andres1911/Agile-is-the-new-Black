from datetime import UTC, datetime

from app.models.models import Expense, ExpenseShare, Household, HouseholdMember, VoteStatus
from app.models.models import User as UserModel

from ..conftest import TestingSessionLocal, login, register


class TestExpenseMembershipEdgeCases:
    def test_user_not_in_any_household_fails(self, client):
        """
        模仿你提供的代码风格：
        1. 注册并登录一个真实用户。
        2. 确保数据库中没有任何该用户的 HouseholdMember 记录。
        3. 调用 API 并断言 400。
        """
        # 1. 准备用户并获取 Token
        register(client, username="lonely_alice", email="alice@edge.com")
        auth_resp = login(client, username="lonely_alice")
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. DB check: ensure no household membership
        db = TestingSessionLocal()
        user = db.query(UserModel).filter(UserModel.username == "lonely_alice").first()
        # Remove any existing household links for clean state
        db.query(HouseholdMember).filter(HouseholdMember.user_id == user.id).delete()
        db.commit()
        db.close()

        # 3. 发送请求
        payload = {
            "description": "Solo Expense",
            "amount": 100.0,
            "category": "Grocery",
            "split_evenly": True,
            "include_creator": True,
        }
        resp = client.post("/api/v1/expenses/create-and-split", json=payload, headers=headers)

        # 4. 断 assertions
        assert resp.status_code == 400
        assert "not currently in any household" in resp.json()["detail"].lower()


class TestExpenseRoommateEdgeCases:
    def test_no_roommates_and_not_including_self_fails(self, client):
        """
        测试场景：Alice 在家庭里，但她是唯一成员。
        她试图创建一个不包含自己的分摊账单（include_creator=False）。
        预期结果：400 错误，提示没有其他成员可分摊。
        """
        # 1. 注册并登录用户
        register(client, username="solo_alice", email="alice_solo@test.com")
        auth_resp = login(client, username="solo_alice")
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. DB state: household with only Alice
        db = TestingSessionLocal()
        user = db.query(UserModel).filter(UserModel.username == "solo_alice").first()

        new_household = Household(name="Solo Home", invite_code="SOLO123")
        db.add(new_household)
        db.flush()

        # 只有 Alice 一个人
        db.add(HouseholdMember(user_id=user.id, household_id=new_household.id, is_admin=True))
        db.commit()
        db.close()

        # 3. Request without self (include_creator=False)
        payload = {
            "description": "Ghost Party",
            "amount": 50.0,
            "category": "Entertainment",
            "split_evenly": True,
            "include_creator": False,  # key: no self, no other members
        }
        resp = client.post("/api/v1/expenses/create-and-split", json=payload, headers=headers)

        # 4. 断言结果
        assert resp.status_code == 400
        assert "no other active members" in resp.json()["detail"].lower()

    def test_roommate_left_treated_as_no_roommates(self, client):
        """
        测试场景：Alice 曾有室友 Bob，但 Bob 已经搬走了 (left_at is not None)。
        预期结果：依然应该报 400。
        """
        register(client, username="alice_alone", email="alone@test.com")
        register(client, username="bob_gone", email="gone@test.com")
        auth_resp = login(client, username="alice_alone")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        db = TestingSessionLocal()
        alice = db.query(UserModel).filter(UserModel.username == "alice_alone").first()
        bob = db.query(UserModel).filter(UserModel.username == "bob_gone").first()

        h = Household(name="Empty Home", invite_code="EMPTY1")
        db.add(h)
        db.flush()

        db.add(HouseholdMember(user_id=alice.id, household_id=h.id))
        # Bob 搬走了
        db.add(HouseholdMember(user_id=bob.id, household_id=h.id, left_at=datetime.now(UTC)))
        db.commit()
        db.close()

        payload = {
            "description": "Past memories",
            "amount": 10.0,
            "split_evenly": True,
            "include_creator": False,
            "category": "Photo",
        }
        resp = client.post("/api/v1/expenses/create-and-split", json=payload, headers=headers)

        assert resp.status_code == 400
        assert "no other active members" in resp.json()["detail"].lower()


class TestExpenseSplitIncludingCreator:
    def test_equal_split_five_members_with_precision(self, client):
        """
        场景：5 人平分 100.01 元。
        """
        # 1. 注册并登录 5 个用户
        member_names = ["Alice", "Bob", "Cara", "David", "Eve"]
        for name in member_names:
            register(client, username=name, email=f"{name.lower()}@test.com")

        # 必须在这里定义 headers
        auth_resp = login(client, username="Alice")
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. 建立 5 人家庭环境
        db = TestingSessionLocal()
        users = {
            u.username: u
            for u in db.query(UserModel).filter(UserModel.username.in_(member_names)).all()
        }

        h = Household(name="Precision Home", invite_code="PREC123")
        db.add(h)
        db.flush()

        for name in member_names:
            db.add(HouseholdMember(user_id=users[name].id, household_id=h.id))
        db.commit()

        # 3. 发送请求
        total_amount = 100.01
        payload = {
            "description": "Precision Test",
            "amount": total_amount,
            "category": "Test",
            "split_evenly": True,
            "include_creator": True,
        }

        resp = client.post("/api/v1/expenses/create-and-split", json=payload, headers=headers)
        assert resp.status_code == 201

        # 4. 数据库深度验证
        # 开启新 session 确保看到 commit 后的数据
        db_check = TestingSessionLocal()
        expense = db_check.query(Expense).filter(Expense.description == "Precision Test").first()
        actual_shares = (
            db_check.query(ExpenseShare).filter(ExpenseShare.expense_id == expense.id).all()
        )

        assert len(actual_shares) == 5

        # Verify total (float tolerance)
        total_calculated = sum(s.amount_owed for s in actual_shares)
        assert abs(total_calculated - total_amount) == 0

        for actual in actual_shares:
            assert actual.expense_id == expense.id

            # 使用 db_check 获取关联的用户名进行断言
            user = db_check.get(UserModel, actual.user_id)

            if user.username == "Alice":
                assert actual.vote_status == VoteStatus.ACCEPTED
            else:
                assert actual.vote_status == VoteStatus.PENDING

            # Amount should be 20.00 or 20.01 (remainder handling)
            assert actual.amount_owed in [20.00, 20.01], (
                f"Wrong amount {actual.amount_owed} for {user.username}"
            )

        db_check.close()


class TestManualSplitEdgeCases:
    def test_manual_split_with_non_household_member_fails(self, client):
        """
        场景：Alice (家庭 A) 试图分摊账单给 Stranger (不在家庭 A)。
        预期：400 错误，提示用户不是该家庭的活跃成员。
        """
        # 1. 注册 Alice 和一个陌生人
        register(client, username="alice_h", email="alice_h@test.com")
        register(client, username="stranger", email="stranger@test.com")

        auth_resp = login(client, username="alice_h")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        db = TestingSessionLocal()
        alice = db.query(UserModel).filter(UserModel.username == "alice_h").first()
        stranger = db.query(UserModel).filter(UserModel.username == "stranger").first()

        # 2. 只把 Alice 加入家庭
        h = Household(name="Alice's Home", invite_code="ALICE99")
        db.add(h)
        db.flush()
        db.add(HouseholdMember(user_id=alice.id, household_id=h.id))
        db.commit()

        # 3. Request: assign share to stranger.id
        payload = {
            "description": "Hack test",
            "amount": 100.0,
            "category": "Test",
            "split_evenly": False,  # 手动分摊
            "include_creator": True,
            "manual_shares": [
                {"user_id": alice.id, "amount": 50.0},
                {"user_id": stranger.id, "amount": 50.0},  # 这人不在家里
            ],
        }
        resp = client.post("/api/v1/expenses/create-and-split", json=payload, headers=headers)

        # 4. 断言
        assert resp.status_code == 400
        assert f"User {stranger.id} is not an active member" in resp.json()["detail"]
        db.close()

    def test_manual_split_with_zero_amount_share_fails(self, client):
        """
        场景：Alice 给 Bob 分摊了 0 元或负数。
        预期：400 错误，提示分摊金额必须大于零。
        """
        # 1. 注册 Alice 和 Bob
        register(client, username="alice_z", email="alice_z@test.com")
        register(client, username="bob_z", email="bob_z@test.com")

        auth_resp = login(client, username="alice_z")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        db = TestingSessionLocal()
        alice = db.query(UserModel).filter(UserModel.username == "alice_z").first()
        bob = db.query(UserModel).filter(UserModel.username == "bob_z").first()

        h = Household(name="Zero Home", invite_code="ZERO1")
        db.add(h)
        db.flush()
        db.add(HouseholdMember(user_id=alice.id, household_id=h.id))
        db.add(HouseholdMember(user_id=bob.id, household_id=h.id))
        db.commit()

        # 2. Request: assign Bob 0 amount
        payload = {
            "description": "Zero split test",
            "amount": 100.0,
            "category": "Test",
            "split_evenly": False,
            "include_creator": True,
            "manual_shares": [
                {"user_id": alice.id, "amount": 100.0},
                {"user_id": bob.id, "amount": 0.0},  # zero amount, invalid
            ],
        }
        resp = client.post("/api/v1/expenses/create-and-split", json=payload, headers=headers)

        # 3. 断言
        assert resp.status_code == 400
        assert f"Share for user {bob.id} must be greater than zero" in resp.json()["detail"]
        db.close()
