# %% [markdown]
# # What Batman plots are made of
#
# The 1980s have complete plot summaries for 59 of 69 ranked stories. The 2020s have 8 of 69. Whatever the words say, they mostly say it about older comics.
#
# The list is [BatChat](https://comicsxf.com/batchat-rankings/), a podcast where **Matt Lazorwitz and Will Nevin** have read and ranked **740 Batman stories**. This notebook covers series, formats, and plot summaries: which series and formats do best, and what **700,000 words of fan-written plot summaries** from the [DC Database wiki](https://dc.fandom.com/) can and cannot tell us.
#
# Companions: [Who gets the good Batman stories?](https://www.kaggle.com/code/danofer/who-gets-the-good-batman-stories) · [Gotham's rogues, ranked](https://www.kaggle.com/code/danofer/gotham-s-rogues-ranked). **Rank 1 is best; lower is better throughout.**
#
# <details><summary>Three words you'll see a lot</summary>
#
# - **Rank**: position on BatChat's list. #1 is the best Batman story; #740 the worst. Lower is better everywhere here.
# - **Median rank**: the typical rank for a group. Half the group's stories rank above it, half below.
# - **Selected story**: an issue can hold several stories (a lead feature and a backup). We only count the one the podcast actually ranked, and the summary of *that* one.
#
# </details>
#
# By [Dan Ofer](https://scholar.google.com/citations?user=uDx2ItYAAAAJ) · [Dataset](https://www.kaggle.com/datasets/danofer/batchat-batman-rankings) · [Code and sources](https://github.com/ddofer/BatRank) · snapshot of 21 October 2026

# %%
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from IPython.display import HTML, display

# Kaggle mounts the dataset under /kaggle/input; locally, `make share` stages it in data/kaggle.
DATA = next(
    p.parent
    for root in ["/kaggle/input", "data/kaggle", "../data/kaggle"]
    for p in Path(root).rglob("stories.csv")
)
COLORS = {"blue": "#2767A0", "orange": "#D57927", "green": "#26806B", "grey": "#75818C"}
sns.set_theme(
    style="ticks",
    font_scale=1.05,
    rc={"axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold"},
)
pd.set_option("display.max_colwidth", 70)


def rank_summary(frame, by):
    """Count, median rank, and best/worst-ranked story titles per group."""
    return (
        frame.sort_values("rank")
        .groupby(by)
        .agg(
            n=("story_id", "nunique"),
            median_rank=("rank", "median"),
            best_rank=("rank", "first"),
            best_story=("title", "first"),
            worst_rank=("rank", "last"),
            worst_story=("title", "last"),
        )
    )


def rank_boxes(ax, entries, key, labels, color=COLORS["blue"]):
    """Box of the middle half plus one faint dot per story, in the order of `labels`."""
    chart = entries[entries[key].isin(labels.index)].assign(label=lambda d: d[key].map(labels))
    common = dict(data=chart, x="rank", y="label", order=labels.tolist(), ax=ax)
    sns.stripplot(**common, color=COLORS["grey"], alpha=0.35, size=3, jitter=False, zorder=0)
    sns.boxplot(**common, color=color, whis=0, showfliers=False, width=0.45)
    ax.set(xlabel="BatChat rank · 1 = best", ylabel="", xlim=(1, N))


PRETTY = {
    "n": "Stories",
    "median_rank": "Median rank",
    "best_rank": "Best rank",
    "best_story": "Best-ranked story",
    "worst_rank": "Worst rank",
    "worst_story": "Worst-ranked story",
}


def collapsible(summary, table, note="", **to_html):
    """Show a long table inside a click-to-expand block."""
    body = table.to_html(escape=True, **to_html)
    return HTML(f"<details><summary>{summary}</summary><p>{note}</p>{body}</details>")


stories = pd.read_csv(DATA / "stories.csv")
issues = pd.read_csv(DATA / "issues.csv")
texts = pd.read_csv(DATA / "story_texts.csv")
N = len(stories)
print(f"{N:,} ranked stories · {len(issues):,} issues · snapshot {stories.snapshot_date.iloc[0]}")

