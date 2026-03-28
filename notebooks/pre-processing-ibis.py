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
from pathlib import Path

import ibis
import ibis.selectors as s
from ibis import _

# %%
ibis.options.interactive = True

# %%
data_dir = Path(__file__).resolve().parent.parent / "data"

con = ibis.duckdb.connect(data_dir / "assign_reviews.db")

# Raw data to import
raw_files = dict(
    scipy_reviewers=data_dir / "scipy_reviewers.csv",  # people who signed up as reviewers
    pretalx_sessions=data_dir / "sessions.csv",  # all proposal exported from pretalx
    pretalx_speakers=data_dir / "speakers.csv",  # all speakers exported from pretalx
    pretalx_reviewers=data_dir / "pretalx_reviewers.csv",  # all reviewers copy-pasted from pretalx
    coi_reviewers=data_dir / "scipy_coi_export.csv",  # all responses to the coi form
    coi_authors=data_dir / "coi_authors.csv",  # copy pasted values of author names from coi form
    tracks=data_dir / "tracks.csv",  # manual mapping of arbitrary track id to track names
)


# %% [markdown]
# Read in the CSVs (creates a view), then normalize column names and lowercase all string columns
# Then write the tables out to the DuckDB database so that some of the inline SQL below can access them


# %%
def _process_strings(table):
    return table.rename("snake_case").mutate(s.across(s.of_type("str"), _.lower()))


for table_name, file_name in raw_files.items():
    t = con.read_csv(file_name, strict_mode=False)
    t = _process_strings(t)
    con.create_table(table_name, t, overwrite=True)

# %% [markdown]
# Load all the tables into variables

# %%
coi_authors = con.tables.coi_authors
coi_reviewers = con.tables.coi_reviewers
pretalx_reviewers = con.tables.pretalx_reviewers
pretalx_sessions = con.tables.pretalx_sessions
pretalx_speakers = con.tables.pretalx_speakers
scipy_reviewers = con.tables.scipy_reviewers
tracks = con.tables.tracks


# %%
# ungainly column names
renames = {
    "github": "github_handle",
    "company": "institution_or_company",
    "tracks": "track(s)_to_review_for_(check_all_that_apply)",
    "proceedings": "i_am_willing_to_complete_full_paper_reviews_for_the_scipy_proceedings",
    "volunteer": "are_you_interested_in_being_a_volunteer_(in_person)_during_tutorials?",
}

scipy_reviewers = scipy_reviewers.rename(renames)
coi_reviewers = coi_reviewers.rename(
    {
        "coi": "mark_the_speaker(s)_or_company/organization/affiliation(s)_that_could_pose_a_conflict_of_interest",
    }
)

# %%
dupes = (
    scipy_reviewers.select("name", "email").group_by("name", "email").agg(_.name.count()).filter(_["Count(name)"] > 1)
)

# %%
reviewers = (
    scipy_reviewers.join(pretalx_reviewers, "email")
    .drop("name_right")
    .join(coi_reviewers, "email")
    .distinct(on=["name", "email"])
)

# %% [markdown]
# Reviewers who signed up for pretalx but did not fill in COI

# %%
no_coi = pretalx_reviewers.anti_join(coi_reviewers, "email")
num_pretalx_no_coi = no_coi.count()

# %% [markdown]
# Reviewers who filled in COI but did not sign up for pretalx

# %%
no_pretalx = coi_reviewers.anti_join(pretalx_reviewers, "email")
num_coi_no_pretalx = no_pretalx.count()

# %%
reviewers_with_email_typos = (
    scipy_reviewers.join(no_coi, "name")
    .join(no_pretalx, "name")
    .select(scipy_reviewers.name, scipy_reviewers.email, no_pretalx_email=no_pretalx.email, no_coi_email=no_coi.email)
)

# %% [markdown]
# People who signed up as reviewer and signed up for pretalx and submitted COI but used different names

# %%
reviewers_with_name_variations = (
    scipy_reviewers.join(no_coi, "email")
    .join(no_pretalx, "email")
    .select(scipy_reviewers.name, scipy_reviewers.email, no_pretalx_name=no_pretalx.name, no_coi_name=no_coi.name)
)

# %%
ghosted_reviewers = (
    scipy_reviewers.anti_join(reviewers, "name").anti_join(no_coi, "name").anti_join(no_pretalx, "name").distinct()
)


# %%
# reviewers_with_tracks = reviewers.join(tracks)

con.create_table("reviewers", reviewers, overwrite=True)

con.raw_sql("""
create or replace table reviewers_with_tracks as
with reviewers_no_dupes as (select distinct * from reviewers)
select reviewers_no_dupes.name, email, list(tracks.name) as tracks, list(tracks.track_id) as track_ids from reviewers_no_dupes
    join tracks on instr(reviewers_no_dupes.tracks, tracks.name)
    group by reviewers_no_dupes.name, email
""")  # noqa: E501

reviewers_with_tracks = con.tables.reviewers_with_tracks.distinct()


con.raw_sql("""
create or replace table reviewers_with_coi as

with submissions_with_authors as (
    select
        id as submission_id,
        speaker_ids
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
    left join pretalx_speakers on contains(coi_authors.author, lower(pretalx_speakers.Name))
    left join submissions_with_authors on contains(submissions_with_authors.speaker_ids, pretalx_speakers.ID)
group by reviewers.name, reviewers.email
order by reviewers.name
""")

reviewers_with_coi = con.tables.reviewers_with_coi

conflicted_check = con.sql("""
with reviewers_with_coi_pre as (
    select name, email, author
    from reviewers
    join coi_authors on instr(coi, coi_authors.author)
)
select count(*), author from reviewers_with_coi_pre anti join pretalx_speakers on contains(reviewers_with_coi_pre.author, pretalx_speakers.Name) group by author
""").order_by(ibis.desc("count_star()"))  # noqa: E501

reviewers_to_assign = reviewers_with_coi.join(reviewers_with_tracks, "email").select(
    reviewer_id=reviewers_with_coi.email,
    tracks=reviewers_with_tracks.track_ids,
    conflicts_submission_ids=reviewers_with_coi.submission_ids,
)

submissions_to_assign = pretalx_sessions.join(tracks, pretalx_sessions.track == tracks.name).select(
    submission_id=_["id"], author_ids=_.speaker_ids.split(", "), track=_.track_id
)

con.create_table("submissions_to_assign", submissions_to_assign, overwrite=True)
con.create_table("reviewers_to_assign", reviewers_to_assign, overwrite=True)
