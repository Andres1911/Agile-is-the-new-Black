def simplify_debt(debt: dict) -> dict:
    """
    Simplify the debt by removing cycles.
    """
    return {
        "name": debt["name"],
        "amount": debt["amount"],
        "interest_rate": debt["interest_rate"],
        "remaining_balance": debt["remaining_balance"],
    }