# %% [markdown]
# ## Which Batman series fare best?
#
# *Gotham Central* follows Gotham's police. *Batman Adventures* brings the animated series to comics. *Legends of the Dark Knight* tells standalone Batman arcs. *Black and White* collects monochrome short stories.
#
# Here are the twelve series with the most ranked stories. A story spanning several series appears in each. Volumes stay separate, because *Batman* has restarted at #1 more than once.

# %%
series_links = issues[["story_id", "wiki_title"]].dropna().copy()
series_links["Series"] = series_links.wiki_title.str.extract(r"^(.* Vol \d+) \d+[A-Za-z]?$")[0]
series_links = (
    series_links.dropna(subset=["Series"])
    .drop_duplicates(["story_id", "Series"])
    .merge(stories[["story_id", "rank", "title"]], on="story_id", validate="many_to_one")
)
series_rankings = rank_summary(series_links, "Series")
top_series = series_rankings.nlargest(12, "n").sort_values("median_rank")
fig, ax = plt.subplots(figsize=(12, 7))
rank_boxes(
    ax, series_links, "Series", top_series.index.to_series() + " · n=" + top_series.n.astype(str)
)
ax.set_title("The twelve most represented series · boxes show the middle half")
fig.tight_layout()
plt.show()
print(f"{series_links.story_id.nunique()} of {N} stories have a matched series title.")

series_table = series_rankings[series_rankings.n.ge(3)].sort_values("median_rank")
display(
    collapsible(
        f"All {len(series_table)} series with three or more ranked stories",
        series_table.rename(columns=PRETTY),
        "Lower median rank is better. A cross-series story can appear in several rows.",
    )
)

# %% [markdown]
# ### Elseworlds and graphic novels
#
# **Elseworlds** stories put familiar characters in alternate continuities. **32 stories** contain an issue explicitly labeled Elseworlds, and the ranking list calls **26** of them original graphic novels. The two groups overlap.
#
# The [DC Database wiki](https://dc.fandom.com/) also labels graphic novels, but that category can include collections, so it gets its own row. All three groups spread across the whole list: a format is not a quality signal. A missing label means unknown, so there is no clean "ordinary comics" comparison group.

# %%
labels = pd.read_csv(DATA / "story_labels.csv")
label_books = stories.merge(labels, on="story_id", validate="one_to_one")
format_groups = {
    "Elseworlds-labeled issue": label_books.elseworlds_issue_count.gt(0),
    "Original graphic novel": label_books.format_hint.eq("original_graphic_novel"),
    "Wiki graphic-novel category": label_books.graphic_novel_issue_count.gt(0),
}
format_rows = pd.concat(
    [
        label_books.loc[mask, ["story_id", "title", "rank"]].assign(label=name)
        for name, mask in format_groups.items()
    ],
    ignore_index=True,
)
display(
    rank_summary(format_rows, "label")
    .loc[list(format_groups)]
    .rename(columns=PRETTY)
    .rename_axis(None)
)
display(
    collapsible(
        "Labeled stories and their ranks",
        format_rows.sort_values(["label", "rank"])[["label", "rank", "title"]],
        index=False,
    )
)

# %% [markdown]
# Bonus: stories tagged with a named DC event (Rebirth, No Man's Land, …). "Event" can mean a holiday special or a relaunch, not only a crossover.

# %%
events = label_books.loc[label_books.event_issue_count.gt(0), ["story_id", "rank", "event_names"]]
events = events.assign(event=events.event_names.str.split("|")).explode("event")
event_summary = events.groupby("event").agg(
    stories=("story_id", "nunique"), median_rank=("rank", "median")
)
display(
    collapsible(
        "Named events with at least three stories (not necessarily crossovers)",
        event_summary.query("stories >= 3").sort_values("median_rank"),
    )
)

# %% [markdown]
# ## What do the plots sound like?
#
# We have **1,711 summaries** totaling **703,219 words**, from the [DC Database wiki](https://dc.fandom.com/). **587 stories** have some text, and **481** have every selected summary plus a complete issue list.
#
# Before looking at the words, check which books they represent. The 1980s have complete text for **59 of 69** stories; the 2020s for just **8 of 69**.
#
# Green means complete, orange partial, and grey no usable text. The numbers count stories. [Can a computer predict BatChat's favorites?](https://www.kaggle.com/code/danofer/batchat-s-favorite-batman-stories) tests whether these words improve rank predictions.

