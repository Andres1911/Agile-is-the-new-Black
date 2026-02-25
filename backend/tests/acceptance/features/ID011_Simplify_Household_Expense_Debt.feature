Feature: Simplify household expense debt

  As a household member
  I want the system to simplify inter-member debts
  So that unnecessary circular or offsetting payments are removed

  Background:
    Given household "MapleHouse" exists with members
      | member |
      | Alice  |
      | Bob    |
      | Cara   |
    And the following net debts exist between members
      | debtor | creditor | amountCAD |
      | Bob    | Alice    | 10.00     |
      | Alice  | Cara     | 10.00     |
      | Cara   | Bob      | 10.00     |

  # Normal Flow: Circular debts cancel out completely
  Scenario: Fully circular debts are simplified to zero
    Given user "Alice" is authenticated as a household member
    When "Alice" requests to simplify household debts
    Then the system calculates the net balances between all members
    And the system removes the following debts
      | debtor | creditor | amountCAD |
      | Bob    | Alice    | 10.00     |
      | Alice  | Cara     | 10.00     |
      | Cara   | Bob      | 10.00     |
    And no outstanding debts remain between any members
    And the system displays message "All circular debts have been simplified"

  # Normal Flow: Partial simplification of debts
  Scenario: Circular debts are partially simplified when amounts differ
    Given the following net debts exist between members
      | debtor | creditor | amountCAD |
      | Bob    | Alice    | 15.00     |
      | Alice  | Cara     | 10.00     |
      | Cara   | Bob      | 10.00     |
    And user "Bob" is authenticated as a household member
    When "Bob" requests to simplify household debts
    Then the system offsets the circular portion of 10.00 CAD
    And the following debts remain
      | debtor | creditor | amountCAD |
      | Bob    | Alice    | 5.00      |
    And the system displays message "Household debts simplified successfully"

  # Normal Flow: Chain simplification (no cycle but reducible)
  Scenario: Linear chain debts are simplified to a direct debt
    Given the following net debts exist between members
      | debtor | creditor | amountCAD |
      | Bob    | Alice    | 20.00     |
      | Alice  | Cara     | 20.00     |
    And user "Cara" is authenticated as a household member
    When "Cara" requests to simplify household debts
    Then the system removes the intermediate debt
      | debtor | creditor | amountCAD |
      | Bob    | Alice    | 20.00     |
      | Alice  | Cara     | 20.00     |
    And the system creates a simplified debt
      | debtor | creditor | amountCAD |
      | Bob    | Cara     | 20.00     |
    And the system displays message "Debts simplified to minimize transactions"

  # Alternative Flow: No simplification possible
  Scenario: No simplification occurs when debts are independent
    Given the following net debts exist between members
      | debtor | creditor | amountCAD |
      | Bob    | Alice    | 10.00     |
      | Cara   | Alice    | 5.00      |
    And user "Alice" is authenticated as a household member
    When "Alice" requests to simplify household debts
    Then the system determines no circular or chain simplifications exist
    And all debts remain unchanged
    And the system displays message "No simplifications available"

  # Error Flow: Unauthorized user attempts simplification
  Scenario: Non-member attempts to simplify debts
    Given user "David" is not a member of household "MapleHouse"
    When "David" attempts to simplify household debts
    Then the system rejects the request
    And the system displays error message "Unauthorized: Only household members can simplify debts"

  # Edge Case: Household with no debts
  Scenario: Simplification requested when no debts exist
    Given no outstanding debts exist between members
    And user "Alice" is authenticated as a household member
    When "Alice" requests to simplify household debts
    Then the system performs no changes
    And the system displays message "No outstanding debts to simplify"