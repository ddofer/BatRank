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
Writers, artists, years, heroes, and villains across 740 ranked Batman stories. Includes a cast atlas and Batman-shaped word clouds.
```

**Opening Markdown cell**

```markdown
# Who gets the good Batman stories?

Doug Moench and Kelley Jones made both *Red Rain* and *Unseen*. BatChat ranks them **710 places apart**: #6 and #716. Same writer, same artist, very different results.

We'll start with writers, characters, and publication years. Then we'll look at artistic partnerships, coloring, lettering, and what plot summaries miss.

The data contains **740 stories ranked by BatChat**, the Batman podcast hosted by Matt Lazorwitz and Will Nevin. Each row is one story. **Rank 1 is best.** We use the **2026-10-21** snapshot of [ComicsXF's list](https://comicsxf.com/batchat-rankings/).



*Part of [BatRank](https://github.com/ddofer/BatRank), by [Dan Ofer](https://scholar.google.com/citations?user=uDx2ItYAAAAJ).*
```

## Prediction — notebook 1

**Title**

```text
Can We Predict BatChat’s Favorite Batman Stories?
```

**Short description**

```text
BatChat ranks the silent story Undone at #47. Two models put it around #490. Can writers, artists, publication dates, or plot words explain the miss?
```

**Opening Markdown cell**

```markdown
# Can we predict BatChat's favorite Batman stories?

*Undone*, a silent story about grief, ranks **47th** on BatChat's list. Two models using its creators and publication details put it around **490th**. What are they missing?

We have **740 ranked stories** from Matt Lazorwitz and Will Nevin's Batman podcast, with writer and artist names, characters, publication dates, awards, and roughly **700,000 words of wiki plot summaries**. We'll test how much these tell us about the hosts' taste, including whether the models cope with unfamiliar artists and later episodes.

**Rank 1 is best.** Everything runs from the supplied snapshot.




*Part of [BatRank](https://github.com/ddofer/BatRank), by [Dan Ofer](https://scholar.google.com/citations?user=uDx2ItYAAAAJ).*
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

BatChat ranks *Red Rain* sixth, despite its **3.66/5 on Goodreads**. *White Knight* gets **4.28**, yet lands at **#734** on the podcast's list. That's a substantial disagreement about what makes a good Batman comic. [Red Rain rating](https://www.goodreads.com/book/show/72479.Batman_Dracula) · [White Knight rating](https://www.goodreads.com/book/show/37775321-batman)

We'll compare the [BatChat podcast's rankings](https://comicsxf.com/batchat-rankings/) with Goodreads readers, Comic Book RoundUp readers, and RoundUp critics. The dataset contains **740 stories**, captured on **21 October 2026**; **rank 1 is best**. Some disagreements recur across all three sources. The apparent difference between reader and critic agreement, though, largely disappears when we compare the same books.

Everything runs from the attached snapshot. These are retrospective comparisons: outside ratings may postdate the episode, and each platform attracts its own audience.



*Part of [BatRank](https://github.com/ddofer/BatRank), by [Dan Ofer](https://scholar.google.com/citations?user=uDx2ItYAAAAJ).*
```

## Shared closing cell — optional for each notebook

```markdown
## Data, sources, and reuse

The rankings come from [ComicsXF’s BatChat list](https://comicsxf.com/batchat-rankings/), hosted by Matt Lazorwitz and Will Nevin. Issue metadata and plot summaries come primarily from [DC Database](https://dc.fandom.com/). The dataset retains source and revision links. Other sources include official award archives, publisher records, a small Grand Comics Database sample, Goodreads, and Comic Book RoundUp.

Start with `data/processed/stories.csv`. Join story tables using `story_id`. Creator tables use `creator_id`. Full summaries are in `story_texts.csv`; an explicit status records missing text. Empty fields mean unknown or inapplicable.

The attached files include a README, data dictionary, source notes, and validation reports. The analysis runs from those saved tables without live scraping. The local package versions are pinned in `uv.lock`.

This is an independent analysis of one podcast’s reading list. Sources retain their respective terms and attribution requirements. See the bundled source notes before redistributing the material.

Which pair of books would you compare next? A useful suggestion names the stories and a difference worth examining: pacing, characterization, page layout, coloring, or something these tables miss.
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
