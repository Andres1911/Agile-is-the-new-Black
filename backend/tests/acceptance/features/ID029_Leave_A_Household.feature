Feature: Leave a household

  As a member of a household
  I want to be able to leave the household
  So that I can manage my transition to a new living arrangement

  Background:
    Given a user with username "<UserName>" already exists in the system 
    And the user "<UserName>" is logged in 

  # --- Normal Flow ---

  Scenario Outline: ID029 Household member with no outstanding debt successfully leaves a household    (Normal Flow)
    Given the user "<UserName>" is living in the household "<HouseholdName>" 
    And the user "<UserName>" has no outstanding balance in "<HouseholdName>"
    When the user requests to leave the household "<HouseholdName>"
    Then the message "Success" is issued 
    And the binding record linking User "<UserName>" to Household "<HouseholdName>" should have LiveIn = false 

    Examples:
      | UserName | HouseholdName  |
      | Alice    | MapleHouse     |
      | Charlie  | The North Star |

    # --- Alternative Flow ---

  Scenario Outline: ID029 Admin successfully leaves after transferring ownership to another member    (Alternative Flow)
    Given the user "<UserName>" is living in the household "<HouseholdName>" 
    And the user "<UserName>" is an admin with IsAdmin = true 
    And the household "<HouseholdName>" has other active members
    And the user "<NewAdmin>" is a member of household "<HouseholdName>"
    When the user "<UserName>" transfers the admin rights to "<NewAdmin>"
    And the user requests to leave the household "<HouseholdName>"
    Then the message "Success" is issued 
    And the binding record linking User "<UserName>" to Household "<HouseholdName>" should have LiveIn = false 
    And the user "<NewAdmin>" should have IsAdmin = true for "<HouseholdName>"

    Examples:
      | UserName | HouseholdName     | NewAdmin |
      | Andres   | McGill Engineers  | Bob      |
      | Samy     | The North Star    | Alice    |

  # --- Error Flows ---

  Scenario Outline: ID029 Household member with an outstanding balance attempts to leave    (Error Flow)
    Given the user "<UserName>" is living in the household "<HouseholdName>" 
    And the user "<UserName>" has a debt of "<Amount>" to another member
    When the user requests to leave the household "<HouseholdName>"
    Then the message "Cannot leave: Outstanding balance remains" is issued
    And the binding record linking User "<UserName>" to Household "<HouseholdName>" should have LiveIn = true 

    Examples:
      | UserName | HouseholdName  | Amount |
      | Alice    | MapleHouse     | 15.50  |
      | Bob      | The North Star | 5.00   |

  Scenario Outline: ID029 Admin attempts to leave without appointing a successor    (Error Flow)
    Given the user "<UserName>" is living in the household "<HouseholdName>" 
    And the user "<UserName>" is an admin with IsAdmin = true 
    And the household "<HouseholdName>" has other active members
    When the user requests to leave the household "<HouseholdName>"
    Then the message "Error: Admin must transfer ownership before leaving" is issued
    And the binding record linking User "<UserName>" to Household "<HouseholdName>" should have IsAdmin = true and LiveIn = true

    Examples:
      | UserName | HouseholdName     |
      | Andres   | McGill Engineers  |
      | Samy     | The North Star    |

  