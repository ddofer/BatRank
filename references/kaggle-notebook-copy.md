# Kaggle copy-and-paste pack

Start with the comics EDA below. The prediction and audience notebooks each have their own introduction afterward. Copy the contents of a fenced block into the corresponding field or Markdown cell. The introductions replace the existing opening cell; they are not extra prefaces. Keep the code and subsequent analysis cells.

These blocks use the **21 October 2026 snapshot**. The private drafts are linked in the sharing guide. Upload and runtime instructions are in the [sharing guide](kaggle-sharing.md).

## Comics EDA — notebook 2

**Title**

```text
Who Gets the Good Batman Stories?
```

**Short description**

```text
Which writers and villains turn up in the best Batman stories? Explore 740 rankings, creative teams, and plot words.
```

**Opening Markdown cell**

```markdown
# Who gets the good Batman stories?

Which writers, artists, and characters turn up in BatChat's favorites? Which series have the strongest showing? And how much changes when we compare books from the same decade?

These are **740 stories ranked by Matt Lazorwitz and Will Nevin** on [BatChat](https://comicsxf.com/batchat-rankings/). **Rank 1 is best. Lower is better throughout.** Start with the leaderboards, then look at eras, creative teams, and plots.

By [Dan Ofer](https://scholar.google.com/citations?user=uDx2ItYAAAAJ). [Dataset](https://www.kaggle.com/datasets/danofer/batchat-batman-rankings) · [Code and sources](https://github.com/ddofer/BatRank).
```

## Prediction — notebook 1

**Title**

```text
Can We Predict BatChat’s Favorite Batman Stories?
```

**Short description**

```text
Can creator names, publication dates, or plot words predict BatChat’s taste? Start with a simple guess and inspect the stories the models get wrong.
```

**Opening Markdown cell**

```markdown
# Can we predict BatChat's favorite Batman stories?

*Undone* ranks **47th** among BatChat's 740 Batman stories. Two models put it near **490th**. They know who made it and when it appeared. They don't know how a silent comic about grief reads.

Can names and dates predict the hosts' taste? Do plot summaries help? And what can we learn from the stories the models get wrong?

We'll start with a simple guess, test a few improvements, and inspect the misses. **Rank 1 is best.**

New to the dataset? Start with [the writers, years, and villains](https://www.kaggle.com/code/danofer/who-gets-the-good-batman-stories). For reader and critic ratings, see [BatChat versus the crowd](https://www.kaggle.com/code/danofer/batchat-vs-the-crowd-where-batman-fans-disagree).

*Part of [BatRank](https://github.com/ddofer/BatRank), by [Dan Ofer](https://scholar.google.com/citations?user=uDx2ItYAAAAJ). Rankings: [Matt Lazorwitz and Will Nevin's BatChat](https://comicsxf.com/batchat-rankings/). Snapshot: October 21, 2026.*
```

## Audience comparison — notebook 3

**Title**

```text
BatChat vs the Crowd: Where Batman Fans Disagree
```

**Short description**

```text
BatChat loves Red Rain. Goodreads prefers White Knight. Compare the podcast with readers and critics, then see what changes when everyone gets the same books.
```

**Opening Markdown cell**

```markdown
# BatChat vs the crowd: where Batman fans disagree

*Red Rain* is **#6** on BatChat's list. On Goodreads, it gets **3.66/5**. *White Knight* gets **4.28/5**, but BatChat puts it at **#734**. [Goodreads: Red Rain](https://www.goodreads.com/book/show/72479.Batman_Dracula) · [White Knight](https://www.goodreads.com/book/show/37775321-batman)

Which other books divide the podcast and its fellow readers? And do the hosts agree more with readers or critics?

We'll compare [740 stories ranked by Matt Lazorwitz and Will Nevin on BatChat](https://comicsxf.com/batchat-rankings/) with Goodreads and Comic Book RoundUp. **Rank 1 is best. Higher outside ratings are better.** The data is a snapshot from **21 October 2026**.

*By [Dan Ofer](https://scholar.google.com/citations?user=uDx2ItYAAAAJ), as part of [BatRank](https://github.com/ddofer/BatRank). [Start with the Batman EDA](https://www.kaggle.com/code/danofer/who-gets-the-good-batman-stories) for writers, eras, heroes, and villains.*
```

## Source note — optional

```markdown
Rankings: [ComicsXF’s BatChat](https://comicsxf.com/batchat-rankings/). Metadata and plot summaries: primarily [DC Database](https://dc.fandom.com/), with other sources linked in the tables. [Dataset](https://www.kaggle.com/datasets/danofer/batchat-batman-rankings) · [Code and notebooks](https://github.com/ddofer/BatRank).
```

## Dataset page — compact description

**Title**

```text
BatRank: A BatChat Batman Ranking Dataset
```

**Subtitle**

```text
Creative teams, characters, outside ratings, and 700,000 words of plot summaries
```

**Description**

```markdown
**BatRank** connects **740 stories ranked by BatChat** to their creators, characters, publication history, awards, plot summaries, and outside ratings. It uses the **21 October 2026** snapshot of [ComicsXF’s list](https://comicsxf.com/batchat-rankings/), hosted by Matt Lazorwitz and Will Nevin.

**Start with `stories.csv`. Rank 1 is best.** The tables identify who worked on each story, separating them from contributors to unrelated stories in the same issue.

| Table | Contents |
|---|---|
| `stories.csv` | 740 ranked stories and their features |
| `issues.csv` | 2,434 issue references within those stories |
| `creators.csv` | 1,847 creator name records, including flagged studios |
| `story_creators.csv` | 19,466 story–creator–role links, with attribution scope |
| `creator_awards.csv` | 311 creator-to-award-event links |
| `story_texts.csv` | 2,637 selected synopsis or missing-text records |

Join story tables on `story_id` and creator tables on `creator_id`. Use `credit_scope='selected_narrative'` for the people who worked on the selected stories. Award links use `event_id` to join `references/award_events.csv`.

The text table contains **1,711 available summaries totaling 703,219 words**, with no length cap. Some text is available for **587 stories**. Every selected summary is available for **481 stories with complete issue lists**. These are wiki contributors’ plot descriptions. Recent comics have much thinner coverage.

The companion notebooks explore heroes and villains, creative teams, audience disagreements, and small predictive models. They include a cast atlas, shaped word clouds, and a bag-of-words experiment.

By [Dan Ofer](https://scholar.google.com/citations?user=uDx2ItYAAAAJ). [Code and notebooks on GitHub](https://github.com/ddofer/BatRank).

Source links, a data dictionary, and validation notes are included. The sources have different terms; redistribution rights have not been cleared for the combined bundle. It is not a CC0 dataset. See the source notes and sharing guide for the current status.
```

The [sharing guide](kaggle-sharing.md) links the drafts and explains setup and source terms.
