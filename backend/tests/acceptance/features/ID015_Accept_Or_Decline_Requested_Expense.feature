Feature: Accept or decline a requested expense

  As a household member
  I want to accept or decline my pending expense shares
  So that I can efficiently settle my financial obligations with other members

  Background:
    Given household "MapleHouse" exists with members
      | member |
      | Alice  |
      | Bob    |
      | Cara   |
    And user "Alice" has created the following expense
      | description | amountCAD | status  |
      | Grocery run | 60.00     | PENDING |
    And that expense has the following expense shares
      | participant | shareCAD | outstandingCAD | vote_status |
      | Bob         | 20.00    | 20.00          | PENDING     |
      | Cara        | 40.00    | 40.00          | PENDING     |

  Scenario: ID015 Household member accepts a pending expense share
    Given "Bob" is logged in
    When "Bob" "ACCEPTED" the share for "Grocery run"
    Then the status for the "Grocery run" expense should be "PENDING"
    And the expense shares for "Grocery run" should be as follows
      | participant | shareCAD | outstandingCAD | vote_status |
      | Bob         | 20.00    | 20.00          | ACCEPTED    |
      | Cara        | 40.00    | 40.00          | PENDING     |

  Scenario: ID015 Household member rejects a pending expense share
    Given "Cara" is logged in
    When "Cara" "REJECTED" the share for "Grocery run"
    Then the status for the "Grocery run" expense should be "DISPUTED"
    And the expense shares for "Grocery run" should be as follows
      | participant | shareCAD | outstandingCAD | vote_status |
      | Bob         | 20.00    | 20.00          | PENDING     |
      | Cara        | 40.00    | 40.00          | REJECTED    |

  Scenario: ID015 All household members accept their pending expense shares
    Given "Bob" has "ACCEPTED" share for "Grocery run"
    And "Cara" is logged in
    When "Cara" "ACCEPTED" the share for "Grocery run"
    Then the status for the "Grocery run" expense should be "FINALIZED"
    And the expense shares for "Grocery run" should be as follows
      | participant | shareCAD | outstandingCAD | vote_status |
      | Bob         | 20.00    | 20.00          | ACCEPTED    |
      | Cara        | 40.00    | 40.00          | ACCEPTED    |

  Scenario: ID015 Household member attempts to accept a previously rejected share
    Given "Cara" has "REJECTED" share for "Grocery run"
    And "Cara" is logged in
    When "Cara" attempts to "ACCEPTED" the share for "Grocery run"
    Then the system should return an error message "Cannot accept a rejected expense"
    And the status for the "Grocery run" expense should be "DISPUTED"
    And the expense shares for "Grocery run" should be as follows
      | participant | shareCAD | outstandingCAD | vote_status |
      | Bob         | 20.00    | 20.00          | PENDING     |
      | Cara        | 40.00    | 40.00          | REJECTED    |

  Scenario: ID015 Household member attempts to reject a previously accepted share
    Given "Bob" has "ACCEPTED" share for "Grocery run"
    And "Bob" is logged in
    When "Bob" attempts to "REJECTED" the share for "Grocery run"
    Then the system should return an error message "Cannot reject an already accepted expense"
    And the status for the "Grocery run" expense should be "PENDING"
    And the expense shares for "Grocery run" should be as follows
      | participant | shareCAD | outstandingCAD | vote_status |
      | Bob         | 20.00    | 20.00          | ACCEPTED    |
      | Cara        | 40.00    | 40.00          | PENDING     |