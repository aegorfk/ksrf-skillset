## ADDED Requirements

### Requirement: Intake derives retrieval identifiers from supplied materials

The skill SHALL start autonomous official retrieval when a user supplies a court act, case number, case link or UID and asks for case assessment or missing acts. It SHALL extract available identifiers itself.

#### Scenario: Only a higher-court PDF is supplied
- **WHEN** the PDF identifies earlier courts, case numbers or parties without a separately typed UID
- **THEN** the skill starts the official retrieval route instead of requesting those earlier acts immediately.

### Requirement: Discovery retains identifiers and verifies case identity

The skill SHALL preserve raw identifiers, use independent observed search fields and record any verified aliases and unresolved conflicts.

#### Scenario: UID year conflicts with the underlying card
- **WHEN** a supplied copy has a different UID year from a card found by case number and parties
- **THEN** the skill preserves both values and verifies the relationship using court, case number, parties, dates and cross-instance links.

#### Scenario: A number query matches another procedural list
- **WHEN** substring or padded-number search returns a similar number in a different case type
- **THEN** the skill rejects that candidate unless independent identity fields establish the requested case.

### Requirement: Retrieval follows cards to full source bytes

The skill SHALL inspect the verified card's document inventory, related instances and available official representations, and SHALL distinguish the date of adjudication from preparation and publication dates.

#### Scenario: Reasons were prepared later
- **WHEN** the hearing-date decision row has no attachment but a later reasoned-decision row has a file
- **THEN** the skill downloads and reads that file and records both dates separately.

#### Scenario: Card exists without a published full act
- **WHEN** no full text is available after the relevant official card and alternatives are checked
- **THEN** the card remains card-only and the skill records the specific missing act and retrieval attempts.

### Requirement: Client failure does not establish source absence

The skill SHALL distinguish transport-specific failures, protection pages, parsing failures and verified publication status. It SHALL use a bounded independent available transport or browser route before declaring an official retrieval gap.

#### Scenario: Python TLS failure with a usable system client
- **WHEN** one client's trust store fails but a system client with certificate verification or a browser retrieves the same official document
- **THEN** the skill records both attempts, validates the successful bytes and does not disable TLS verification.

#### Scenario: Access remains blocked
- **WHEN** available bounded routes encounter a CAPTCHA or other unresolved restriction
- **THEN** the skill retains an access-gap status and does not infer that the court act is absent.

### Requirement: Case evidence and methodological publication remain separate

The skill SHALL retain source URLs, transport, timestamps, format, hashes, identity checks and extraction lineage locally. Public skill changes SHALL contain reusable method and synthetic cases without private documents or reconstructive derivatives.

#### Scenario: A later review repeats the same matter
- **WHEN** local receipts or prior official links are available
- **THEN** the skill checks those artifacts and revalidates the relevant source instead of discarding them because a general search returns nothing.

### Requirement: Plugin delivery preserves the corrected source

When this correction is delivered through the applicant plugin, the release SHALL rebuild from the verified published canonical source and verify the installed distribution's source SHA and changed skill bytes.

#### Scenario: Installed package still contains the older route
- **WHEN** the global skills have been corrected but the installed plugin is from an older source
- **THEN** the patch release refreshes the generated marketplace and supported installation, and reports any need for a new task to load its instructions.
