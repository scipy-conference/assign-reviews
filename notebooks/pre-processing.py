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
#     version: 3.12.1
# ---

# %%
import duckdb
from IPython import display

# Raw data to import
raw_files = dict(
    scipy_reviewers="../data/scipy_reviewers.csv",  # people who signed up as reviewers
    pretalx_sessions="../data/sessions.csv",  # all proposal exported from pretalx
    pretalx_speakers="../data/speakers.csv",  # all speakers exported from pretalx
    pretalx_reviewers="../data/pretalx_reviewers.csv",  # all reviewers copy-pasted from pretalx
    coi_reviewers="../data/scipy_coi_export.csv",  # all responses to the coi form
    coi_authors="../data/coi_authors.csv",  # copy pasted values of author names from coi form
    tracks="../data/tracks.csv",  # manually entered track IDs
)

# Output
database_file = "../data/assign_reviews.db"

# %%
con = duckdb.connect(database_file)


# %%
def create_and_show_table(file_name, table_name, show=True):
    con.sql(f'create or replace table {table_name} as select * from read_csv("{file_name}", header=true)')
    if show is True:
        return con.sql(f"table {table_name}")


# %%
for table_name, file_name in raw_files.items():
    print(table_name)
    display.display(create_and_show_table(file_name, table_name).df())
    print("\n")

# %%
con.sql(
    """
table tracks
"""
)

# %%
con.sql(
    """
with dupes as
    (
        select
            name,
            num,
            email
        from
            (
                select
                    name,
                    count(*) as num,
                    string_agg(Email) as email
                from
                    scipy_reviewers
                    group by Name
            )
            where
                num>1
        )

select * from dupes
"""
).df()

# %%
con.sql(
    """
select count(*) from scipy_reviewers
"""
)

# %%
con.sql(
    """
select count(*) from pretalx_reviewers
"""
)

# %%
con.sql(
    """
select count(*) from coi_reviewers
"""
)

# %% [markdown]
# This is a table with all reviewers who
# 1. signed up
# 2. created an account on pretalx
# 3. submitted the COI form

# %%
con.sql(
    """
create or replace table reviewers as
    select
        scipy_reviewers.Name as name,
        scipy_reviewers.Email as email,
        \"Track(s) to review for (check all that apply)\" as tracks,
        \"Mark the speaker(s) or company/organization/affiliation(s) that could pose a conflict of interest\" as coi
    from scipy_reviewers
    join pretalx_reviewers on scipy_reviewers.Email = pretalx_reviewers.Email
    join coi_reviewers on coi_reviewers.Email = pretalx_reviewers.Email
"""
)

df = con.sql("select distinct * from reviewers").df()
num_reviewers = len(df)
df

# %% [markdown]
# Reviewers who signed up for pretalx but did not fill in COI

# %%
con = duckdb.connect(database_file)

# %%
df = con.sql(
    "select * from pretalx_reviewers anti join coi_reviewers on pretalx_reviewers.Email = coi_reviewers.Email"
).df()
num_pretalx_no_coi = len(df)
df

# %%
# df.to_csv("input/signed_up_for_pretalx_no_coi.csv")

# %% [markdown]
# Reviewers who filled in COI but did not sign up for pretalx

# %%
df = con.sql(
    "select * from coi_reviewers anti join pretalx_reviewers on coi_reviewers.Email = pretalx_reviewers.Email"
).df()
num_coi_no_pretalx = len(df)
df

# %%
# df.to_csv("input/submitted_coi_no_pretalx.csv")

# %% [markdown]
# People who signed up as reviewer

# %%
df = con.sql(
    """
select distinct * from scipy_reviewers
"""
).df()
num_signed_up = len(df)
df

# %% [markdown]
# People who signed up as reviewer and signed up for pretalx and submitted COI but used different email addresses

# %%
df = con.sql(
    """
create or replace table reviewers_with_email_typos as
(with no_coi as
(select * from pretalx_reviewers anti join coi_reviewers on pretalx_reviewers.Email = coi_reviewers.Email),
no_pretalx as
(select * from coi_reviewers anti join pretalx_reviewers on coi_reviewers.Email = pretalx_reviewers.Email)
select distinct scipy_reviewers.Name, scipy_reviewers.Email, no_pretalx.Email as no_pretalx_email, no_coi.email as no_coi_email from scipy_reviewers
join no_coi on no_coi.Name = scipy_reviewers.Name
join no_pretalx on no_pretalx.Name = no_coi.Name)
"""  # noqa: E501
)
df = con.sql("table reviewers_with_email_typos").df()
num_typos = len(df)
df

# %% [markdown]
# People who signed up as reviewer and signed up for pretalx and submitted COI but used different names

# %%
df = con.sql(
    """
(with no_coi as
(select * from pretalx_reviewers anti join coi_reviewers on pretalx_reviewers.Email = coi_reviewers.Email),
no_pretalx as
(select * from coi_reviewers anti join pretalx_reviewers on coi_reviewers.Email = pretalx_reviewers.Email)
select distinct scipy_reviewers.Name, scipy_reviewers.Email, no_pretalx.Name as no_pretalx_name, no_coi.name as no_coi_name from scipy_reviewers
join no_coi on no_coi.Email = scipy_reviewers.Email
join no_pretalx on no_pretalx.Email = no_coi.Email)
"""  # noqa: E501
).df()
num_typos_name = len(df)
df

# %%
# df.to_csv("input/reviewers_multi_email.csv")

