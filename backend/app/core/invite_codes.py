from __future__ import annotations

import secrets
from collections.abc import Callable

from app.models.models import Household

INVITE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

DEFAULT_INVITE_CODE_LENGTH = 8


def _random_candidate(length: int) -> str:
    return "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(length))


def generate_unique_invite_code(
    db,
    *,
    length: int = DEFAULT_INVITE_CODE_LENGTH,
    max_attempts: int = 1_000,
    candidate_fn: Callable[[int], str] | None = None,
) -> str:
    if length < 4:
        raise ValueError("Invite code length must be at least 4")
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    make_candidate = candidate_fn or _random_candidate

    for _ in range(max_attempts):
        code = make_candidate(length).upper()

        exists = db.query(Household).filter(Household.invite_code == code).first()
        if not exists:
            return code

    raise RuntimeError("Could not generate a unique invite code")
