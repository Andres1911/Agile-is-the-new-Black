Feature: Add new user

  As a new visitor
  I want to create an account by providing a unique username, email, and a secure password
  So that I can use the system services

  # --- Normal Flow ---

  Scenario Outline: Add a New User (Normal Flow)
    Given the system has no user with email "<Email>"
    And the system has no user with username "<UserName>"
    When the password "<Password>" is valid (at least 8 characters)
    And a registration is requested with username "<UserName>" and email "<Email>" and password "<Password>"
    Then the account with email "<Email>" and username "<UserName>" and password "<Password>" is successfully created
    And the message "Success" is issued
    And a user record for "<UserName>" should exist

    Examples:
      | UserName | Email             | Password  |
      | Alice    | alice@example.com | Pass123!  |
      | Bob      | bob@example.com   | Secure456 |

  # --- Error Flows ---

  Scenario Outline: Register with Duplicate Username and Invalid Password (Error Flow)
    Given the system has no user with email "<InputEmail>"
    And a user with username "<InputUserName>" exists
    When the password "<Password>" is invalid (less than 8 characters)
    And a registration is requested with username "<InputUserName>" and email "<InputEmail>" and password "<Password>"
    Then the account with email "<InputEmail>" should not be created
    And the error message "Username Already in Use, Password Invalid" is returned

    Examples:
      | InputEmail       | InputUserName | Password |
      | unique@mail.com  | Bob           | 123      |
      | test@example.com | Alice         | abcd     |

  Scenario Outline: Register with Duplicate Email (Error Flow)
    Given a user with email "<InputEmail>" already exists
    And the system has no user with username "<InputUserName>"
    When the password "<Password>" is valid (at least 8 characters)
    And a registration is requested with username "<InputUserName>" and email "<InputEmail>" and password "<Password>"
    Then the account with email "<InputUserName>" should not be created
    And the error message "Email Address Already in Use" is returned

    Examples:
      | InputEmail        | InputUserName | Password  |
      | alice@example.com | BrandNewUser  | Pass123!  |
      | bob@example.com   | UniqueHero    | Secure789 |
