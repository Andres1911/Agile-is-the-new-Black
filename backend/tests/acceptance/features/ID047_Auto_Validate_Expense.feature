Feature: Auto-validate expense by member majority
  As a household member
  I want the system to automatically finalize an expense
  So that disputed expenses are resolved without admin intervention when enough members agree

  Background:
    Given household "MapleHouse" exists with members
      | member | role   |
      | Alice  | ADMIN  |
      | Bob    | MEMBER |
      | Cara   | MEMBER |
      | Paul   | MEMBER |
      | Dave   | MEMBER |
    And user "Alice" has an existing expense with the following details
      | description   | amount | status   |
      | Internet Bill | 60.00  | DISPUTED |
    And the expense has the following expense shares
      | payer | amount_owed | vote_status |
      | Bob   | 20.00       | REJECTED    |
      | Cara  | 20.00       | PENDING     |
      | Paul  | 20.00       | PENDING     |

  Scenario: ID047 Expense is auto-finalized when strictly more than 50% of members accept    (Normal Flow)
    Given "Bob" is logged in
    When "Cara" accepts the expense share for "Internet Bill"
    And "Paul" accepts the expense share for "Internet Bill"
    Then the system automatically updates the status of "Internet Bill" to "FINALIZED"
    And the system displays success message "Expense share accepted"

  Scenario: ID047 Expense remains disputed when fewer than 50% of members accept    (Normal Flow)
    Given the expense has the following expense shares
      | payer | amount_owed | vote_status |
      | Bob   | 15.00       | REJECTED    |
      | Cara  | 15.00       | REJECTED    |
      | Paul  | 15.00       | PENDING     |
      | Dave  | 15.00       | PENDING     |
    When "Paul" accepts the expense share for "Internet Bill"
    Then the status of "Internet Bill" remains "DISPUTED"
  
   Scenario: ID047 Expense remains disputed when exactly 50% of members accept    (Alternate Flow)
    Given "Bob" is logged in
    When "Cara" accepts the expense share for "Internet Bill"
    Then the status of "Internet Bill" remains "DISPUTED"

  Scenario: ID047 Expense is auto-finalized when all members accept    (Normal Flow)
    When "Cara" accepts the expense share for "Internet Bill"
    And "Paul" accepts the expense share for "Internet Bill"
    And "Bob" changes their vote to accepted for "Internet Bill"
    Then the system automatically updates the status of "Internet Bill" to "FINALIZED"