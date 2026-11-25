## MODIFIED Requirements

### Requirement: Planning parameters
The `planning` package SHALL keep one record of planning parameters, with a change history, that staff edit in the admin:

- `certainty`, the probability `p` with which a stock is to last its runway, from 0.5 to 0.999, default 0.95;
- `buffer_days`, the time from a synthesis's end until its product can be delivered, for QC, filling and the unforeseen, from 0 to 365, default 28;
- `default_synthesis_days`, from 1 to 730, default 21;
- `history_quarters`, from 4 to 40, default 12;
- `min_orders`, from 3 to 100, default 6;
- `high_days` and `medium_days`, the priority bands, `0 ≤ high_days < medium_days`, defaults 14 and 56;
- `target_days`, from 30 to 1095, default 365.

When no record exists, the defaults apply.

#### Scenario: Defaults
- **WHEN** no parameter record exists
- **THEN** the forecast uses 0.95, 28, 21, 12, 6, 14, 56 and 365

#### Scenario: Bands out of order
- **WHEN** a staff user saves `high_days` 60 and `medium_days` 56
- **THEN** the admin shows an error and keeps the earlier record
