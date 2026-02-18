Feature: Generate unique invite code for households

  As a user
  I want a household to receive a unique invite code when created
  So that other members can join using that code

  Background:
    Given user "Alice" is authenticated
    And household "MapleHouse" exists with invite code "ABCDEFGH"

  # Normal Flow: creating a new household generates a unique code
  Scenario Outline: Create household generates a unique invite code (Normal Flow)
    When "Alice" creates household "<householdName>"
    Then household "<householdName>" is created
    And household "<householdName>" has an invite code
    And the invite code is 8 characters long
    And the invite code contains only allowed characters
    And the invite code is not "ABCDEFGH"

    Examples:
      | householdName |
      | PineHouse     |
      | CedarHouse    |
      | OakHouse      |

  # Normal Flow: generated code differs from a known existing code
  Scenario Outline: Generated invite code does not match a known existing code (Normal Flow)
    When "Alice" creates household "<householdName>"
    Then household "<householdName>" has an invite code
    And the invite code is not "<existingCode>"

    Examples:
      | householdName | existingCode |
      | BirchHouse    | ABCDEFGH     |
      | SpruceHouse   | ABCDEFGH     |

  # Alternative Flow: collision then retry
  Scenario Outline: System retries when the generated invite code collides (Alternative Flow)
    Given the invite code generator will propose codes "<firstCandidate>" then "<secondCandidate>"
    When "Alice" creates household "<householdName>"
    Then household "<householdName>" has invite code "<secondCandidate>"

    Examples:
      | householdName | firstCandidate | secondCandidate |
      | ElmHouse      | ABCDEFGH       | ZZZZZZZZ        |
      | AshHouse      | ABCDEFGH       | QWERTY22        |

  # Error Flow: cannot generate unique code
  Scenario Outline: Household creation is rejected if no unique invite code can be generated (Error Flow)
    Given the invite code generator will propose code "<collidingCode>"
    When "Alice" attempts to create household "<householdName>"
    Then the system rejects the household creation
    And the system displays error message "<errorMessage>"

    Examples:
      | householdName | collidingCode | errorMessage                                                     |
      | WillowHouse   | ABCDEFGH      | Cannot create household: Unable to generate a unique invite code |
