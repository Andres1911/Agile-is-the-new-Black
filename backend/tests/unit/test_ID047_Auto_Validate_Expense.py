# tests/unit/test_auto_validate_expense.py

from unittest.mock import MagicMock

from app.api.expenses import compute_expense_status
from app.models.models import ExpenseShare, ExpenseStatus, VoteStatus


def make_share(vote_status: VoteStatus) -> ExpenseShare:
    share = MagicMock(spec=ExpenseShare)
    share.vote_status = vote_status
    return share


class TestAutoValidateExpense:
    def test_ID047_expense_finalized_with_majority_acceptance(self):
        """Strictly more than 50% accepted → FINALIZED."""
        shares = [
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.REJECTED),
        ]
        assert compute_expense_status(shares) == ExpenseStatus.FINALIZED

    def test_ID047_expense_remains_disputed_when_exactly_50_percent_household_members_accepted(
        self,
    ):
        """Exactly 50% accepted → not FINALIZED (stays DISPUTED due to rejection)."""
        shares = [
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.REJECTED),
        ]
        assert compute_expense_status(shares) == ExpenseStatus.DISPUTED

    def test_ID047_expense_remains_disputed_when_less_than_50_percent_household_members_accepted(
        self,
    ):
        """Less than 50% accepted with rejections → DISPUTED."""
        shares = [
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.REJECTED),
            make_share(VoteStatus.REJECTED),
        ]
        assert compute_expense_status(shares) == ExpenseStatus.DISPUTED

    def test_ID047_expense_finalized_when_all_household_members_accepted(self):
        """100% accepted → FINALIZED."""
        shares = [
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.ACCEPTED),
        ]
        assert compute_expense_status(shares) == ExpenseStatus.FINALIZED

    def test_ID047_expense_without_vote_stays_pending(self):
        """No votes yet → PENDING."""
        shares = [
            make_share(VoteStatus.PENDING),
            make_share(VoteStatus.PENDING),
        ]
        assert compute_expense_status(shares) == ExpenseStatus.PENDING

    def test_ID047_expense_remains_pending_with_minority_vote(self):
        """1 accepted, 3 pending → PENDING (25% < 50%)."""
        shares = [
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.PENDING),
            make_share(VoteStatus.PENDING),
            make_share(VoteStatus.PENDING),
        ]
        assert compute_expense_status(shares) == ExpenseStatus.PENDING
