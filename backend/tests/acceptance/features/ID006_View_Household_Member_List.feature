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

  Scenario: ID006 Household admin Views household members    (Normal Flow)
    Given user "Alice" is authenticated as a household member
    When "Alice" requests the member list for household "MapleHouse"
    Then the system returns the following members for "MapleHouse"
      | member | role   |
      | Alice  | owner  |
      | Bob    | member |
      | Cara   | member |
    And the message "Success" is issued

  # Alternative Flow 

  Scenario Outline: ID006 Household non-admin Views household members    (Alternative Flow)
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

  Scenario: ID006 User not living in the household attempts to view that household members    (Error Flow)
    Given user "Dave" is authenticated and exists in the system
    And user "Dave" is not a member of household "MapleHouse"
    When "Dave" requests the member list for household "MapleHouse"
    Then the system denies the request
    And the error message "Access denied: You are not a member of this household" is returned

  Scenario: ID006 User not logged in attempts to view members of his household    (Error Flow)
    Given no user is authenticated
    When an unauthenticated request is made to view the member list for household "MapleHouse"
    Then the system denies the request
    And the error message "Not authenticated" is returned

  Scenario: ID006 User attempts to view the members of a non-existent household    (Error Flow)
    Given user "Alice" is authenticated as a household member
    And no household with name "GhostHouse" exists in the system
    When "Alice" requests the member list for household "GhostHouse"
    Then the system denies the request
    And the error message "Household not found" is returned