# %% [markdown]
# People who signed up as reviewer and didn't sign up for pretalx nor submitted COI

# %%
df = con.sql(
    """
(with no_coi as
(select * from pretalx_reviewers anti join coi_reviewers on pretalx_reviewers.Email = coi_reviewers.Email),
no_pretalx as
(select * from coi_reviewers anti join pretalx_reviewers on coi_reviewers.Email = pretalx_reviewers.Email)
select distinct scipy_reviewers.Name, scipy_reviewers.Email from scipy_reviewers
anti join reviewers on reviewers.Name = scipy_reviewers.Name
anti join no_coi on no_coi.Name = scipy_reviewers.Name
anti join no_pretalx on no_pretalx.Name = scipy_reviewers.Name)
"""
).df()
df

# %%
df = con.sql(
    """
select distinct * from scipy_reviewers
anti join reviewers on scipy_reviewers.Email = reviewers.email
"""
).df()
num_no_show = len(df)
df

# %%
# df.to_csv("input/all_reviewers_without_assignments.csv")

# %%
num_no_show = num_signed_up - num_reviewers - num_pretalx_no_coi - num_coi_no_pretalx
num_partial = sum([num_pretalx_no_coi, num_coi_no_pretalx, num_no_show])
num_reviewers, num_signed_up, num_pretalx_no_coi, num_coi_no_pretalx, num_no_show, num_partial

# %%
con.sql("select * from reviewers where instr(name, 'eli')")

# %%
# con.sql("table reviewers").df().to_csv("input/reviewers_to_assign_with_name.csv")

# %%
con.sql("select * from reviewers where instr(Name, 'Wu')")

# %%
sum([num_pretalx_no_coi, num_coi_no_pretalx, num_reviewers])

# %%
con.sql(
    """
with dupes as
    (
        select
            *
        from
            (
                select
                    name,
                    count(*) as num,
                    string_agg(email) as email,
                    string_agg(tracks) as tracks,
                    string_agg(coi) as coi
                from
                    reviewers
                    group by name
            )
            where
                num>1
        )

select * from dupes
"""
).df().T.to_json()

# %%
con.sql("create or replace table reviewers as (select distinct * from reviewers)")

# %%
con.sql(
    """
create or replace table reviewers_with_tracks as
with reviewers_no_dupes as (select distinct * from reviewers)
select reviewers_no_dupes.name, email, list(tracks.name) as tracks, list(tracks.track_id) as track_ids from reviewers_no_dupes
    join tracks on instr(reviewers_no_dupes.tracks, tracks.name)
    group by reviewers_no_dupes.name, email
"""  # noqa: E501
)

con.sql("select distinct * from reviewers_with_tracks")

# %%
con.sql('select ID as submission_id, "Speaker IDs" as speaker_ids from pretalx_sessions')

# %%
con.sql(
    """
create or replace table reviewers_with_coi as

with submissions_with_authors as (
    select
        ID as submission_id,
        \"Speaker IDs\" as speaker_ids
    from
        pretalx_sessions
)
select
    reviewers.name,
    reviewers.email,
    list(pretalx_speakers.Name) as speakers,
    list(pretalx_speakers.ID) AS speaker_ids,
    list(submissions_with_authors.submission_id) as submission_ids
from
    reviewers
    left join coi_authors on instr(coi, coi_authors.author)
    left join pretalx_speakers on contains(coi_authors.author, pretalx_speakers.Name)
    left join submissions_with_authors on contains(submissions_with_authors.speaker_ids, pretalx_speakers.ID)
group by reviewers.name, reviewers.email
order by reviewers.name
"""
)

con.sql("table reviewers_with_coi")

# %%
con.sql(
    """
with reviewers_with_coi_pre as (
    select name, email, author
    from reviewers
    join coi_authors on instr(coi, coi_authors.author)
)
select count(*), author from reviewers_with_coi_pre anti join pretalx_speakers on contains(reviewers_with_coi_pre.author, pretalx_speakers.Name) group by author
"""  # noqa: E501
)

# %%
con.sql("table reviewers_with_tracks").df()

# %%
con.sql("select email as reviewer_id, list(track_id) as tracks from reviewers_with_tracks group by email")

# %% [markdown]
# # Final tables for script

# %% [markdown]
# ## reviewers_to_assign

# %%
con.sql(
    """
create or replace table reviewers_to_assign as
select
    reviewers_with_coi.email as reviewer_id,
    reviewers_with_tracks.track_ids as tracks,
    reviewers_with_coi.submission_ids as conflicts_submission_ids
from reviewers_with_coi
join reviewers_with_tracks on reviewers_with_tracks.email = reviewers_with_coi.email
"""
)

con.sql("table reviewers_to_assign").df()

# %%
# con.sql("table reviewers_to_assign").df().to_csv("input/reviewers_to_assign.csv")

# %% [markdown]
# ## submissions_to_assign

# %%
con.sql(
    """
create or replace table submissions_to_assign as
select
    ID as submission_id,
    string_split(\"Speaker IDs\", '\n') as author_ids,
    track_id as track
from pretalx_sessions
    join tracks on pretalx_sessions.Track = tracks.name
"""
)

con.sql("table submissions_to_assign").df()

# %%
# con.sql("table submissions_to_assign").df().to_csv("input/submissions_to_assign.csv")

# %%
# con.sql("table submissions_to_assign").df().author_ids.iloc[1]

# %%
con.close()

# %%
