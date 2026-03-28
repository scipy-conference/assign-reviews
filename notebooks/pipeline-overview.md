# SciPy Review Assignment Pipeline

This document describes the two main scripts in the `notebooks/` directory that
together form the review-assignment pipeline for SciPy conference proposals.

---

## 1. Pre-processing (`pre-processing-ibis.py`)

This script reads raw CSV exports from multiple sources, cleans and joins them,
and produces two final tables (`reviewers_to_assign` and `submissions_to_assign`)
in a DuckDB database (`data/assign_reviews.db`).

### Input files

| File | Description |
|---|---|
| `scipy_reviewers.csv` | People who signed up as reviewers |
| `sessions.csv` | All proposals exported from Pretalx |
| `speakers.csv` | All speakers exported from Pretalx |
| `pretalx_reviewers.csv` | Reviewers copy-pasted from Pretalx |
| `scipy_coi_export.csv` | Responses to the conflict-of-interest form |
| `coi_authors.csv` | Author names from the COI form |
| `tracks.csv` | Manual mapping of track IDs to track names |

### What it does

1. **Import and normalize** -- Reads each CSV, snake-cases column names, and
   lowercases all string columns for consistent matching.
2. **Join reviewer data** -- Joins the SciPy reviewer sign-up list with Pretalx
   reviewer accounts and COI form responses by email, producing a unified
   `reviewers` table.
3. **Data-quality checks** -- Identifies reviewers with email typos, name
   variations across sources, and people who completed some but not all sign-up
   steps ("ghosted" reviewers).
4. **Map reviewers to tracks** -- Joins reviewers with the `tracks` table to
   produce `reviewers_with_tracks` (each reviewer's list of track IDs they can
   review for).
5. **Map reviewers to conflicts** -- Matches COI form responses against speaker
   names and submission IDs to produce `reviewers_with_coi` (each reviewer's
   list of conflicted submission IDs).
6. **Build final tables** -- Combines tracks and COI data into
   `reviewers_to_assign` (columns: `reviewer_id`, `tracks`,
   `conflicts_submission_ids`) and builds `submissions_to_assign` (columns:
   `submission_id`, `author_ids`, `track`).

---

## 1b. Pre-processing — non-Ibis variant (`pre-processing.py`)

Same inputs, same output tables, same workflow as the Ibis version but written
in **raw DuckDB SQL** (~430 lines vs ~220). Key differences:

- Uses pure SQL strings instead of Ibis expressions.
- Manual column-name cleaning (`REPLACE`/`TRIM`) instead of `rename("snake_case")`.
- Wraps join predicates in explicit `lower()` calls (the Ibis version sometimes
  omits these, relying on columns being lowercased at import).
- More verbose inline validation: displays intermediate dataframes, duplicate
  checks, email mismatches, and ghosted-reviewer diagnostics at each step.

---

## 2. Running assignments (`run-assignments.py`)

This script reads the two tables produced by pre-processing and runs a
Mixed-Integer Linear Programming (MILP) solver in three successive steps to
assign reviewers to submissions. Each step writes intermediate results to both
the DuckDB database and JSON files in the `output/` directory.

### The three assignment steps

| Step | Suffix | What it does |
|---|---|---|
| Step 1 | `00` | Assigns **tutorials** to reviewers (3-4 reviewers per tutorial, up to 5 tutorials per reviewer). |
| Step 2 | `01` | Assigns **talks** to reviewers who received **no tutorials** in Step 1 (5-9 reviews per person, 2-4 reviewers per talk). |
| Step 3 | `02` | Assigns remaining under-reviewed talks to **tutorial reviewers** from Step 1 (up to 4 extra reviews per person, targeting talks that only got 2 reviewers). |

### Output files

Each step produces three JSON files via `format_and_output_result`:

| File pattern | Contents |
|---|---|
| `review-assignments{NN}.json` | `reviewer_id` -> list of submission IDs assigned **in that step** |
| `review-assignments-debug{NN}.json` | `reviewer_id` -> list of booleans (`true` = tutorial, `false` = talk) for each assignment in that step. Only written when `DEBUG = True`. |
| `submission-assignments{NN}.json` | `submission_id` -> list of reviewer IDs assigned **in that step** |

Where `NN` is `00`, `01`, or `02` matching the step number.

After all three steps, the script writes one final file:

| File | Contents |
|---|---|
| `reviewer-assignments.json` | The **final combined** mapping of `reviewer_id` -> all assigned submission IDs across all steps. This is the file you would use downstream. |

### Summary

- The `00`/`01`/`02` files are **per-step snapshots** useful for debugging and
  understanding how assignments were distributed.
- `reviewer-assignments.json` is the **final consolidated output**.
- The debug files let you verify properties like how many tutorials vs. talks
  each reviewer was assigned.
