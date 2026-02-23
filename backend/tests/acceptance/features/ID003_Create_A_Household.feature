Feature: Create a household

  As a user without a household
  I want to create a new household
  So that I can invite others and start managing our shared household expenses

  Background:
    Given a user with username "<UserName>" already exists in the system
    And the user "<UserName>" is logged in

  Scenario Outline: Create a New Household (Normal Flow)
    Given the user "<UserName>" hasn't been assigned a household
    And a household named "<Name>" does not exist
    When requesting the addition of household "<Name>"
    Then a household named "<Name>" should be created successfully
    And the message "Success" is issued
    And a binding record should link User "<UserName>" to Household "<Name>"
    And the binding should have LiveIn = true
    And the binding should have IsAdmin = true

    Examples:
      | UserName | Name         |
      | Alice    | MapleHouse   |
      | Bob      | DowntownLoft |

  Scenario Outline: Create a New Household with Address (Alternative Flow)
    Given the user "<UserName>" hasn't been assigned a household
    And a household named "<Name>" does not exist
    When requesting the addition of household "<Name>" with address "<Address>"
    Then a household named "<Name>" with address "<Address>" should be created successfully
    And the message "Success" is issued
    And a binding record should link User "<UserName>" to Household "<Name>"
    And the binding should have LiveIn = true
    And the binding should have IsAdmin = true

    Examples:
      | UserName | Name        | Address          |
      | Charlie  | SunsetVilla | 123 Maple St, NY |
      | David    | GreenGarden | 456 Oak Ave, LA  |

  Scenario Outline: Attempt to Create a Household with a Duplicate Name (Error Flow)
    Given a household named "<HouseholdName>" already exists in the system
    And the user "<UserName>" is not currently living in any household
    When requesting the addition of household "<HouseholdName>"
    Then the message "Name already exists" is issued
    And the user "<UserName>" should still not live in any household

    Examples:
      | UserName | HouseholdName |
      | Alice    | MapleHouse    |
      | Bob      | Downtown      |

  Scenario Outline: Attempt to Create a New Household While Already Lived In (Error Flow)
    Given the user "<UserName>" is already living in the household "<CurrentHome>"
    When requesting the addition of household "<NewHome>"
    Then the message "User is already registered as living in another household" is issued
    And the old binding record should still link User "<UserName>" to Household "<CurrentHome>"
    And the binding should have LiveIn = true
    And no binding record should exist between User "<UserName>" and Household "<NewHome>"

    Examples:
      | UserName | CurrentHome | NewHome      |
      | Alice    | MapleHouse  | SecondHome   |
      | Bob      | Downtown    | SummerVilla  |