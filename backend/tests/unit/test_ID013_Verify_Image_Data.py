from app.api.expenses import verify_and_modify_expense
from app.schemas.schemas import ExpenseCreate


class TestVerifyImageDataLogic:
    def test_ID013_logic_modify_amount_to_zero(self):
        """
        Scenario: User attempts to modify image-extracted data with zero amount.
        Verification: Ensure the logic layer raises an error or returns a failure message
        when the manually overridden amount is 0.0.
        """
        # 1. Simulate the system-extracted data (OCR Result)
        # Assume OCR initially found 50.0
        initial_expense = ExpenseCreate(
            description="", amount=50.0, category=None, split_evenly=True, include_creator=True
        )

        # 2. Define the user's malicious/invalid override
        manual_amount = 0.0
        change_amount = True
        new_description = "Free Coffee"
        new_category = "Food"

        # 3. Call the logic function and capture the error/exception
        # Depending on how your verify_and_modify_expense is implemented,
        # it might raise a ValueError or return an object with an error attribute.

        try:
            result = verify_and_modify_expense(
                expense=initial_expense,
                change_amount=change_amount,
                amount=manual_amount,
                description=new_description,
                category=new_category,
            )
            assert result is None

        except Exception as e:
            # 4. Assert the error message is correct
            assert str(e) == "Invalid amount: Amount must be a positive number"
