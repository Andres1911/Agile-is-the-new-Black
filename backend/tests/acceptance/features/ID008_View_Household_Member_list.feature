Feature: View Household Member List

  As a household member
  I want to view the list of members in my household
  So that I know who I am sharing and splitting expenses with

  Background:
    Given household "MapleHouse" exists with members
      | member | role   |
      | Alice  | owner  |
      | Bob    | member |
      | Cara   | member |

  # Normal Flow

  Scenario: Member views the full list of household members (Normal Flow)
    Given user "Alice" is authenticated as a household member
    When "Alice" requests the member list for household "MapleHouse"
    Then the system returns the following members for "MapleHouse"
      | member | role   |
      | Alice  | owner  |
      | Bob    | member |
      | Cara   | member |
    And the message "Success" is issued

  # Alternative Flow 

  Scenario Outline: Any household member can view the member list (Alternative Flow)
    Given user "<User>" is authenticated as a household member
    When "<User>" requests the member list for household "MapleHouse"
    Then the system returns the following members for "MapleHouse"
      | member | role   |
      | Alice  | owner  |
      | Bob    | member |
      | Cara   | member |
    And the message "Success" is issued

    Examples:
      | User  |
      | Bob   |
      | Cara  |

  # Error Flows

  Scenario: User not in the household attempts to view the member list (Error Flow)
    Given user "Dave" is authenticated and exists in the system
    And user "Dave" is not a member of household "MapleHouse"
    When "Dave" requests the member list for household "MapleHouse"
    Then the system denies the request
    And the error message "Access denied: You are not a member of this household" is returned

  Scenario: Unauthenticated user attempts to view the member list (Error Flow)
    Given no user is authenticated
    When an unauthenticated request is made to view the member list for household "MapleHouse"
    Then the system denies the request
    And the error message "Not authenticated" is returned

  Scenario: Member requests the member list for a non-existent household (Error Flow)
    Given user "Alice" is authenticated as a household member
    And no household with name "GhostHouse" exists in the system
    When "Alice" requests the member list for household "GhostHouse"
    Then the system denies the request
    And the error message "Household not found" is returned
