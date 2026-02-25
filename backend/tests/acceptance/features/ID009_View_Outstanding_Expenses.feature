Feature: View outstanding expenses and balances

  As a household member
  I want to view my outstanding expenses and balances
  So that I know how much I owe or am owed

  Background:
    Given a user with username "Alice" exists in the system
    And a household named "MapleHouse" exists in the system
    And "Alice" is a member of "MapleHouse"
    And the following expense shares exist for "MapleHouse"
      | ExpenseDescription | Payee  | Payer | AmountOwed | VoteStatus | IsPaid |
      | Groceries         | Bob    | Alice | 50.00      | ACCEPTED   | False  |
      | Utilities         | Bob    | Alice | 100.00     | ACCEPTED   | False  |
      | Internet          | Alice  | Bob   | 60.00      | ACCEPTED   | False  |
      | Snacks            | Bob    | Alice | 10.00      | PENDING    | False  |
      | Taxi              | Bob    | Alice | 25.00      | ACCEPTED   | True   |
    And the user "Alice" is logged in

  Scenario: View shares where the user owes money (Normal Flow)
    When "Alice" requests her balances using GET "/users/me/balances"
    Then the household "MapleHouse" should show outstanding owed by "Alice" of 150.00 CAD
    And the response should include 2 outstanding shares where payer is "Alice"
    And the response should not include shares with vote status not "ACCEPTED"
    And the response should not include shares marked as paid

  Scenario: View expenses where the user is payee and is owed (Normal Flow)
    When "Alice" requests her balances using GET "/users/me/balances"
    Then the household "MapleHouse" should show outstanding owed to "Alice" of 60.00 CAD
    And the response should include 1 outstanding share where payee is "Alice"

  Scenario: View all outstanding household expenses summary (Normal Flow)
    When "Alice" requests her balances using GET "/users/me/balances"
    Then the response should include a summary for household "MapleHouse"
    And the summary total outstanding owed by "Alice" should be 150.00 CAD
    And the summary total outstanding owed to "Alice" should be 60.00 CAD

  Scenario: Member with no outstanding balances (Empty State)
    Given all expense shares for "Alice" in "MapleHouse" are marked as paid
    When "Alice" requests her balances using GET "/users/me/balances"
    Then the household "MapleHouse" should show outstanding owed by "Alice" of 0.00 CAD
    And the household "MapleHouse" should show outstanding owed to "Alice" of 0.00 CAD
    And the message "No outstanding balances" is issued

  Scenario: User not in any household (Error Flow)
    Given a user with username "Charlie" exists in the system
    And "Charlie" is logged in
    And "Charlie" is not a member of any household
    When "Charlie" requests balances using GET "/users/me/balances"
    Then the message "Cannot view expenses: You are not a member of any household" is issued
    And no balance data should be returned