# %%
available = texts[texts.text_status.eq("available")].copy()
# Identical summaries (ignoring case and spacing) count once per story.
available["text_key"] = available.synopsis_text.str.casefold().str.split().str.join(" ")
plot_text = (
    available.drop_duplicates(["story_id", "text_key"])
    .groupby("story_id")
    .synopsis_text.agg("\n\n".join)
)
text_profile = stories[["story_id", "title", "rank", "cover_year_start"]].assign(
    plot_text=stories.story_id.map(plot_text).fillna(""),
    has_text=stories.story_id.isin(available.story_id),
    # Complete: every selected summary is available and the issue list is complete.
    complete=stories.story_id.map(texts.text_status.eq("available").groupby(texts.story_id).all())
    & stories.issue_list_complete,
)
text_profile["coverage"] = np.select(
    [text_profile.complete, text_profile.has_text], ["Complete", "Partial"], default="None"
)
text_profile["decade"] = (text_profile.cover_year_start // 10 * 10).astype("Int64")
coverage_order = ["Complete", "Partial", "None"]
text_by_era = pd.crosstab(text_profile.decade, text_profile.coverage)[coverage_order]
shares = 100 * text_by_era.div(text_by_era.sum(axis=1), axis=0)

fig, ax = plt.subplots(figsize=(10, 5.4))
shares.plot.barh(
    stacked=True, color=[COLORS["green"], COLORS["orange"], "#D8DDE1"], width=0.72, ax=ax
)
for bars, status in zip(ax.containers, coverage_order):
    labels = [str(n) if share >= 9 else "" for n, share in zip(text_by_era[status], shares[status])]
    ax.bar_label(
        bars,
        labels=labels,
        label_type="center",
        fontsize=9,
        color="white" if status == "Complete" else "#202B35",
    )
ax.set(
    yticklabels=[f"{decade}s (n={n})" for decade, n in text_by_era.sum(axis=1).items()],
    xlim=(0, 100),
    xlabel="Share of stories in each publication decade (%)",
    ylabel="",
    title="Recent comics have much less plot text",
)
ax.invert_yaxis()
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False)
plt.show()
print(f"{text_profile.decade.isna().sum()} stories have no known decade and are not shown.")

# %% [markdown]
# ### Vampires, nightmares, and other plot ingredients
#
# Vampires turn up in **nine fully summarized stories**, from *Red Rain* (#6) to *Superman and Batman vs. Vampires and Werewolves* (#732). The same premise leaves plenty of room in execution.
#
# These are keyword searches, not hand-labeled themes, so a dream can be a passing remark. Each dot is one story. We use the 481 stories with complete summaries; longer summaries have more chances to match.

# %%
plot_terms = {
    "Vampires": r"\bvampir\w*",
    "Dreams / nightmares": r"\b(?:dreams?|nightmares?)\b",
    "Amnesia": r"\b(?:amnesia|amnesiac)\b",
    "Time travel": r"\btime[- ]trav\w*",
    "Trials / juries": r"\b(?:trial|jury|courtroom)\b",
    "Cloning": r"\bclon(?:e[sd]?|ing)\b",
}
complete_plots = text_profile[text_profile.complete].reset_index(drop=True)
term_matches = pd.concat(
    [
        complete_plots.loc[
            complete_plots.plot_text.str.contains(pattern, case=False),
            ["story_id", "title", "rank"],
        ].assign(topic=topic)
        for topic, pattern in plot_terms.items()
    ],
    ignore_index=True,
)
term_summary = rank_summary(term_matches, "topic").sort_values("median_rank")
fig, ax = plt.subplots(figsize=(10, 4.5))
sns.stripplot(
    data=term_matches,
    x="rank",
    y="topic",
    order=term_summary.index,
    jitter=False,
    alpha=0.45,
    color=COLORS["blue"],
    ax=ax,
)
ax.scatter(
    term_summary.median_rank,
    range(len(term_summary)),
    marker="|",
    s=350,
    color="black",
    label="Median rank",
    zorder=4,
)
ax.set_yticks(range(len(term_summary)), [f"{k} (n={n})" for k, n in term_summary.n.items()])
ax.set(
    xlim=(0, N + 1),
    xlabel="BatChat rank · 1 = best",
    ylabel="",
    title="Plot ingredients: every matching story, with its median",
)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), frameon=False)
plt.show()
term_summary.drop(columns=["best_rank", "worst_rank"]).rename(columns=PRETTY)

