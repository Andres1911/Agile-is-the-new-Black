Feature: Confirm expense is paid

  As a household member
  I want to confirm that my share of an expense has been paid
  So that outstanding balances are updated and payments are tracked

  Background:
    Given household "MapleHouse" exists with members
      | member |
      | Alice  |
      | Bob    |
      | Cara   |
    And user "Alice" has created the following expense
      | expenseId | description | amountCAD | date       |
      | EXP-101   | Grocery run | 60.00     | 2026-02-01 |
    And expense "EXP-101" has the following expense shares
      | participant | shareCAD | outstandingCAD | status |
      | Bob         | 20.00    | 20.00          | Unpaid |
      | Cara        | 40.00    | 40.00          | Unpaid |

  # Normal Flow: Participant confirms full payment of their share
  Scenario: Participant confirms full payment of their expense share
    Given user "Bob" is authenticated as a household member
    When "Bob" confirms payment of his expense share for expense "EXP-101" with amount 20.00 CAD
    Then the system records the payment
      | payer | expenseId | amountCAD |
      | Bob   | EXP-101   | 20.00     |
    And expense "EXP-101" has the following updated expense shares
      | participant | shareCAD | outstandingCAD | status |
      | Bob         | 20.00    | 0.00           | Paid   |
      | Cara        | 40.00    | 40.00          | Unpaid |
    And expense "EXP-101" status is "Partially Settled"

  # Normal Flow: Full settlement of expense
  Scenario: Expense becomes fully settled when all participants confirm payment
    Given user "Cara" is authenticated as a household member
    And "Bob" has already confirmed payment of his expense share for expense "EXP-101"
    And expense "EXP-101" has the following expense shares
      | participant | shareCAD | outstandingCAD | status  |
      | Bob         | 20.00    | 0.00           | Paid    |
      | Cara        | 40.00    | 40.00          | Unpaid  |
    When "Cara" confirms payment of her expense share for expense "EXP-101" with amount 40.00 CAD
    Then the system records the payment
      | payer | expenseId | amountCAD |
      | Cara  | EXP-101   | 40.00     |
    And expense "EXP-101" has the following updated expense shares
      | participant | shareCAD | outstandingCAD | status |
      | Bob         | 20.00    | 0.00           | Paid   |
      | Cara        | 40.00    | 0.00           | Paid   |
    And expense "EXP-101" status is "Fully Settled"

  # Alternative Flow: Partial payment
  Scenario: Participant confirms partial payment of their expense share
    Given user "Cara" is authenticated as a household member
    When "Cara" confirms payment of her expense share for expense "EXP-101" with amount 15.00 CAD
    Then the system records the payment
      | payer | expenseId | amountCAD |
      | Cara  | EXP-101   | 15.00     |
    And expense "EXP-101" has the following updated expense shares
      | participant | shareCAD | outstandingCAD | status         |
      | Bob         | 20.00    | 20.00          | Unpaid         |
      | Cara        | 40.00    | 25.00          | Partially Paid |
    And expense "EXP-101" status is "Partially Settled"

  # Error Flow: Non-participant attempts to confirm payment
  Scenario: Non-participant attempts to confirm payment for an expense they have no share in
    Given user "Alice" has created the following expense
      | expenseId | description | amountCAD | date       |
      | EXP-102   | Movie night | 30.00     | 2026-02-02 |
    And expense "EXP-102" has the following expense shares
      | participant | shareCAD | outstandingCAD | status |
      | Bob         | 30.00    | 30.00          | Unpaid |
    And user "Cara" is authenticated as a household member
    When "Cara" attempts to confirm payment for expense "EXP-102"
    Then the system rejects the payment confirmation
    And the system displays error message "Cannot confirm payment: You do not have an expense share for this expense"
    And expense "EXP-102" expense shares remain unchanged
      | participant | shareCAD | outstandingCAD | status |
      | Bob         | 30.00    | 30.00          | Unpaid |

  # Error Flow: Payment exceeds outstanding share
  Scenario: Participant attempts to confirm payment exceeding their outstanding share
    Given user "Bob" is authenticated as a household member
    When "Bob" attempts to confirm payment of his expense share for expense "EXP-101" with amount 25.00 CAD
    Then the system rejects the payment confirmation
    And the system displays error message "Cannot confirm payment: Amount 25.00 CAD exceeds outstanding balance of 20.00 CAD"
    And "Bob" expense share for expense "EXP-101" remains unchanged with outstanding 20.00 CAD

  # Error Flow: Attempt to confirm payment for already paid share
  Scenario: Participant attempts to confirm payment for an already paid expense share
    Given user "Bob" is authenticated as a household member
    And "Bob" has already confirmed payment of his expense share for expense "EXP-101"
    And expense "EXP-101" has the following expense shares
      | participant | shareCAD | outstandingCAD | status |
      | Bob         | 20.00    | 0.00           | Paid   |
      | Cara        | 40.00    | 40.00          | Unpaid |
    When "Bob" attempts to confirm payment of his expense share for expense "EXP-101" with amount 5.00 CAD
    Then the system rejects the payment confirmation
    And the system displays error message "Cannot confirm payment: Your expense share is already fully paid"
