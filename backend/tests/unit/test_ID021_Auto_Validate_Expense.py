# tests/unit/test_auto_validate_expense.py

from unittest.mock import MagicMock

from app.api.expenses import compute_expense_status
from app.models.models import ExpenseShare, ExpenseStatus, VoteStatus


def make_share(vote_status: VoteStatus) -> ExpenseShare:
    share = MagicMock(spec=ExpenseShare)
    share.vote_status = vote_status
    return share


class TestAutoValidateExpense:
    def test_majority_accepted_finalizes_expense(self):
        """Strictly more than 50% accepted → FINALIZED."""
        shares = [
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.REJECTED),
        ]
        assert compute_expense_status(shares) == ExpenseStatus.FINALIZED

    def test_exactly_50_percent_accepted_does_not_finalize(self):
        """Exactly 50% accepted → not FINALIZED (stays DISPUTED due to rejection)."""
        shares = [
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.REJECTED),
        ]
        assert compute_expense_status(shares) == ExpenseStatus.DISPUTED

    def test_minority_accepted_stays_disputed(self):
        """Less than 50% accepted with rejections → DISPUTED."""
        shares = [
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.REJECTED),
            make_share(VoteStatus.REJECTED),
        ]
        assert compute_expense_status(shares) == ExpenseStatus.DISPUTED

    def test_all_accepted_finalizes_expense(self):
        """100% accepted → FINALIZED."""
        shares = [
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.ACCEPTED),
        ]
        assert compute_expense_status(shares) == ExpenseStatus.FINALIZED

    def test_all_pending_stays_pending(self):
        """No votes yet → PENDING."""
        shares = [
            make_share(VoteStatus.PENDING),
            make_share(VoteStatus.PENDING),
        ]
        assert compute_expense_status(shares) == ExpenseStatus.PENDING

    def test_mixed_pending_and_accepted_no_majority(self):
        """1 accepted, 3 pending → PENDING (25% < 50%)."""
        shares = [
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.PENDING),
            make_share(VoteStatus.PENDING),
            make_share(VoteStatus.PENDING),
        ]
        assert compute_expense_status(shares) == ExpenseStatus.PENDING

    def test_majority_accepted_overrides_disputed_state(self):
        """Even with one rejection, if majority accepted → FINALIZED."""
        shares = [
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.ACCEPTED),
            make_share(VoteStatus.REJECTED),
        ]
        assert compute_expense_status(shares) == ExpenseStatus.FINALIZED
