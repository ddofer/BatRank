"""Shared analysis routines. Regression targets and errors use original page-order rank units."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import DisjointSet
from scipy.stats import kendalltau, spearmanr
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

COLORS = {
    "blue": "#2767A0",
    "orange": "#D57927",
    "green": "#26806B",
    "red": "#B84D55",
    "grey": "#75818C",
}
ROLES = ["writers", "pencilers", "inkers", "colorists", "letterers", "editors"]
BIBLIOGRAPHY = [
    "cover_year_start",
    "cover_year_end",
    "issue_count",
    "metadata_coverage",
    "discussion_day",
    "issue_count_available",
]
CRAFT = [
    "narrative_credit_issue_coverage",
    "narrative_team_count",
    "narrative_dominant_team_share",
    "narrative_self_inking_share",
    "narrative_writer_artist_overlap_share",
    "team_switch_rate",
    "featured_entity_count",
    "antagonists_entity_count",
    "cast_issue_coverage",
    "substory_attribution_coverage",
    "cast_eligible",
]
CATEGORIES = ["medium", "format_hint"]
CAST = ["featured_entity_ids", "antagonists_entity_ids"]
AWARDS = [
    "creator_eisner_personal_wins_pre_publication",
    *[f"{role}_eisner_role_wins_pre_publication" for role in ROLES if role != "editors"],
]
AWARD_CONTROLS = [
    "awards_prepublication_observed_years",
    "awards_credited_creator_count",
    "awards_window_observed",
]


def load_data():
    roots = [Path.cwd(), Path.cwd().parent]
    roots += [p.parents[2] for p in Path("/kaggle/input").glob("**/data/processed/stories.csv")]
    root = next(p for p in roots if (p / "data/processed/stories.csv").exists())
    stories = pd.read_csv(root / "data/processed/stories.csv")
    issues = pd.read_csv(root / "data/processed/issues.csv")
    assert stories.story_id.is_unique
    assert stories["rank"].tolist() == list(range(1, len(stories) + 1))
    assert set(issues.story_id) == set(stories.story_id)
    report = (
        Path("/kaggle/working/reports") if Path("/kaggle/working").exists() else root / "reports"
    )
    (report / "figures").mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "figure.figsize": (10, 5),
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "font.size": 11,
            "axes.labelcolor": "#273440",
            "text.color": "#273440",
            "savefig.facecolor": "white",
            "axes.grid": False,
        }
    )
    pd.set_option("display.max_colwidth", 70)
    return root, report, stories, issues


def split_set(value):
    return [item for item in value.split("|") if item] if isinstance(value, str) else []


def validation_groups(stories, issues, texts=None):
    """Connected episodes/issues and, optionally, shared source or normalized plot text."""
    components = DisjointSet(stories.story_id)
    collections = [g.story_id.tolist() for _, g in stories.groupby("episode_url", dropna=True)]
    collections += [
        g.story_id.unique().tolist()
        for _, g in issues.dropna(subset=["issue_id"]).groupby("issue_id")
    ]
    if texts is not None:
        if not set(texts.story_id) <= set(stories.story_id):
            raise ValueError("Synopsis has an unknown story ID")
        available = texts.loc[texts.text_status.eq("available")].copy()
        available["text_key"] = available.synopsis_text.str.casefold().str.split().str.join(" ")
        for columns in [["source_url", "source_substory_index"], ["text_key"]]:
            collections += [
                g.story_id.unique().tolist() for _, g in available.groupby(columns, dropna=True)
            ]
    for members in collections:
        for member in members[1:]:
            components.merge(members[0], member)
    label = {member: min(component) for component in components.subsets() for member in component}
    return np.array([label[x] for x in stories.story_id])


def grouped_folds(stories, issues, seed=42, texts=None):
    groups = validation_groups(stories, issues, texts)
    folds = list(
        GroupKFold(n_splits=5, shuffle=True, random_state=seed).split(stories, groups=groups)
    )
    for train, test in folds:
        assert set(groups[train]).isdisjoint(groups[test])
        train_issues = set(
            issues.loc[issues.story_id.isin(stories.story_id.iloc[train]), "issue_id"].dropna()
        )
        test_issues = set(
            issues.loc[issues.story_id.isin(stories.story_id.iloc[test]), "issue_id"].dropna()
        )
        assert train_issues.isdisjoint(test_issues)
    return groups, folds


def plot_documents(stories, texts):
    """Unordered bags of available plot text, with explicit completeness and length controls."""
    if not stories.story_id.is_unique or set(texts.story_id) != set(stories.story_id):
        raise ValueError("Synopsis and story key sets must agree")
    available = texts.loc[texts.text_status.eq("available")].copy()
    if available.synopsis_text.fillna("").str.strip().eq("").any():
        raise ValueError("Available synopsis must contain text")
    available["text_key"] = available.synopsis_text.str.casefold().str.split().str.join(" ")
    unique = available.drop_duplicates(["story_id", "text_key"])
    documents = unique.groupby("story_id").synopsis_text.agg("\n\n".join)
    frame = stories[["story_id", "issue_list_complete"]].copy()
    frame["plot_text"] = frame.story_id.map(documents).fillna("")
    total = frame.story_id.map(texts.groupby("story_id").size())
    found = frame.story_id.map(available.groupby("story_id").size()).fillna(0)
    frame["plot_available"] = found.gt(0).astype(float)
    frame["plot_complete"] = (found.eq(total) & frame.issue_list_complete.eq(True)).astype(float)
    frame["plot_fraction"] = found / total
    frame["log_plot_words"] = np.log1p(frame.plot_text.str.split().str.len())
    frame["log_plot_units"] = np.log1p(total)
    return frame.drop(columns="issue_list_complete")


def feature_frame(stories):
    columns = list(
        dict.fromkeys(
            [c for c in BIBLIOGRAPHY if c != "discussion_day"]
            + CATEGORIES
            + CRAFT
            + ROLES
            + ["narrative_" + r for r in ROLES]
            + CAST
            + AWARDS
            + [
                "narrative_team_comparable_transitions",
                "narrative_team_switch_count",
                "awards_prepublication_observed_years",
                "awards_credited_creator_count",
            ]
        )
    )
    derived = {"team_switch_rate", "issue_count_available", "cast_eligible"}
    frame = stories[[c for c in columns if c not in derived]].copy()
    dates = pd.to_datetime(stories.discussion_date)
    frame["discussion_day"] = (dates - dates.min()).dt.days
    denominator = frame.narrative_team_comparable_transitions.replace(0, np.nan)
    frame["team_switch_rate"] = frame.narrative_team_switch_count / denominator
    frame["issue_count_available"] = stories.issue_count.notna().astype(float)
    resolved_cast = stories.cast_scope.eq("selected_narratives") & stories.cast_issue_coverage.eq(1)
    frame["cast_eligible"] = resolved_cast.astype(float)
    frame["awards_window_observed"] = (
        stories.creator_eisner_personal_wins_pre_publication.notna().astype(float)
    )
    frame[CAST] = frame[CAST].where(resolved_cast, "")
    frame[["featured_entity_count", "antagonists_entity_count"]] = frame[
        ["featured_entity_count", "antagonists_entity_count"]
    ].where(resolved_cast)
    for column in AWARDS:
        frame[column] = np.log1p(frame[column])
    for col in ROLES + ["narrative_" + r for r in ROLES] + CAST:
        frame[col] = frame[col].fillna("")
    return frame


def regression(numeric, token_columns=(), categorical=CATEGORIES, forest=False):
    preprocessing = ColumnTransformer(
        [
            (
                "numeric",
                make_pipeline(
                    SimpleImputer(strategy="median", keep_empty_features=True),
                    StandardScaler(),
                ),
                list(numeric),
            ),
            (
                "categories",
                OneHotEncoder(handle_unknown="ignore", min_frequency=3),
                list(categorical),
            ),
            *[
                (
                    col,
                    CountVectorizer(
                        tokenizer=split_set,
                        token_pattern=None,
                        lowercase=False,
                        binary=True,
                        min_df=3,
                    ),
                    col,
                )
                for col in token_columns
            ],
        ]
    )
    estimator = (
        RandomForestRegressor(
            n_estimators=240, min_samples_leaf=6, max_features=0.7, random_state=42, n_jobs=2
        )
        if forest
        else Ridge(alpha=20, solver="lsqr")
    )
    return make_pipeline(preprocessing, estimator)


def fit_oof(models, frame, y, folds):
    predictions, estimators, metrics = {}, {}, []
    for name, template in models.items():
        prediction = np.empty(len(y))
        fitted = []
        for fold, (train, test) in enumerate(folds):
            estimator = clone(template).fit(frame.iloc[train], y[train])
            prediction[test] = estimator.predict(frame.iloc[test])
            fitted.append(estimator)
            values = prediction[test]
            rho = spearmanr(y[test], values).statistic if np.std(values) > 1e-10 else np.nan
            tau = kendalltau(y[test], values).statistic if np.std(values) > 1e-10 else np.nan
            metrics.append(
                {
                    "model": name,
                    "fold": fold,
                    "n_test": len(test),
                    "MAE_rank_places": mean_absolute_error(y[test], values),
                    "Spearman": rho,
                    "Kendall_tau": tau,
                }
            )
        assert np.isfinite(prediction).all()
        predictions[name], estimators[name] = prediction, fitted
    return predictions, estimators, pd.DataFrame(metrics)


def model_summary(y, predictions):
    return pd.DataFrame(
        [
            {
                "model": name,
                "MAE_rank_places": mean_absolute_error(y, p),
                "R2": r2_score(y, p),
                "Spearman": spearmanr(y, p).statistic,
            }
            for name, p in predictions.items()
        ]
    )


def correlation_interval(x, y, groups, repetitions=600):
    """Percentile interval for Spearman correlation, resampling whole groups."""
    pairs = np.column_stack([x, y])
    groups = np.asarray(groups)
    units = [pairs[groups == g] for g in pd.unique(groups)]
    rng = np.random.default_rng(42)
    values = []
    for _ in range(repetitions):
        selected = np.concatenate([units[k] for k in rng.integers(0, len(units), len(units))])
        value = spearmanr(selected[:, 0], selected[:, 1]).statistic
        if np.isfinite(value):
            values.append(value)
    return np.quantile(values, [0.025, 0.975])


def bootstrap_gain(y, baseline, candidate, groups, repetitions=2000, seed=42):
    """Paired group bootstrap of fixed OOF losses; positive means candidate improves MAE."""
    gain = np.abs(y - baseline) - np.abs(y - candidate)
    blocks = (
        pd.DataFrame({"group": groups, "gain": gain})
        .groupby("group")
        .gain.agg(["sum", "count"])
        .to_numpy()
    )
    rng = np.random.default_rng(seed)
    selected = blocks[rng.integers(0, len(blocks), size=(repetitions, len(blocks)))]
    samples = selected[:, :, 0].sum(axis=1) / selected[:, :, 1].sum(axis=1)
    return {
        "gain_rank_places": float(gain.mean()),
        "ci_low": float(np.quantile(samples, 0.025)),
        "ci_high": float(np.quantile(samples, 0.975)),
    }


def block_importance(estimators, frame, y, folds, blocks, repeats=5):
    """Shuffle whole feature blocks within observed-mask strata; leave availability unchanged."""
    records = []
    for fold, ((train, test), estimator) in enumerate(zip(folds, estimators)):
        held = frame.iloc[test]
        baseline = mean_absolute_error(y[test], estimator.predict(held))
        for name, columns in blocks.items():
            rng = np.random.default_rng(100 + fold)
            columns = [c for c in columns if c in frame]
            for repeat in range(repeats):
                changed = permute_observed_block(held, columns, rng)
                delta = mean_absolute_error(y[test], estimator.predict(changed)) - baseline
                records.append(
                    {
                        "fold": fold,
                        "block": name,
                        "repeat": repeat,
                        "MAE_increase_rank_places": delta,
                    }
                )
    return pd.DataFrame(records)


def permute_observed_block(frame, columns, rng):
    changed = frame.copy()
    absent = frame[columns].isna() | frame[columns].eq("")
    strata = absent.astype(str).agg("|".join, axis=1)
    for positions in strata.groupby(strata, sort=False).indices.values():
        changed.iloc[positions, changed.columns.get_indexer(columns)] = frame.iloc[
            rng.permutation(positions)
        ][columns].to_numpy()
    return changed


def creator_table(stories, column, minimum=8):
    associations = (
        stories[["story_id", "rank", column]]
        .assign(creator=stories[column].map(split_set))
        .explode("creator")
        .dropna(subset=["creator"])
    )
    associations = associations.drop_duplicates(["story_id", "creator"])
    table = associations.groupby("creator")["rank"].agg(
        n="size", median="median", q25=lambda x: x.quantile(0.25), q75=lambda x: x.quantile(0.75)
    )
    return table[table.n.ge(minimum)].sort_values("median")


def save_figure(fig, report, name):
    fig.savefig(report / "figures" / f"{name}.png", dpi=160, bbox_inches="tight")
    plt.show()
    plt.close(fig)
