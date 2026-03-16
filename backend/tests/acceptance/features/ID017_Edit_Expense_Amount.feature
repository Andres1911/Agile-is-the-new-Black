# Kevin Jiang
# 261090190

Feature: Edit an expense amount

    As an expense creator
    I want to edit the amount of an expense I created
    So that I can ensure the accuracy of the expense before it settles

    Background:
        Given household "MapleHouse" exists with members
            | member |
            | Alice  |
            | Bob    |
            | Cara   |
    
    Scenario: ID017 Household member edits the amount of their expense and resplits it manually   (normal flow)
        Given user "Alice" is logged in
        And "Alice" has an existing expense with the following details
            | description | amount | status  |
            | Grocery run | 60.00  | PENDING |
        And the expense has the following expense shares
            | payer | amount_owed | paid_amount | is_paid | vote_status  |
            | Bob   | 30.00       | 0.00        | False   | PENDING      |
            | Cara  | 30.00       | 0.00        | False   | PENDING      |
        When "Alice" edits the expense amount to "90.00"
        And "Alice" manually updates the expense shares with the following amounts
            | payer | amount_owed |
            | Bob   | 30.00       |
            | Cara  | 60.00       |
        Then the system updates that expense for "Alice" in "MapleHouse" with amount "90.00"
        And the description "Grocery run", category "None", and status "PENDING" remain unchanged
        And the expense has the following expense shares
            | payer | amount_owed | paid_amount | is_paid | vote_status |
            | Bob   | 30.00       | 0.00        | False   | PENDING     |
            | Cara  | 60.00       | 0.00        | False   | PENDING     |
    

    Scenario: ID017 Household member edits the amount of their expense and resplits it equally    (alternative flow)
        Given user "Alice" is logged in
        And "Alice" has an existing expense with the following details
            | description | amount | category | status   |
            | Pizza night | 30.00  | food     | DISPUTED |
        And the expense has the following expense shares
            | payer | amount_owed | paid_amount | is_paid | vote_status |
            | Alice | 10.00       | 0.00        | False   | ACCEPTED    |
            | Bob   | 5.00        | 0.00        | False   | REJECTED    |
            | Cara  | 15.00       | 0.00        | False   | REJECTED    |
        When "Alice" edits the expense amount to "45.00"
        And "Alice" resplits the expense equally with include_self="true"
        Then the system updates that expense for "Alice" in "MapleHouse" with amount "45.00"
        And the description "Pizza night", category "food", and status "PENDING" remain unchanged
        And the expense has the following expense shares
            | payer | amount_owed | paid_amount | is_paid | vote_status |
            | Alice | 15.00       | 0.00        | False   | ACCEPTED    |
            | Bob   | 15.00       | 0.00        | False   | PENDING     |
            | Cara  | 15.00       | 0.00        | False   | PENDING     |
    
    Scenario: ID017 Former household member edits the amount of their expense and resplits it manually   (alternative flow)
        Given user "Alice" is logged in
        And "Alice" has an existing expense with the following details
            | description | amount | status  |
            | Grocery run | 60.00  | PENDING |
        And the expense has the following expense shares
            | payer | amount_owed | paid_amount | is_paid | vote_status  |
            | Bob   | 30.00       | 0.00        | False   | ACCEPTED     |
            | Cara  | 30.00       | 0.00        | False   | PENDING      |
        And "Alice" leaves household "MapleHouse"
        When "Alice" edits the expense amount to "90.00"
        And "Alice" manually updates the expense shares with the following amounts
            | payer | amount_owed |
            | Bob   | 30.00       |
            | Cara  | 60.00       |
        Then the system updates that expense for "Alice" in "MapleHouse" with amount "90.00"
        And the description "Grocery run", category "None", and status "PENDING" remain unchanged
        And the expense has the following expense shares
            | payer | amount_owed | paid_amount | is_paid | vote_status |
            | Bob   | 30.00       | 0.00        | False   | PENDING     |
            | Cara  | 60.00       | 0.00        | False   | PENDING     |
    

    Scenario: ID017 Household member attempts to edit their expense with split amounts do not equal total    (error flow)
        Given user "Alice" is logged in
        And "Alice" has an existing expense with the following details
            | description | amount | category    | status  |
            | Grocery run | 60.00  | groceries   | PENDING |
        And the expense has the following expense shares
            | payer | amount_owed | paid_amount | is_paid | vote_status  |
            | Bob   | 30.00       | 0.00        | False   | PENDING      |
            | Cara  | 30.00       | 0.00        | False   | PENDING      |
        When "Alice" edits the expense amount to "100.00"
        And "Alice" manually updates the expense shares with the following amounts
            | payer | amount_owed |
            | Bob   | 40.00       |
            | Cara  | 40.00       |
        Then the system rejects the expense modification
        And the system displays error message "Cannot update expense: Split amounts 80.00 CAD do not equal expense total 100.00 CAD"
    

    Scenario: ID017 Household member attempts to edit their expense with a negative amount    (error flow)
        Given user "Alice" is logged in
        And "Alice" has an existing expense with the following details
            | description | amount | category  | status  |
            | Grocery run | 60.00  | groceries | PENDING |
        And the expense has the following expense shares
            | payer | amount_owed | paid_amount | is_paid | vote_status |
            | Bob   | 60.00       | 0.00        | False   | PENDING     |
        When "Alice" edits the expense amount to "-20.00"
        And "Alice" manually updates the expense shares with the following amounts
            | payer | amount_owed |
            | Bob   | -20.00      |
        Then the system rejects the expense modification
        And the system displays error message "Cannot update expense: Amount must be greater than zero"

    Scenario: ID017 Household member attempts to edit their finalized expense    (error flow)
        Given user "Alice" is logged in
        And "Alice" has an existing expense with the following details
            | description | amount | category | status    |
            | Hydro Bill  | 150.00 | bills    | FINALIZED |
        And the expense has the following expense shares
            | payer | amount_owed  | paid_amount | is_paid | vote_status |
            | Alice | 100.00       | 0.00        | True    | ACCEPTED    |
            | Bob   | 25.00        | 0.00        | True    | ACCEPTED    |
            | Cara  | 25.00        | 0.00        | True    | ACCEPTED    |
        When "Alice" edits the expense amount to "180.00"
        And "Alice" manually updates the expense shares with the following amounts
            | payer | amount_owed |
            | Alice | 60.00       |
            | Bob   | 60.00       |
            | Cara  | 60.00       |
        Then the system rejects the expense modification
        And the system displays error message "Cannot update expense: Finalized expenses cannot be modified"
    

    Scenario: ID017 Household member attempts to edit their fully settled expense    (error flow)
        Given user "Alice" is logged in
        And "Alice" has an existing expense with the following details
            | description | amount | category | status        |
            | Hydro Bill  | 150.00 | bills    | FULLY_SETTLED |
        And the expense has the following expense shares
            | payer | amount_owed | paid_amount | is_paid | vote_status  |
            | Alice | 50.00       | 50.00       | True    | ACCEPTED     |
            | Bob   | 50.00       | 50.00       | True    | ACCEPTED     |
            | Cara  | 50.00       | 50.00       | True    | ACCEPTED     |
        When "Alice" edits the expense amount to "180.00"
        And "Alice" manually updates the expense shares with the following amounts
            | payer | amount_owed |
            | Alice | 60.00       |
            | Bob   | 60.00       |
            | Cara  | 60.00       |
        Then the system rejects the expense modification
        And the system displays error message "Cannot update expense: Fully settled expenses cannot be modified"