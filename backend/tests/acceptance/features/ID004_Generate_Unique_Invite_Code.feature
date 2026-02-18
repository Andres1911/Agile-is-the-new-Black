Feature: Generate unique invite code for households (ID004)

  As a household creator
  I want the system to generate a unique invite code for my household
  So that other users can join my household using a simple code

  Background:
    Given user "Alice" is authenticated
    And household "MapleHouse" exists with members
      | member |
      | Alice  |
      | Bob    |
      | Cara   |
    And household "MapleHouse" has invite code "ABCDEFGH"

  # --- Normal Flow ---

  Scenario Outline: Create household generates a unique invite code (Normal Flow)
    Given the system has no household with name "<NewHousehold>"
    When "Alice" creates household "<NewHousehold>"
    Then the system creates household "<NewHousehold>"
    And the system generates an invite code for household "<NewHousehold>"
    And household "<NewHousehold>" has an invite code that is 8 characters long
    And household "<NewHousehold>" invite code contains only uppercase letters and digits
    And household "<NewHousehold>" invite code is unique (not used by any existing household)

    Examples:
      | NewHousehold |
      | PineHouse    |
      | CedarHouse   |
      | OakHouse     |

  Scenario Outline: Generated invite code does not match a known existing code (Normal Flow)
    Given the system has no household with name "<NewHousehold>"
    When "Alice" creates household "<NewHousehold>"
    Then the system creates household "<NewHousehold>"
    And household "<NewHousehold>" invite code should not equal "<ExistingCode>"

    Examples:
      | NewHousehold | ExistingCode |
      | BirchHouse   | ABCDEFGH     |
      | SpruceHouse  | ABCDEFGH     |

  # --- Alternative Flow ---

  Scenario Outline: System retries when the generated invite code collides (Alternative Flow)
    Given the system has no household with name "<NewHousehold>"
    And the invite code generator will propose codes "<FirstCode>" then "<SecondCode>"
    When "Alice" creates household "<NewHousehold>" using the proposed codes
    Then the system creates household "<NewHousehold>"
    And household "<NewHousehold>" invite code should equal "<SecondCode>"
    And household "<NewHousehold>" invite code is unique (not used by any existing household)

    Examples:
      | NewHousehold | FirstCode | SecondCode |
      | ElmHouse     | ABCDEFGH  | ZZZZZZZZ   |
      | AshHouse     | ABCDEFGH  | QWERTY22   |

  # --- Error Flow ---

  Scenario Outline: Household creation is rejected if no unique invite code can be generated (Error Flow)
    Given the system has no household with name "<NewHousehold>"
    And the invite code generator will always return "<CollidingCode>"
    When "Alice" creates household "<NewHousehold>"
    Then the system rejects the household creation
    And the system displays error message "<ErrorMessage>"
    And no household named "<NewHousehold>" is created

    Examples:
      | NewHousehold | CollidingCode | ErrorMessage                                                    |
      | WillowHouse  | ABCDEFGH      | Cannot create household: Unable to generate a unique invite code |
