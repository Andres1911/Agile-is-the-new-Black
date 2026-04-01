Feature: Scan and parse values from a receipt image
  As a household member
  I want to scan a receipt image and have the system extract the date, amount, and items
  So that I can quickly add expenses without manual entry

  Background:
    Given household "MapleHouse" exists with members
      | member |
      | Alice  |
      | Bob    |
      | Cara   |
    And user "Alice" is authenticated as a household member

  # Normal Flow: Successfully scan a clear receipt image
  Scenario: ID012 Household member scans a clear receipt and values are parsed successfully    (Normal Flow)
    Given "Alice" is logged in 
    When "Alice" photos a clear image of a receipt with the following details
      | field          | value        |
      | date           | 2026-03-01   |
      | total amount   | 45.97        |
      | item 1         | Milk 3.99    |
      | item 2         | Bread 2.49   |
      | item 3         | Chicken 9.99 |
    Then the system extracts and displays the following parsed values
      | field        | value      |
      | date         | 2026-03-01 |
      | totalAmount  | 45.97      |
    And the system extracts and displays the following items
      | item    | amount |
      | Milk    | 3.99   |
      | Bread   | 2.49   |
      | Chicken | 9.99   |
    And the system displays message "Receipt scanned successfully"

  # Alternative Flow: Member selects an existing image from device
  Scenario: ID012 Household member selects an existing receipt image from device gallery    (Alternative Flow)
    Given "Alice" is logged in
    When "Alice" selects a receipt image from the gallery with the following details
      | field          | value        |
      | date           | 2026-03-10   |
      | total amount   | 52.50        |
      | merchant       | Costco       |
    Then the system extracts and displays the following parsed values
      | field          | value        |
      | date           | 2026-03-10   |
      | totalAmount    | 52.50        |
      | merchant       | Costco       |
    And the system extracts and displays the following items
      | item           | amount |
      | Coffee Beans   | 18.99  |
      | Paper Towels   | 24.50  |
      | Sales Tax (QC) | 9.01   |
    And the system displays message "Receipt scanned successfully"

  # Alternative Flow: Partial extraction from a receipt
  Scenario: ID012 System partially extracts values from an unclear receipt    (Alternative Flow)
    Given "Alice" is logged in
    When "Alice" uploads a partially legible receipt image
    Then the system extracts the values it can identify
    And the system informs the user about fields it could not parse
    And the system displays message "Some values could not be read. Please review and complete the missing fields"

  # Error Flow: Unsupported file format uploaded
  Scenario: ID012 Household member uploads a file that is not a supported image format    (Error Flow)
    Given "Alice" is logged in
    When "Alice" uploads a file with an unsupported format "receipt.pdf"
    Then the system rejects the file
    And the system displays error message "Unsupported file format. Please upload a JPG, PNG, or HEIC image"

  # Error Flow: Image contains no recognizable receipt
  Scenario: ID012 Household member uploads an image that is not a receipt    (Error Flow)
    Given "Alice" is logged in
    When "Alice" uploads an image that does not contain a receipt
    Then the system fails to extract any receipt values
    And the system displays error message "No receipt detected in the image. Please upload a clear photo of a receipt"

  # Error Flow: Camera access denied
  Scenario: ID012 System cannot access the camera when permission is denied    (Error Flow)
    Given "Alice" is logged in
    When "Alice" requests camera access
    And "Alice" denies the permission
    Then the system does not open the camera
    And the system displays error message "Camera access denied. Please enable camera permissions or choose an image from your gallery"

  # Error Flow: No debts or items on receipt
  Scenario: ID012 Household member scans a receipt with zero items    (Error Flow)
    Given "Alice" is logged in
    When "Alice" uploads a valid image that contains a receipt header but no line items
    Then the system extracts the date and total amount if available
    And the system displays message "No individual items detected. Please add items manually"
