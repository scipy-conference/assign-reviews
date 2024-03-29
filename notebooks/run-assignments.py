# ---
# jupyter:
#   jupytext:
#     notebook_metadata_filter: all,-jupytext.text_representation.jupytext_version
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
#   language_info:
#     codemirror_mode:
#       name: ipython
#       version: 3
#     file_extension: .py
#     mimetype: text/x-python
#     name: python
#     nbconvert_exporter: python
#     pygments_lexer: ipython3
#     version: 3.12.2
# ---

# %%
####################
## ASSIGN REVIEWS ##
####################
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.append("..")
from assign_reviews import format_and_output_result, solve_milp

# %% [markdown]
# # Start script

# %%
output_dir = Path().cwd() / "output"
output_dir.mkdir(exist_ok=True)

# %%
ASSIGN_TUTORIALS_TO_ANYONE = False
TUTORIAL_COEFF = 0.8

DEBUG = True

database_file = "../data/assign_reviews.db"
con = duckdb.connect(database_file)
df_submissions = con.sql("table submissions_to_assign").df()
df_reviewers = con.sql("table reviewers_to_assign").df()

df_submissions = df_submissions.assign(assigned_reviewer_ids=[[]] * len(df_submissions))
df_reviewers = df_reviewers.assign(assigned_submission_ids=[[]] * len(df_reviewers))

len(df_submissions), len(df_reviewers)

# %%
df_submissions[df_submissions.track == "TUT"]

# %% [markdown]
# ## Step 1. Assign tutorial reviewers

# %%
MIN_TUTORIALS_PER_PERSON = 0
MAX_TUTORIALS_PER_PERSON = 5
MIN_REVIEWERS_PER_TUTORIAL = 3
MAX_REVIEWERS_PER_TUTORIAL = 4

df_submissions_tutorials = df_submissions[df_submissions.track == "TUT"]

solution = solve_milp(
    df_reviewers,
    df_submissions_tutorials,
    MIN_TUTORIALS_PER_PERSON,
    MAX_TUTORIALS_PER_PERSON,
    MIN_REVIEWERS_PER_TUTORIAL,
    MAX_REVIEWERS_PER_TUTORIAL,
    TUTORIAL_COEFF,
    ASSIGN_TUTORIALS_TO_ANYONE,
)
reviewers, submissions = format_and_output_result(df_reviewers, df_submissions_tutorials, solution, post_fix="00")

# %%
df = pd.DataFrame(reviewers)
df

# %%
df_reviewers_with_tut = df_reviewers.assign(assigned_submission_ids=df.assigned_submission_ids)
df_reviewers_with_tut

# %%
con.sql("select * from df_reviewers_with_tut")

# %%
con.sql("create or replace table reviewer_assignments_00 as select * from df_reviewers_with_tut")

# %%
df = pd.DataFrame(submissions)
df

# %%
con.sql(
    """
create or replace table submission_assignments_00 as
select df_submissions.submission_id, df_submissions.author_ids, df_submissions.track,
list_concat(df_submissions.assigned_reviewer_ids, df.assigned_reviewer_ids) as assigned_reviewer_ids
from df_submissions
left join df on df.submission_id = df_submissions.submission_id
"""
)
con.sql("table submission_assignments_00")

# %% [markdown]
# ## Step 2. Assign talk reviewers

# %%
df_reviewers_with_tut[df_reviewers_with_tut.assigned_submission_ids.apply(len) == 0]

# %%
MIN_REVIEWS_PER_PERSON = 5
MAX_REVIEWS_PER_PERSON = 9
MIN_REVIEWERS_PER_SUBMISSION = 2
MAX_REVIEWERS_PER_SUBMISSION = 4

df_reviewers_no_submissions = df_reviewers_with_tut[df_reviewers_with_tut.assigned_submission_ids.apply(len) == 0]
df_submissions_no_tutorials = df_submissions[df_submissions.track != "TUT"]

solution = solve_milp(
    df_reviewers_no_submissions,
    df_submissions_no_tutorials,
    MIN_REVIEWS_PER_PERSON,
    MAX_REVIEWS_PER_PERSON,
    MIN_REVIEWERS_PER_SUBMISSION,
    MAX_REVIEWERS_PER_SUBMISSION,
    TUTORIAL_COEFF,
    ASSIGN_TUTORIALS_TO_ANYONE,
)
if solution is not None:
    reviewers, submissions = format_and_output_result(
        df_reviewers_no_submissions, df_submissions_no_tutorials, solution, post_fix="01"
    )

# %%
df_reviewers_with_tut

# %%
df = pd.DataFrame(reviewers)[["reviewer_id", "assigned_submission_ids"]]

# %%
df

# %%
con.sql(
    """
create or replace table reviewer_assignments_01 as
select
    df_reviewers_with_tut.reviewer_id, tracks, conflicts_submission_ids,
    list_concat(df_reviewers_with_tut.assigned_submission_ids, df.assigned_submission_ids) as assigned_submission_ids
from df_reviewers_with_tut
left join df on df.reviewer_id = df_reviewers_with_tut.reviewer_id
"""
)
con.sql("table reviewer_assignments_01")

# %%
df = pd.DataFrame(submissions)
df

