# %%
####################
## ASSIGN REVIEWS ##
####################
# Imports
import json
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

DEBUG = True


def create_objective_fun(df_reviewers, df_submissions, tutorial_coeff):
    reviewers = df_reviewers.to_dict("records")
    submissions = df_submissions.to_dict("records")

    n_reviewers = len(reviewers)
    n_submissions = len(submissions)

    # Maximize the total number of reviews
    objective_fun = -np.ones((n_reviewers, n_submissions))

    # Make tutorials more expensive to review
    for n, reviewer in enumerate(reviewers):
        objective_fun[n][df_submissions.track == "TUT"] *= tutorial_coeff

    objective_fun = objective_fun.flatten()

    return objective_fun


def create_lb_ub(reviewers, submissions, assign_tutorials_to_anyone):
    n_reviewers = len(reviewers)
    n_submissions = len(submissions)
    # both zero if reviewer cannot review submission, both one if reviewer is assigned to submission
    lb = np.zeros((n_reviewers, n_submissions))  # lower bound
    ub = np.zeros((n_reviewers, n_submissions))  # upper bound

    # Establish lower and upper bounds
    # reviewer cannot be assigned out of domain
    # reviewer must be re-assigned previous assignments
    for i, reviewer in enumerate(reviewers):
        for j, submission in enumerate(submissions):
            # each variable is assignment of a submission j to a reviewer i
            # everyone can be assigned a tutorial because we're short on tutorial reviewers
            in_domain = submission["track"] in reviewer["tracks"] or (
                assign_tutorials_to_anyone and submission["track"] == "TUT"
            )
            no_conflict = submission["submission_id"] not in reviewer["conflicts_submission_ids"]
            ub[i, j] = in_domain and no_conflict

            already_assigned = submission["submission_id"] in reviewer["assigned_submission_ids"]
            lb[i, j] = already_assigned

    return lb, ub


def create_constraints(reviewers, submissions, min_reviews, max_reviews, min_reviewers, max_reviewers):
    n_reviewers = len(reviewers)
    n_submissions = len(submissions)

    submission_constraints = np.zeros(
        (n_submissions, n_reviewers, n_submissions)
    )  # constraints on reviews per submission
    reviewer_constraints = np.zeros(
        (n_reviewers, n_reviewers, n_submissions)
    )  # constraints on submissions per reviewer. 1 in all the places where reviewer could be assigned

    # Constraints
    # each reviewer assigned < max reviews
    for i, reviewer in enumerate(reviewers):
        reviewer_constraints[i, i, :] = 1
    reviewer_constraints = reviewer_constraints.reshape(n_reviewers, -1)

    # each paper assigned to 4 reviewers
    for j, _ in enumerate(submissions):
        submission_constraints[j, :, j] = 1
    submission_constraints = submission_constraints.reshape(n_submissions, -1)

    submission_per_reviewer_constraint = LinearConstraint(reviewer_constraints, min_reviews, max_reviews)
    reviews_per_paper_constraint = LinearConstraint(submission_constraints, min_reviewers, max_reviewers)
    constraints = [submission_per_reviewer_constraint, reviews_per_paper_constraint]

    return constraints


def solve_milp(
    df_reviewers,
    df_submissions,
    min_reviews,
    max_reviews,
    min_reviewers,
    max_reviewers,
    tutorial_coeff,
    assign_tutorials_to_anyone,
):
    reviewers = df_reviewers.to_dict("records")
    submissions = df_submissions.to_dict("records")

    objective_fun = create_objective_fun(df_reviewers, df_submissions, tutorial_coeff)
    lb, ub = create_lb_ub(reviewers, submissions, assign_tutorials_to_anyone)
    bounds = Bounds(lb.ravel(), ub.ravel())
    constraints = create_constraints(reviewers, submissions, min_reviews, max_reviews, min_reviewers, max_reviewers)

    # Run MILP
    res = milp(objective_fun, integrality=True, bounds=bounds, constraints=constraints)
    print(res)
    n_reviewers = len(reviewers)
    n_submissions = len(submissions)

    # %%
    if res.success:
        x = np.round(res.x).astype(bool)
        solution = x.reshape(n_reviewers, n_submissions)
        return solution


# %%
############################
## FORMAT AND OUTPUT DATA ##
############################
def format_and_output_result(df_reviewers, df_submissions, solution, post_fix="", output_dir=Path.cwd() / "output"):
    reviewers = df_reviewers.to_dict("records")
    submissions = df_submissions.to_dict("records")

    for reviewer, assignments in zip(reviewers, solution):
        # reviewer["assigned_submission_ids"] = reviewer["assigned_submission_ids"] + \
        # df_submissions.submission_id[assignments].values.tolist()
        reviewer["assigned_submission_ids"] = df_submissions.submission_id[assignments].values.tolist()
        if DEBUG:
            # Check how many tutorials everyone got
            reviewer["is_tutorial"] = [t == "TUT" for t in df_submissions.track[assignments]]
            reviewer["num_tutorials"] = sum(reviewer["is_tutorial"])
            reviewer["num_submissions"] = len(reviewer["assigned_submission_ids"])
            reviewer["tutorial_reviewer"] = "TUT" in reviewer["tracks"]
            # Check that each reviewer actually was assigned a submission in their domain
            reviewer["track_in_domain"] = [t in reviewer["tracks"] for t in df_submissions.track[assignments]]

    if DEBUG:
        result = {reviewer["reviewer_id"]: sorted(reviewer["is_tutorial"]) for reviewer in reviewers}

        with open(output_dir / f"review-assignments-debug{post_fix}.json", "w") as fp:
            fp.write(json.dumps(result, indent=4))

    result = {reviewer["reviewer_id"]: reviewer["assigned_submission_ids"] for reviewer in reviewers}

    with open(output_dir / f"review-assignments{post_fix}.json", "w") as fp:
        fp.write(json.dumps(result, indent=4))

    for submission, assignments in zip(submissions, solution.T):
        submission["assigned_reviewer_ids"] = df_reviewers.reviewer_id[assignments].values.tolist()

    result = {submission["submission_id"]: submission["assigned_reviewer_ids"] for submission in submissions}

    with open(output_dir / f"submission-assignments{post_fix}.json", "w") as fp:
        fp.write(json.dumps(result, indent=4))

    return reviewers, submissions
