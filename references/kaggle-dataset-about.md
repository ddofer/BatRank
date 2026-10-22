BatChat takes >740 Batman stories and ranks them from best (1) to worst. It's hosted by Matt Lazorwitz and Will Nevin on [ComicsXF](https://comicsxf.com/batchat-rankings/).
BatRank links these stories to creators, characters, awards, plot, and ratings.

**Start with `stories.csv`. Rank 1 is best.**

| Table | Contents |
|---|---|
| `stories.csv` | 740 ranked stories; 21 columns with rank and title first |
| `story_features.csv` | Specialist features and provenance; join one-to-one on `story_id` |
| `issues.csv` | 2,434 issue references within those stories |
| `creators.csv` | 1,847 creator name records, including flagged studios |
| `story_creators.csv` | 19,466 story–creator–role links, with attribution scope |
| `creator_awards.csv` | 311 creator-to-award-event links |
| `story_texts.csv` | 2,637 selected synopsis or missing-text records |

Start with the compact `stories.csv`; add `story_features.csv` for cast, awards, outside ratings and their match scopes. Join story tables on `story_id` and creator tables on `creator_id`. Use `credit_scope='selected_narrative'` for the people who worked on the selected stories. Award links use `event_id` to join `award_events.csv`. Smaller curated tables add issue labels (`story_labels.csv`), animal sightings (`animal_watch.csv`), Mad Hatter's reviewed story roles (`hatter_story_roles.csv`), and a cited creator-controversy list (`creator_watch.csv`).

Outside ratings are available for 70 Goodreads matches, 390 stories on RoundUp readers, and 227 on RoundUp critics. Complete same-story and review-count checks leave comparison samples of 52, 147, and 110. Coverage is curated and differs by era and edition.

The text table contains **1,711 available summaries totaling 703,219 words**; these are wiki contributors’ plot descriptions. Recent comics have thinner coverage.


By [Dan Ofer](https://scholar.google.com/citations?user=uDx2ItYAAAAJ). [Code and notebooks on GitHub](https://github.com/ddofer/BatRank).

Source links and column descriptions are included. The sources have different terms; redistribution rights have not been cleared for the combined bundle.
I'll try to update as the rankings progress, they've got stories for years!

### Notebooks

- [Who Gets the Good Batman Stories?](https://www.kaggle.com/code/danofer/who-gets-the-good-batman-stories) — writers, artists, letterers, eras
- [Gotham's Rogues, Ranked](https://www.kaggle.com/code/danofer/gotham-s-rogues-ranked) — heroes, villains, the Mad Hatter trick, villain word clouds
- [What Batman Plots Are Made Of](https://www.kaggle.com/code/danofer/what-batman-plots-are-made-of) — series, Elseworlds, plot-summary coverage, the bat word cloud
- [BatChat vs the Crowd](https://www.kaggle.com/code/danofer/batchat-vs-the-crowd-where-batman-fans-disagree) — where Goodreads readers and critics disagree with the hosts
- [Can a Computer Predict BatChat's Favorites?](https://www.kaggle.com/code/danofer/batchat-s-favorite-batman-stories) — regression, plot words, the misses
- [What Pushes a Batman Story Up BatChat's List?](https://www.kaggle.com/code/danofer/what-pushes-a-batman-story-up-batchat-s-list) — model weights, stability checks, SHAP breakdowns

- [Which Batman Stories Deserve a Second Look?](https://www.kaggle.com/code/danofer/which-batman-stories-deserve-a-second-look) — 20 reranking discussion candidates, including ten from early episodes
