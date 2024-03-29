from contextlib import closing

import numpy as np
import requests
import yaml
from tqdm.auto import tqdm

with open(".pretalx.yaml") as pretalx_config:
    config = yaml.safe_load(pretalx_config)
    token = config["api_tokens"][0]["token"]


def fetch_sequence(url, token, max_queries=50):
    sequence = []
    max_queries = 50
    num_queries = 0
    num_results_expected = None

    with closing(tqdm(total=max_queries)) as progress:
        while True:
            response = requests.get(url, headers={"Authorization": f"Token {token}"})
            assert response.ok
            data = response.json()
            progress.update()
            num_queries += 1

            assert "results" in data
            assert "next" in data

            if num_results_expected is None and "count" in data:
                num_results_expected = data["count"]
                max_queries = int(np.ceil(num_results_expected / len(data["results"])))
                progress.reset(max_queries)
                progress.update(num_queries)
            else:
                assert num_results_expected == data["count"]

            sequence += data["results"]
            url = data["next"]
            if not url:
                break

    return sequence


reviews = fetch_sequence("https://cfp.scipy.org/api/events/2024/reviews/", token)
submissions = fetch_sequence("https://cfp.scipy.org/api/events/2024/submissions/", token)
