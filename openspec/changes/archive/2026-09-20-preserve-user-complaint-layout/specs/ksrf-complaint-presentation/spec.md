## ADDED Requirements

### Requirement: Latest user revision controls editorial work
The drafting workflow SHALL use the latest user-designated edited document as the editorial baseline and preserve deliberate paragraph divisions, selected remedies, citations and deletions within the authorized scope. It SHALL NOT silently restore deleted material from an older draft or impose a fixed number of requests. Unresolved required particulars SHALL remain in the companion review without being marked verified or ready for filing.

#### Scenario: User removes a request and a formal particular
- **WHEN** the user supplies an edited DOCX that removes an alternative request and a required particular
- **THEN** the revision preserves the selected requests, records the formal gap separately and does not silently restore either deletion from an older template.

### Requirement: Case-specific source selection
Court-facing source selection SHALL follow the user's explicit restrictions for the current document. Such restrictions SHALL NOT become universal prohibitions or excuse a false attribution or omission from the internal source/adverse assessment. An unresolved support problem SHALL remain in the separate review.

#### Scenario: User limits one category of citations
- **WHEN** the user restricts which individual decisions may appear in one complaint
- **THEN** the editor respects that scope, preserves independently allowed categories and does not apply the restriction automatically to other complaints.