# %% [markdown]
# ### Gotham without "Batman"
#
# The bat below is built from the words in the **481 completely summarized stories**. Larger words appear in more stories; repeating a word within one story adds nothing.
#
# We remove common English words and a short list of character and place names, so the names don't crowd out everything else. **Rankings play no part in these clouds.**

# %%
from matplotlib.colors import ListedColormap
from matplotlib.font_manager import findfont
from matplotlib.path import Path as ShapePath
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
from wordcloud import WordCloud

extra_stopwords = set(
    """batman bruce wayne gotham city robin dick grayson tim drake
    jason todd alfred gordon riddler edward nashton nigma nygma penguin oswald cobblepot
    tells says asks comes goes gets just later soon new man men time way back
    couldn didn doesn isn wasn wouldn don ve ll aren weren hasn hadn haven shouldn needn mustn mightn won shan""".split()
)
vectorizer = CountVectorizer(
    binary=True,
    min_df=3,
    stop_words=sorted(ENGLISH_STOP_WORDS | extra_stopwords),
    token_pattern=r"(?u)\b[a-zA-Z]{3,}\b",
)
word_presence = vectorizer.fit_transform(complete_plots.plot_text)  # stories × words, 1 = present
terms = vectorizer.get_feature_names_out()
story_counts = pd.Series(word_presence.sum(axis=0).A1, index=terms)

# A drawn bat silhouette as the cloud mask; 0 = draw here.
bat_outline = ShapePath(
    [(20, 90), (190, 180), (360, 155), (425, 130), (445, 45), (480, 110), (520, 110), (555, 45),
     (575, 130), (640, 155), (810, 180), (980, 90), (920, 220), (900, 335), (800, 215), (690, 345),
     (580, 300), (500, 475), (420, 300), (310, 345), (200, 215), (100, 335), (80, 220), (20, 90), (20, 90)],
    [1, 3, 3, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 79],
)  # fmt: skip
yy, xx = np.mgrid[:520, :1000]
inside = bat_outline.contains_points(np.column_stack([xx.ravel(), yy.ravel()])).reshape(xx.shape)
bat_mask = np.where(inside, 0, 255).astype("uint8")
font_path = findfont("DejaVu Sans")


def word_cloud(frequencies, mask, colors, max_words):
    return WordCloud(
        mask=mask,
        background_color="white",
        font_path=font_path,
        random_state=42,
        max_words=max_words,
        scale=2,
        prefer_horizontal=1,
        colormap=ListedColormap(colors),
        contour_width=1,
        contour_color="#BBC6D0",
    ).generate_from_frequencies(frequencies)


common_words = story_counts.sort_index().sort_values(ascending=False, kind="stable").head(120)
fig, ax = plt.subplots(figsize=(12, 6.8))
ax.imshow(
    word_cloud(common_words.to_dict(), bat_mask, ["#172C44", "#31587B", "#9A6500", "#547184"], 120)
)
ax.axis("off")
ax.set_title("The vocabulary under the cowl", fontsize=20, pad=14)
fig.text(
    0.5,
    0.10,
    f"{len(complete_plots)} fully summarized stories · larger words appear in more stories",
    ha="center",
    fontsize=11,
)
fig.text(
    0.5,
    0.055,
    "Words from wiki plot summaries, not Batman's dialogue. Color and position carry no data.",
    ha="center",
    fontsize=10,
    color=COLORS["grey"],
)
fig.tight_layout(rect=(0, 0.12, 1, 1))
plt.show()

