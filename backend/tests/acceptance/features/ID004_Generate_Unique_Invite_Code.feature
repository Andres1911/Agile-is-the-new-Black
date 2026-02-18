Feature: Generate Invite Code

    As a household administrator
    I would like to generate an invite code
    So that other users can join my household

    Scenario Outline: Admin Generates a Random Invite Code for Household (Normal Flow)
        Given a user with username "<UserName>" already exists in the system
        And the user "<UserName>" is an Admin of the household "<HouseholdName>"
        And the user "<UserName>" is logged in
        When the user requests to generate a random invite code for the household "<HouseholdName>"
        Then the household "<HouseholdName>" should have the invite code as its attribute
        And the message "Success" is issued

        Examples:
        | UserName | HouseholdName  |
        | Alice    | The North Star |
        | Bob      | DowntownLoft   |

    Scenario Outline: Admin Manually Enters an Invite Code (Alternative Flow)
        Given a user with username "<UserName>" already exists in the system
        And the user "<UserName>" is an Admin of the household "<HouseholdName>"
        And the user "<UserName>" is logged in
        And no other household in the system uses the invite code "<ManualCode>"
        When the manual code "<ManualCode>" is valid with at least 8 characters
        And the user requests to set the invite code to "<ManualCode>" for the household "<HouseholdName>"
        Then the household "<HouseholdName>" should have the invite code "<ManualCode>" as its attribute
        And the message "Success" is issued

        Examples:
        | UserName | HouseholdName  | ManualCode     |
        | Alice    | The North Star | MYHOUSE2024    |
        | Bob      | DowntownLoft   | LOFTSUITE123   |

    Scenario Outline: Non-Admin attempts to generate household invite code (Error Flow)
        Given a user with username "<UserName>" already exists in the system
        And the user "<UserName>" is logged in
        But the user "<UserName>" not an Admin of the household "<HouseholdName>"
        When the user requests to generate a random invite code for the household "<HouseholdName>"
        Then the invite code for household "<HouseholdName>" should not be generated
        And the error message "Permission Denied: Admin rights required" is returned

        Examples:
        | UserName | HouseholdName  |
        | Charlie  | The North Star |
        | Dave     | DowntownLoft   |
