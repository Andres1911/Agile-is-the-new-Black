Feature: Create and split an expense

  As a household member
  I want to create an expense and split it among household members
  So that everyone knows their share and can pay it back

  Background:
    Given household "MapleHouse" exists with members
      | member |
      | Alice  |
      | Bob    |
      | Cara   |

  # Normal Flow: Create expense and split among multiple members
  Scenario: Member creates an expense and splits it among household members
    Given user "Alice" is authenticated as a household member
    When "Alice" specifies an expense with the following details
      | description | amountCAD |
      | Grocery run | 60.00     |
    And "Alice" creates and splits the expense among the following members
      | payer | shareCAD |
      | Bob   | 20.00    |
      | Cara  | 40.00    |
    Then the system records an expense for "Alice" in "MapleHouse" with amount "60.00", description "Grocery run", category "None", and status "PENDING"
    And the expense has the following expense shares
      | user  | amount_owed | paid_amount | is_paid | vote_status |
      | Bob   | 20.00       | 0.00        | False   | PENDING     |
      | Cara  | 40.00       | 0.00        | False   | PENDING     |

  # Normal Flow: Equal split among all members
  Scenario: Member creates an expense with equal split among all household members
    Given user "Alice" is authenticated as a household member
    When "Alice" specifies an expense with the following details
      | description  | amountCAD | category    |
      | Utility bill | 90.00     | electricity |
    And "Alice" creates and splits the expense equally with include_self="false"
    Then the system records an expense for "Alice" in "MapleHouse" with amount "90.00", description "Utility bill", category "electricity", and status "PENDING"
    And the expense has the following expense shares
      | user  | amount_owed | paid_amount | is_paid | vote_status |
      | Bob   | 45.00       | 0.00        | False   | PENDING     |
      | Cara  | 45.00       | 0.00        | False   | PENDING     |

  # Alternative Flow: Payee includes themselves in the split
  Scenario: Payee includes themselves as a payer in the expense split
    Given user "Alice" is authenticated as a household member
    When "Alice" specifies an expense with the following details
      | description | amountCAD | category    |
      | Pizza night | 30.00     | food        |
    And "Alice" creates and splits the expense among the following members
      | payer | shareCAD |
      | Alice | 10.00    |
      | Bob   | 10.00    |
      | Cara  | 10.00    |
    Then the system records an expense for "Alice" in "MapleHouse" with amount "30.00", description "Pizza night", category "food", and status "PENDING"
    And the expense has the following expense shares
      | user  | amount_owed | paid_amount | is_paid | vote_status |
      | Alice | 10.00       | 0.00        | False   | ACCEPTED    |
      | Bob   | 10.00       | 0.00        | False   | PENDING     |
      | Cara  | 10.00       | 0.00        | False   | PENDING     |

  # Error Flow: Split amounts do not match total expense
  Scenario: Member attempts to create expense where split amounts do not equal total
    Given user "Alice" is authenticated as a household member
    When "Alice" specifies an expense with the following details
      | description | amountCAD | category    |
      | Grocery run | 60.00     | groceries   |
    And "Alice" creates and splits the expense among the following members
      | payer | shareCAD |
      | Bob   | 20.00    |
      | Cara  | 30.00    |
    Then the system rejects the expense creation
    And the system displays error message "Cannot create expense: Split amounts 50.00 CAD do not equal expense total 60.00 CAD"

  # Error Flow: Create expense with zero or negative amount
  Scenario: Member attempts to create expense with invalid amount
    Given user "Alice" is authenticated as a household member
    When "Alice" specifies an expense with the following details
      | description | amountCAD | category    |
      | Invalid     | -10.00    | invalid     |
    And "Alice" creates and splits the expense among the following members
      | payer | shareCAD |
      | Bob   | -10.00    |
    Then the system rejects the expense creation
    And the system displays error message "Cannot create expense: Amount must be greater than zero"