# %%
con.sql(
    """
create or replace table submission_assignments_01 as
select submission_assignments_00.submission_id, submission_assignments_00.author_ids, submission_assignments_00.track,
list_concat(submission_assignments_00.assigned_reviewer_ids, df.assigned_reviewer_ids) as assigned_reviewer_ids
from submission_assignments_00
left join df on df.submission_id = submission_assignments_00.submission_id
"""
)
con.sql("table submission_assignments_01")

# %%
df = pd.DataFrame(submissions)
df = df.assign(num_reviewers=df.assigned_reviewer_ids.apply(len))
df[df.num_reviewers > 2]
df[df.num_reviewers == 2]

# %% [markdown]
# ## Step 3. Assign talks to tutorial reviewers

# %%
df = pd.DataFrame(submissions)
df = df.assign(num_reviewers=df.assigned_reviewer_ids.apply(len))
df_submissions_few_reviewers = df[df.num_reviewers == 2]

# %%
MIN_REVIEWS_PER_PERSON = 0
MAX_REVIEWS_PER_PERSON = 4
MIN_REVIEWERS_PER_SUBMISSION = 1
MAX_REVIEWERS_PER_SUBMISSION = 2

df_reviewers_only_tut = df_reviewers_with_tut[df_reviewers_with_tut.assigned_submission_ids.apply(len) > 0]

solution = solve_milp(
    df_reviewers_only_tut,
    df_submissions_few_reviewers,
    MIN_REVIEWS_PER_PERSON,
    MAX_REVIEWS_PER_PERSON,
    MIN_REVIEWERS_PER_SUBMISSION,
    MAX_REVIEWERS_PER_SUBMISSION,
    TUTORIAL_COEFF,
    ASSIGN_TUTORIALS_TO_ANYONE,
)

if solution is not None:
    reviewers, submissions = format_and_output_result(
        df_reviewers_only_tut, df_submissions_few_reviewers, solution, post_fix="02"
    )

# %%
df = pd.DataFrame(submissions)
df = df.assign(num_reviewers=df.assigned_reviewer_ids.apply(len))
df

# %%
df = pd.DataFrame(reviewers)
df = df[["reviewer_id", "assigned_submission_ids"]]
df

# %%
con.sql(
    """
create or replace table reviewer_assignments_02 as
select
    reviewer_assignments_01.reviewer_id, tracks, conflicts_submission_ids,
    list_concat(reviewer_assignments_01.assigned_submission_ids, df.assigned_submission_ids) as assigned_submission_ids
from reviewer_assignments_01
left join df on df.reviewer_id = reviewer_assignments_01.reviewer_id
"""
)
con.sql("table reviewer_assignments_02")

# %%
con.sql(
    "select count(*), string_agg(reviewer_id), len(assigned_submission_ids) as num_submissions from reviewer_assignments_02 group by num_submissions"  # noqa: E501
)

# %%
df = pd.DataFrame(submissions)
df

# %%
con.sql(
    """
create or replace table submission_assignments_02 as
select submission_assignments_01.submission_id, submission_assignments_01.author_ids, submission_assignments_01.track,
list_concat(submission_assignments_01.assigned_reviewer_ids, df.assigned_reviewer_ids) as assigned_reviewer_ids
from submission_assignments_01
left join df on df.submission_id = submission_assignments_01.submission_id
"""
)
con.sql("table submission_assignments_02")

# %% [markdown]
# ## Final counts/checks

# %% [markdown]
# All submissions have at least 3 reviewers

# %%
con.sql(
    """
select string_agg(submission_id), count(track), len(assigned_reviewer_ids) from submission_assignments_02 group by len(assigned_reviewer_ids)
"""  # noqa: E501
)

# %% [markdown]
# Step 1: Only tutorial assignments

# %%
con.sql(
    """
select string_agg(reviewer_id), count(reviewer_id), string_agg(tracks), len(assigned_submission_ids) from reviewer_assignments_00 group by len(assigned_submission_ids)
"""  # noqa: E501
)

# %% [markdown]
# Step 2: Add talks assignments

# %%
con.sql(
    """
select string_agg(reviewer_id), count(reviewer_id), string_agg(tracks), len(assigned_submission_ids) from reviewer_assignments_01 group by len(assigned_submission_ids)
"""  # noqa: E501
)

# %% [markdown]
# Step 3: Assign talks to tutorial reviewers

# %%
con.sql(
    """
select string_agg(reviewer_id), count(reviewer_id), string_agg(tracks), len(assigned_submission_ids) from reviewer_assignments_02 group by len(assigned_submission_ids)
"""  # noqa: E501
)

# %%
con.close()

# %% [markdown]
# ## Final export

# %%
database_file = "../data/assign_reviews.db"
con = duckdb.connect(database_file)

# %%
reviewer_assignments_final = {
    item["reviewer_id"]: item["assigned_submission_ids"].tolist()
    for item in con.sql("table reviewer_assignments_02")
    .df()[["reviewer_id", "assigned_submission_ids"]]
    .to_dict("records")
}
with open("output/reviewer-assignments.json", "w") as fp:
    fp.write(json.dumps(reviewer_assignments_final, indent=4))

# %%
con.close()
