import numpy as np
import pandas as pd

from scripts.analysis import bootstrap_gain, plot_documents, validation_groups


def test_transitive_episode_and_issue_overlap_is_grouped():
    stories = pd.DataFrame(
        {"story_id": ["a", "b", "c", "d"], "episode_url": ["one", "one", "two", "three"]}
    )
    issues = pd.DataFrame({"story_id": ["a", "b", "c", "d"], "issue_id": [1, 2, 2, 3]})
    labels = validation_groups(stories, issues)
    assert labels.tolist() == ["a", "a", "a", "d"]
    shuffled = validation_groups(stories.iloc[::-1], issues.iloc[::-1])
    assert dict(zip(stories.story_id, labels)) == dict(zip(stories.iloc[::-1].story_id, shuffled))


def test_group_bootstrap_uses_weighted_story_loss_and_correct_direction():
    y = np.zeros(4)
    base = np.ones(4)
    candidate = np.zeros(4)
    result = bootstrap_gain(y, base, candidate, ["a", "a", "a", "b"], repetitions=100)
    assert result == {"gain_rank_places": 1.0, "ci_low": 1.0, "ci_high": 1.0}


def test_permutation_retains_observed_masks_and_value_sets():
    from scripts.analysis import permute_observed_block

    frame = pd.DataFrame(
        {
            "cast": ["Bruce", "", "Joker", ""],
            "award": [1.0, np.nan, 3.0, np.nan],
            "unrelated": [1, 2, 3, 4],
        }
    )
    changed = permute_observed_block(frame, ["cast", "award"], np.random.default_rng(42))
    pd.testing.assert_frame_equal(frame.isna(), changed.isna())
    assert frame.cast.eq("").equals(changed.cast.eq(""))
    assert set(changed.loc[[0, 2], "cast"]) == {"Bruce", "Joker"}
    assert changed.unrelated.equals(frame.unrelated)


def test_rank_error_does_not_depend_on_subset_size():
    y = np.array([100.0, 700.0])
    baseline = np.array([200.0, 600.0])
    candidate = np.array([150.0, 650.0])
    result = bootstrap_gain(y, baseline, candidate, ["a", "b"], repetitions=100)
    assert result["gain_rank_places"] == 50.0


def test_shared_source_and_normalized_text_extend_groups_transitively():
    stories = pd.DataFrame({"story_id": list("abcd"), "episode_url": list("wxyz")})
    issues = pd.DataFrame({"story_id": list("abcd"), "issue_id": [1, 2, 3, 4]})
    texts = pd.DataFrame(
        {
            "story_id": list("abcd"),
            "source_url": ["one", "one", "three", "four"],
            "source_substory_index": [1, 1, 2, 1],
            "synopsis_text": [
                "First version.",
                "Batman returns.",
                "BATMAN  returns.",
                "Other plot.",
            ],
            "text_status": ["available"] * 4,
        }
    )
    assert validation_groups(stories, issues, texts).tolist() == ["a", "a", "a", "d"]


def test_plot_bags_deduplicate_without_hiding_missing_selected_texts():
    stories = pd.DataFrame({"story_id": list("abc"), "issue_list_complete": [True, True, False]})
    texts = pd.DataFrame(
        {
            "story_id": ["a", "a", "a", "b", "c"],
            "synopsis_text": ["Batman returns.", "BATMAN  returns.", None, None, "Robin escapes."],
            "text_status": [
                "available",
                "available",
                "missing_synopsis",
                "missing_synopsis",
                "available",
            ],
        }
    )
    bags = plot_documents(stories, texts).set_index("story_id")
    assert bags.loc["a", "plot_text"] == "Batman returns."
    assert bags.loc["a", "plot_fraction"] == 2 / 3
    assert bags.plot_complete.tolist() == [0, 0, 0]
    assert bags.loc["b", "plot_text"] == "" and bags.loc["b", "log_plot_words"] == 0
    assert np.isclose(bags.loc["a", "log_plot_words"], np.log1p(2))


def test_correlation_bootstrap_matches_dataframe_reference_with_ties_and_unequal_groups():
    from scipy.stats import spearmanr

    from scripts.analysis import correlation_interval

    frame = pd.DataFrame(
        {
            "x": [1, 2, 2, 4, 5, 6, 7],
            "y": [2, 1, 3, 3, 6, 5, 4],
            "group": ["b", "b", "a", "a", "a", "c", "c"],
        },
        index=[20, 4, 90, 1, 13, 8, 42],
    )
    units = [frame.loc[frame.group.eq(g)] for g in frame.group.unique()]
    rng = np.random.default_rng(42)
    correlations = []
    for _ in range(100):
        selected = pd.concat([units[k] for k in rng.integers(0, len(units), len(units))])
        correlations.append(spearmanr(selected.x, selected.y).statistic)
    expected = np.quantile(correlations, [0.025, 0.975])
    actual = correlation_interval(frame.x, frame.y, frame.group, repetitions=100)
    np.testing.assert_array_equal(actual, expected)
