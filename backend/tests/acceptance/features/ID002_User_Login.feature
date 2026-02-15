Feature: User Login

  As a registered user
  I want to authenticate using either my email address or my username
  So that I have flexible yet secure access to my account and household data

  # --- Normal Flow ---
  Scenario Outline: Login with Email (Normal Flow)
    Given a user with email "<Email>" and password "<Password>" already exists in the system
    When the user attempts to log in with email "<Email>" and password "<Password>"
    Then the message "Success" is issued
    And a session will be created
    And the user should be redirected to the dashboard

    Examples:
      | Email             | Password  |
      | alice@example.com | Pass123!  |
      | bob@example.com   | Secure456 |

  # --- Alternative Flow ---
  Scenario Outline: Login with Username (Alternative Flow)
    Given a user with username "<UserName>" and password "<Password>" already exists in the system
    When the user attempts to log in with username "<UserName>" and password "<Password>"
    Then the message "Success" is issued
    And a session will be created
    And the user should be redirected to the dashboard

    Examples:
      | UserName | Password  |
      | Alice    | Pass123!  |
      | Bob      | Secure456 |

  # --- Error Flow ---
  Scenario Outline: Login Failure with Correct Username but Incorrect Password (Error Flow)
    Given a user with username "<UserName>" already exists in the system
    When the user attempts to log in with username "<UserName>" and an incorrect password "<WrongPassword>"
    Then the error message "Invalid username or password" is returned
    And a session will not be created
    And the user should remain on the login page

    Examples:
      | UserName | WrongPassword |
      | Alice    | WrongPass123  |
      | Bob      | Admin888      |

  # --- Error Flow ---
  Scenario Outline: Login Failure with Non-existent Email (Error Flow)
    Given the system has no user with email "<InvalidEmail>"
    When the user attempts to log in with email "<InvalidEmail>" and password "<AnyPassword>"
    Then the error message "Invalid email or password" is returned
    And a session will not be created
    And the user should remain on the login page

    Examples:
      | InvalidEmail            | AnyPassword |
      | ghost_user@example.com  | Secret123   |
      | unknown@mail.com        | Pass888!    |
