# Automation Backlog For KSRF Argument Patterns

These are implementation ideas to support pattern use on new cases.

## practice-split

Build a lower-court practice split finder:

- input: target norm, issue phrase, party role, time window, court system;
- fetch: cassation and appeal acts;
- extract holdings on the norm;
- cluster holdings into compatible/incompatible approaches;
- output: split table with citations, court/date/case number, and quote windows.

## legal-certainty

Build a norm ambiguity detector:

- detect undefined evaluative terms;
- compare statutory text with judicial criteria actually used;
- flag competing tests and missing thresholds;
- produce "predictability risk" memo.

## constitutional-meaning

Build a constitutional meaning mapper:

- input ordinary-court interpretation;
- retrieve KSRF positions on the norm or adjacent institutions;
- propose constitutional-compatible interpretation variants;
- mark which variants save the norm and which imply unconstitutionality.

## proportionality and interest-balance

Build a proportionality worksheet:

- right affected;
- public aim;
- measure;
- suitability;
- necessity / less restrictive alternatives;
- burden distribution;
- compensation and procedural safeguards.

## effective-remedy and procedural-guarantees

Build an ignored-dovod checker:

- parse the complaint/appeal/cassation arguments;
- parse court acts;
- align each argument to a court response;
- flag omitted, circular, or purely formal responses.

## legitimate-expectations and retroactivity

Build a timeline checker:

- event creating right/obligation;
- law or interpretation changes;
- court act applying new rule;
- whether the person could foresee consequences;
- whether transition rules existed.

## non-mechanical-application and liability-fairness

Build an individualization checker:

- extract factual circumstances relevant to sanction, liability, access, status, or benefit;
- compare them with the court's reasoning;
- flag automatic application, missing proportionality, and ignored mitigating factors.

## property-compensation

Build a deprivation/compensation checker:

- identify property interest;
- classify interference: deprivation, restriction, non-payment, recovery, expropriation;
- check public aim, procedure, compensation, good faith, limitation period.

## reconsideration-execution

Build a KSRF aftermath planner:

- decide whether KSRF ruling creates a route to reconsideration;
- identify affected cases beyond named applicants;
- generate procedural route and evidence list.

