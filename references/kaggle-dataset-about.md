BatChat takes >740 Batman stories and ranks them from best (1) to worst. It's hosted by Matt Lazorwitz and Will Nevin on [ComicsXF](https://comicsxf.com/batchat-rankings/).
BatRank links these stories to creators, characters, awards, plot, and ratings.

**Start with `stories.csv`. Rank 1 is best.**

| Table | Contents |
|---|---|
| `stories.csv` | 740 ranked stories and their features |
| `issues.csv` | 2,434 issue references within those stories |
| `creators.csv` | 1,847 creator name records, including flagged studios |
| `story_creators.csv` | 19,466 story–creator–role links, with attribution scope |
| `creator_awards.csv` | 311 creator-to-award-event links |
| `story_texts.csv` | 2,637 selected synopsis or missing-text records |

Join story tables on `story_id` and creator tables on `creator_id`. Use `credit_scope='selected_narrative'` for the people who worked on the selected stories. Award links use `event_id` to join `award_events.csv`. Smaller curated tables add issue labels (`story_labels.csv`), animal sightings (`animal_watch.csv`), Mad Hatter's reviewed story roles (`hatter_story_roles.csv`), and a cited creator-controversy list (`creator_watch.csv`).

The text table contains **1,711 available summaries totaling 703,219 words**; these are wiki contributors’ plot descriptions. Recent comics have thinner coverage.


By [Dan Ofer](https://scholar.google.com/citations?user=uDx2ItYAAAAJ). [Code and notebooks on GitHub](https://github.com/ddofer/BatRank).

Source links and column descriptions are included. The sources have different terms; redistribution rights have not been cleared for the combined bundle.
I'll try to update as the rankings progress, they've got stories for years!

### Start with the EDA

- [Who Gets the Good Batman Stories?](https://www.kaggle.com/code/danofer/who-gets-the-good-batman-stories)
- [BatChat vs the Crowd: Where Batman Fans Disagree](https://www.kaggle.com/code/danofer/batchat-vs-the-crowd-where-batman-fans-disagree)
- [BatChat's Favorite Batman Stories?](https://www.kaggle.com/code/danofer/batchat-s-favorite-batman-stories)
