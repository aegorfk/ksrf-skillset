## ADDED Requirements

### Requirement: Hypothesis finding references SHALL respect explicit finding membership

Для каждого `finding_id` в `ArgumentHypothesis.supporting_finding_ids` либо `adverse_finding_ids` валидатор SHALL проверять не только глобальное существование finding, но и присутствие текущего непустого строкового `hypothesis_id` в `ResearchFinding.hypothesis_ids`. Нестроковый или пустой `hypothesis_id` SHALL NOT отключать проверку. Необъявленный перенос finding между гипотезами SHALL fail closed.

#### Scenario: Finding bound only to another hypothesis

- **WHEN** F1 содержит `hypothesis_ids=[H1]`, а H2 ссылается на F1
- **THEN** валидатор возвращает blocking error для H2→F1
- **AND** F1 SHALL NOT считаться evidence H2

#### Scenario: Finding bound to the referencing hypothesis

- **WHEN** F1 содержит H1 в `hypothesis_ids`, а H1 ссылается на F1
- **THEN** membership-проверка проходит

#### Scenario: Finding explicitly shared by two hypotheses

- **WHEN** F1 содержит `hypothesis_ids=[H1,H2]`, и обе гипотезы ссылаются на F1
- **THEN** membership-проверка проходит для обеих
- **AND** валидатор SHALL NOT требовать обратного exact-set равенства или выводить relation polarity
