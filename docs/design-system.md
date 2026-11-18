# Workspace design system

The founder workspace (`app/ui/static`) is organised around the founder's questions, not
around the system's components. This page records the structure, the plain-language
vocabulary and the visual tokens, so that changes stay consistent.

## Information architecture

| Destination | The founder's question | Holds |
|---|---|---|
| **Projects** (`#projects`) | Which ideas do I have, where does each stand, what next? | One card per run: plain recommendation, status, date, next action |
| **New idea** (`#brief`) | How do I start? | The founder brief in four groups, review, submit |
| **Analysis** (`#analysis`) | Is my idea good? Why? What now? | Recommendation and main reason; four questions (supports, concerns, unknown, next); how the analysis ran; the brief; the evidence; challenged assumptions; what could change the result |
| **Build & validate** (`#build`) | How do I test it, and what needs my approval? | Six-phase journey with real states; decisions waiting for the founder; validation files and recorded results |
| **History & details** (`#details`) | Can I check everything? | Run identifiers and provenance, each agent's record, the full audit trail |

The eleven earlier screen names still work as links (`#evidence/F-01`, `#decision`,
`#approvals`, ...): `ALIASES` in `views.js` maps each to the page and section that now
holds it, and the page scrolls to and focuses that section.

## Plain language, without changing meaning

Labels are a fixed mapping of recorded codes (`VERDICTS`, `RULE_REASONS`,
`STANDING_GROUPS` in `views.js`). They never upgrade a standing or change a decision,
and the exact codes stay one click away under **Technical details**.

| Recorded | Shown |
|---|---|
| `GO` | Ready for the next validation step (never "proof of demand") |
| `REPEAT` | More evidence needed (missing evidence is not evidence of absence) |
| `PIVOT` | Consider changing direction |
| `STOP` | Do not proceed under current conditions, with the kind of STOP: Policy, Pass mark missed, or Evidence against |
| `ESTABLISHED` / `PARTIAL_EVIDENCE` / `CONTRADICTED` / `NEEDS_REVIEW` / `UNSUPPORTED` / `ASSUMPTION` | Strong evidence / Partial evidence / Contradicts the idea / Needs verification / Not supported by its source / Assumption |

Superseded decisions are always shown as "Superseded (was …)", never with their old
recommendation.

## Progressive disclosure

- Collapsed by default: each finding (statement, classification, source), each challenged
  assumption, the technical details of a decision, each agent's record.
- One click reveals: the exact quotation (never rewritten), its source link, the
  attribution limits ("Original author not verified"), the classification reason, the
  finding ID and the recorded standing; the rule ID, gate trace and thresholds.

## Tokens

Defined once on `:root` in `styles.css`, with a dark theme under
`prefers-color-scheme: dark`.

- **Type**: `Inter, "Segoe UI", Arial, sans-serif` (system fonts only); 28 / 24 / 19 / 16 / 15 / 13 px.
- **Spacing**: 4, 8, 12, 16, 24, 32, 48 px (`--s1` … `--s7`).
- **Radius**: 6, 10, 14 px.
- **Status tones**: good, warn, bad, info, neutral, each a background and text pair that
  meets WCAG AA in both themes. Status is never shown by colour alone: every chip has an
  icon and words.
- **Depth**: one 1-2 px shadow in light mode, none in dark mode.

## Components

Chip (status), verdict, question card, stepper, evidence summary and bar, finding,
concern, phase card, request (approval), artifact row, validation meter, key/value list,
table, dialog, empty/loading/error states.

## Rules

- **No inline styles**: the page policy is `style-src 'self'`. Chart widths come from
  `data-flex`, `data-width` and `data-left` attributes applied through the DOM style API.
- **Performance**: no web fonts, blur, fixed backgrounds or large shadows. A
  100,000-character quotation and 5,000 findings render within the browser test budget,
  and findings are paged 50 at a time.
- **Approval**: approving opens a confirmation dialog that states what will and will not
  happen; nothing is sent until the founder confirms. Reasons are never prefilled.
- **Honesty**: every chart and count comes from backend data. Nothing shows a percentage,
  confidence or probability that the backend does not record.
