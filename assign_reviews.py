# %%
####################
## ASSIGN REVIEWS ##
####################
# Imports
import json

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

MIN_REVIEWS_PER_PERSON = 5
MAX_REVIEWS_PER_PERSON = 9
MIN_REVIEWERS_PER_SUBMISSION = 4
MAX_REVIEWERS_PER_SUBMISSION = 4
ASSIGN_TUTORIALS_TO_ANYONE = True
TUTORIAL_COEFF = 0.8

DEBUG = True

df_submissions = pd.read_csv("2023_submissions_to_assign.csv")
df_reviewers = pd.read_csv("2023_reviewers_to_assign.csv")

df_submissions = df_submissions.assign(assigned_reviewer_ids=[[]] * len(df_submissions))
df_reviewers = df_reviewers.assign(assigned_submission_ids=[[]] * len(df_reviewers))

reviewers = df_reviewers.to_dict("records")
submissions = df_submissions.to_dict("records")

n_reviewers = len(reviewers)
n_submissions = len(submissions)

# Maximize the total number of reviews
objective_fun = -np.ones((n_reviewers, n_submissions))

if ASSIGN_TUTORIALS_TO_ANYONE:
    # Make tutorials more expensive to review
    for n, reviewer in enumerate(reviewers):
        objective_fun[n][df_submissions.track == "TUT"] *= TUTORIAL_COEFF

objective_fun = objective_fun.flatten()

# both zero if reviewer cannot review submission, both one if reviewer is assigned to submission
lb = np.zeros((n_reviewers, n_submissions))  # lower bound
ub = np.zeros((n_reviewers, n_submissions))  # upper bound

submission_constraints = np.zeros((n_submissions, n_reviewers, n_submissions))  # constraints on reviews per submission
reviewer_constraints = np.zeros(
    (n_reviewers, n_reviewers, n_submissions)
)  # constraints on submissions per reviewer. 1 in all the places where reviewer could be assigned

# Establish lower and upper bounds
# reviewer cannot be assigned out of domain
# reviewer must be re-assigned previous assignments
for i, reviewer in enumerate(reviewers):
    for j, submission in enumerate(submissions):
        # each variable is assignment of a submission j to a reviewer i
        # everyone can be assigned a tutorial because we're short on tutorial reviewers
        in_domain = submission["track"] in reviewer["tracks"] or (
            ASSIGN_TUTORIALS_TO_ANYONE and submission["track"] == "TUT"
        )
        no_conflict = submission["submission_id"] not in reviewer["conflicts_submission_ids"]
        ub[i, j] = in_domain and no_conflict

        already_assigned = submission["submission_id"] in reviewer["assigned_submission_ids"]
        lb[i, j] = already_assigned

# Constraints
# each reviewer assigned < max reviews
for i, reviewer in enumerate(reviewers):
    reviewer_constraints[i, i, :] = 1
reviewer_constraints = reviewer_constraints.reshape(n_reviewers, -1)

# each paper assigned to 4 reviewers
for j, _ in enumerate(submissions):
    submission_constraints[j, :, j] = 1
submission_constraints = submission_constraints.reshape(n_submissions, -1)

bounds = Bounds(lb.ravel(), ub.ravel())
submission_per_reviewer_constraint = LinearConstraint(
    reviewer_constraints, MIN_REVIEWS_PER_PERSON, MAX_REVIEWS_PER_PERSON
)
reviews_per_paper_constraint = LinearConstraint(
    submission_constraints, MIN_REVIEWERS_PER_SUBMISSION, MAX_REVIEWERS_PER_SUBMISSION
)
constraints = [submission_per_reviewer_constraint, reviews_per_paper_constraint]

# Run MILP
res = milp(objective_fun, integrality=True, bounds=bounds, constraints=constraints)
print(res)

# %%
x = np.round(res.x).astype(bool)
solution = x.reshape(n_reviewers, n_submissions)

# %%
############################
## FORMAT AND OUTPUT DATA ##
############################
for reviewer, assignments in zip(reviewers, solution):
    reviewer["assigned_submission_ids"] = df_submissions.submission_id[assignments].values.tolist()
    if DEBUG:
        # Check how many tutorials everyone got
        reviewer["is_tutorial"] = [t == "TUT" for t in df_submissions.track[assignments]]
        # Check that each reviewer actually was assigned a submission in their domain
        reviewer["track_in_domain"] = [t in reviewer["tracks"] for t in df_submissions.track[assignments]]

if DEBUG:
    result = {reviewer["reviewer_id"]: sorted(reviewer["is_tutorial"]) for reviewer in reviewers}

    with open("review-assignments-debug.json", "w") as fp:
        fp.write(json.dumps(result, indent=4))

result = {reviewer["reviewer_id"]: reviewer["assigned_submission_ids"] for reviewer in reviewers}

with open("review-assignments.json", "w") as fp:
    fp.write(json.dumps(result, indent=4))

for submission, assignments in zip(submissions, solution.T):
    submission["assigned_reviewer_ids"] = df_reviewers.reviewer_id[assignments].values.tolist()

result = {submission["submission_id"]: submission["assigned_reviewer_ids"] for submission in submissions}

with open("submission-assignments.json", "w") as fp:
    fp.write(json.dumps(result, indent=4))

# %%
