Feature: Join A Household

  As a user not living in any household
  I would like to enter a unique invite code
  So that I can join my roommates' existing household

  Background:
    Given a user with username "<UserName>" already exists in the system
    And the user "<UserName>" is logged in

  # --- Normal Flow ---

  Scenario Outline: Guest joins a household with correct credentials (Normal Flow)
    Given the user "<UserName>" does not currently belong to any household
    And a household named "<HouseholdName>" exists in the system
    And the household "<HouseholdName>" has the invite code "<InviteCode>"
    When the user requests to join household "<HouseholdName>" with invite code "<InviteCode>"
    Then the message "Success" is issued
    And a binding record should link User "<UserName>" to Household "<HouseholdName>"
    And the binding should have LiveIn = true
    And the binding should have IsAdmin = false

    Examples:
      | UserName | HouseholdName  | InviteCode   |
      | Charlie  | The North Star | MYHOUSE2024  |

  # --- Error Flows ---

  Scenario Outline: Attempt to join with an incorrect invite code (Error Flow)
    Given the user "<UserName>" does not currently belong to any household
    And a household named "<HouseholdName>" exists in the system
    And the household "<HouseholdName>" has a code that is NOT "<WrongCode>"
    When the user requests to join household "<HouseholdName>" with invite code "<WrongCode>"
    Then the message "Invalid invite code" is issued
    And the user "<UserName>" should still not belong to any household

    Examples:
      | UserName | HouseholdName  | WrongCode    |
      | Charlie  | The North Star | WRONG666     |

  Scenario Outline: Attempt to join a non-existent household (Error Flow)
    Given the user "<UserName>" does not currently belong to any household
    And a household named "<FakeHouse>" does not exist in the system
    When the user requests to join household "<FakeHouse>" with any invite code "CODE123"
    Then the message "Household not found" is issued
    And the user "<UserName>" should still not belong to any household

    Examples:
      | UserName | FakeHouse      |
      | Charlie  | GhostMansion   |
      | Dave     | MarsColony     |

  Scenario Outline: Already-in-household user attempts to join another (Error Flow)
    Given the user "<UserName>" is already living in the household "<CurrentHome>"
    And another household named "<TargetHouse>" exists with the invite code "<ValidCode>"
    When the user requests to join household "<TargetHouse>" with invite code "<ValidCode>"
    Then the message "User is already registered as living in another household" is issued
    And the user "<UserName>" should still only be bound to "<CurrentHome>"
    And no binding record should exist between User "<UserName>" and Household "<TargetHouse>"

    Examples:
      | UserName | CurrentHome    | TargetHouse   | ValidCode    |
      | Charlie  | The North Star | DowntownLoft  | LOFTSUITE123 |