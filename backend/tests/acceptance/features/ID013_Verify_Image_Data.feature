Feature: Verify and modify image-extracted expense data

  As a household member
  I want to review and modify data extracted from an expense photo before saving it
  So that I can correct any OCR errors, add missing details, and save an accurate expense record

  Background:
    Given a user with username "Alice" exists in the system
    And a household named "MapleHouse" exists in the system
    And "Alice" is a member of "MapleHouse"
    And the user "Alice" is logged in
    And "Alice" has taken a photo of a receipt

  # --- Normal Flow ---

  Scenario: ID013 User verifies image extracted data without modifications    (Normal Flow)
    Given the system has processed the image and extracted amount "45.00" from the receipt
    When "Alice" confirms the extracted data with the following details
      | description | category  |
      | Grocery run | groceries |
    Then the data has the following details
      | amount | description | category  |
      | 45.00  | Grocery run | groceries |

  # --- Alternative Flows ---

  Scenario: ID013 User verifies image extracted data with modifications    (Alternative Flow)
    Given the system has processed the image and extracted amount "42.00" from the receipt
    When "Alice" modifies the extracted data with amount "45.00"
    And "Alice" confirms the extracted data with the following details
      | description         | category  |
      | Weekly grocery shop | groceries |
    Then the data has the following details
      | amount | description         | category  |
      | 45.00  | Weekly grocery shop | groceries |
  

  # --- Error Flows ---

  Scenario: ID013 User attempts to modify image extracted data with negative amount    (Error Flow)
    Given the system has processed the image and extracted amount "50.00" from the receipt
    When "Alice" modifies the extracted data with amount "-30.00"
    And "Alice" confirms the extracted data with the following details
      | description         | category  |
      | Weekly grocery shop | groceries |
    Then the system rejects the modification
    And the system displays error message "Invalid amount: Amount must be a positive number"