# %% [markdown]
# ## Same length, different ways to tell a story
#
# *Undone* uses **20 silent pages**. *The Clown at Midnight* uses **22 pages of illustrated prose**. They rank **47th and 85th**: similar lengths, very different reading experiences. [DC on the silent issue](https://www.dc.com/blog/2013/09/05/5-2-reasons-dc-comics-the-new-52-anniversary-edition)
#
# A wiki summary can describe a silent image at length or squeeze pages of dialogue into a sentence. Its word count doesn't measure how wordy the comic is.
#
# ### What a plot summary can't show you
#
# ![Ego artwork: Batman moves among angular black-and-grey towers under an orange sky; a yellow spotlight cuts diagonally across the city.](attachment:ego-study.webp)
#
# Batman almost disappears into the angular black shapes of Gotham. The orange sky separates the towers, and a yellow beam pulls the eye diagonally across the scene.
#
# "Batman above Gotham" captures the subject but loses the composition.
#
# Color also depends on the edition. Richmond Lewis colored *Year One* twice, for different presentations. Studying that difference would require knowing which version the hosts read. [DC on Richmond Lewis](https://www.dc.com/blog/2024/03/29/the-woman-whose-colors-brought-batman-year-one-to-life-twice)
#
# *Darwyn Cooke artwork for Ego, © DC. Small image reproduced by [ComicsXF](https://comicsxf.com/batchat-rankings/); [image source](https://i0.wp.com/www.comicsxf.com/wp-content/uploads/2022/06/batman-ego-666x1024.webp?resize=640%2C984). Included for the visual commentary above.*

# %% [markdown]
# ## A note on creator controversy
#
# The dataset ships a short, cited list (`creator_watch.csv`) of four creators with documented misconduct events. Did the hosts rank their books before or after those events became public?

# %%
creator_watch = pd.read_csv(DATA / "creator_watch.csv")
creators = pd.read_csv(DATA / "creators.csv")
credits = pd.read_csv(DATA / "story_creators.csv")
story_credits = credits[
    credits.credit_scope.eq("selected_narrative")
]  # the ranked story, not backups
watch_links = (
    story_credits.merge(creators[["creator_id", "name"]], on="creator_id", validate="many_to_one")
    .merge(creator_watch, left_on="name", right_on="creator", validate="many_to_one")
    .merge(stories[["story_id", "discussion_date"]], on="story_id", validate="many_to_one")
)
watch_links["after_event"] = pd.to_datetime(watch_links.discussion_date) >= pd.to_datetime(
    watch_links.event_date
)
watch_links.groupby(["name", "role", "event_date"]).agg(
    stories=("story_id", "nunique"), all_discussed_after_event=("after_event", "all")
).reset_index().replace({"role": {"writers": "Writer", "editors": "Editor"}}).rename(
    columns={
        "name": "Creator",
        "role": "Role",
        "event_date": "Recorded event date",
        "stories": "Stories",
        "all_discussed_after_event": "All discussed after event?",
    }
)

# %% [markdown]
# After, in every case: Eddie Berganza edited 26 of these stories and Warren Ellis wrote two, all discussed once the events were public. So there is no before-and-after comparison to make here. Absence from the list means unreviewed, not cleared.
#
# ## Takeaways
#
# - Summaries cover the 1980s almost completely and the 2020s barely at all, so any text analysis leans old.
# - Vampires, time travel, and amnesia are premises, not predictors: each spreads across the whole ranking.
# - Elseworlds and original graphic novels sit all over the list; a format is not a quality signal.
# - The clouds show what wiki summaries sound like ("takes", "finds", "police"), not what the comics sound like.
#
# **More BatChat notebooks:** [Who gets the good Batman stories?](https://www.kaggle.com/code/danofer/who-gets-the-good-batman-stories) · [Gotham's rogues, ranked](https://www.kaggle.com/code/danofer/gotham-s-rogues-ranked) · [Can a computer predict BatChat's favorites?](https://www.kaggle.com/code/danofer/batchat-s-favorite-batman-stories) · [BatChat vs the crowd](https://www.kaggle.com/code/danofer/batchat-vs-the-crowd-where-batman-fans-disagree) · [The dataset](https://www.kaggle.com/datasets/danofer/batchat-batman-rankings)
#
# If you enjoyed this, an upvote helps other Batman fans find it.
