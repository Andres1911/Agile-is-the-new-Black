import re

import pytest

from app.core.invite_codes import (
    DEFAULT_INVITE_CODE_LENGTH,
    INVITE_CODE_ALPHABET,
    generate_unique_invite_code,
)
from app.models.models import Household


class TestInviteCodeTool:
    def test_generates_expected_length_and_charset(self, db):
        """Happy path: the tool returns an uppercase, human-friendly code."""
        code = generate_unique_invite_code(db)

        assert len(code) == DEFAULT_INVITE_CODE_LENGTH
        # Only allowed characters
        assert all(c in INVITE_CODE_ALPHABET for c in code)
        # Uppercase invariant
        assert code == code.upper()

        assert re.fullmatch(r"[A-Z2-9]+", code)

    def test_does_not_return_existing_code(self, db):
        """If a code already exists in the DB, the tool must not return it."""
        existing = "ABCDEFGH"
        db.add(Household(name="Existing", invite_code=existing))
        db.commit()

        candidates = iter([existing, "ZZZZZZZZ"])

        def candidate_fn(_len: int) -> str:
            return next(candidates)

        code = generate_unique_invite_code(db, candidate_fn=candidate_fn)
        assert code != existing
        assert code == "ZZZZZZZZ"

    def test_raises_after_max_attempts_when_all_candidates_collide(self, db):
        existing = "ABCDEFGH"
        db.add(Household(name="Existing", invite_code=existing))
        db.commit()

        def always_collide(_len: int) -> str:
            return existing

        with pytest.raises(RuntimeError):
            generate_unique_invite_code(db, max_attempts=3, candidate_fn=always_collide)

    @pytest.mark.parametrize(
        "length,max_attempts,exc",
        [
            (3, 10, ValueError),
            (0, 10, ValueError),
            (8, 0, ValueError),
        ],
    )
    def test_invalid_params_raise(self, db, length, max_attempts, exc):
        with pytest.raises(exc):
            generate_unique_invite_code(db, length=length, max_attempts=max_attempts)
