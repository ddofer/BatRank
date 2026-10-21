# Catalogue enrichment: what we obtained, and what the sample can establish

Research and collection date: 2026-10-21. Sources: the Grand Comics Database (GCD), Metron's official API documentation, and live read-only service checks. No account creation or authentication bypass was attempted.

## Result

`data/external/catalogue.json` contains **30 selected narrative units across 22 BatChat entries**. Seventeen entries have a complete narrative page total supported by original-issue records. Five retain partial or reprint-only evidence with explicit coverage. This is a purposive bibliographic sample, chosen to check high and low ranks, backup stories, illustrated prose, silent comics, and edition scope. It does not estimate page-count coverage or length effects for the complete ranking.

The file preserves individual evidence records and exports two joinable lists: `stories` keyed by `story_id`, and `issues` keyed by `story_id, requested_title`. `python -m scripts.catalogue` rebuilds these from cached indexed records and the checked crosswalk in `data/raw/catalogue/matches.json`.

| Ranked entry | Narrative pages | Why the distinction matters |
|---|---:|---|
| Year One | 90 | Four narratives of 22, 22, 22 and 24 pages, rather than four physical issues of 36 pages. [Original chapter one](https://www.comics.org/issue/42449/), [two](https://www.comics.org/issue/42568/), [three](https://www.comics.org/issue/42687/), [four](https://www.comics.org/issue/42811/) |
| Ego | 62 | The original object is a 68-page physical publication. Its narrative is smaller, and *Ego & Other Tails* is a larger anthology. [Original](https://www.comics.org/issue/291254/) |
| Cold Days | 62 | Three parts of 20, 20 and 22 pages. [Part one](https://www.comics.org/issue/1825080/), [two](https://www.comics.org/issue/1830523/), [three](https://www.comics.org/issue/1836082/) |
| Undone | 20 | GCD identifies the actual comic narrative separately from cover art and house material. This is the silent Batman and Robin #18 story. [Original issue](https://www.comics.org/issue/1094409/) |
| The Clown at Midnight | 22 | GCD classifies it as a **text story**; its page count should not imply the same reading experience as a 22-page conventional comic. [Original issue](https://www.comics.org/issue/329763/) |
| Night of the Stalker | 14 | It appears inside a 100-page issue containing unrelated reprints. [Original issue](https://www.comics.org/issue/27196/) |
| Death Casts the Deciding Vote / The Silent Night of Batman | 22.17 | The ranked entry names **both** Batman stories: 14.17 + 8 pages. A third, unrelated four-page Phantom Stranger reprint is excluded. [Original issue](https://www.comics.org/issue/23317/) |
| Gotham Knights Black & White collection | 8 sampled; full total missing | Only the eight-page *To Become the Bat* backup is sampled from #1. The 23-page *Constants* main story has different creators and is excluded. This covers one of sixteen ranked references. [Original issue](https://www.comics.org/issue/73848/) |
| Dreadful Reins | 64 | A complete long single narrative, rather than an ordinary monthly installment. [Original issue](https://www.comics.org/issue/2425702/) |
| Three Jokers | 144 | Three 48-page narratives; comparison by issue count alone disguises the reading length. [Book one](https://www.comics.org/issue/2139088/), [two](https://www.comics.org/issue/2150785/), [three](https://www.comics.org/issue/2159129/) |

The remaining complete totals are *Some of These Days* (38), *The Joker's Five-Way Revenge* (22.5), *To Kill a Legend* (19), *The Beautiful People* (22), *Mad Love* (64), *The Nobody* (24), *There Is No Hope in Crime Alley* (12), and *Earth One* (138). Their individual source URLs are retained in the JSON records. *White Knight* and *The Last Arkham* have only their first installment sampled; neither receives a complete total. *The Killing Joke* and *Silent, But Deadly* have same-narrative reprint evidence, which does not populate original-issue dates or complete-original totals.

## Acquisition and access

**GCD:** direct requests to `https://www.comics.org/robots.txt` and the known Batman #219 issue page returned Cloudflare HTTP 403 challenges. The script did not retry with a browser disguise, alternate endpoint, challenge solver, or another host. Ordinary web search did expose indexed first-party GCD records. Those returned texts are cached under `data/raw/catalogue/*.txt`, and the evidence is labeled `acquisition_mode=indexed_primary_record`. These are indexed snapshots, not successful live HTML/API downloads: their omissions and possible staleness remain explicit.

Discovery used exact series, issue and narrative names. Selection then checked **issue identity, GCD issue identifier, sequence number and narrative title**. Identically named stories are not sufficient: searches for *Silent, But Deadly* returned unrelated Marvel stories, which were discarded. Public catalogue URLs and sequence indices identify the records precisely. A GCD issue ID is not a GCD story ID.

The parser ignores search snippets, cover/advertisement sequences and clipped text that cannot be attached directly to a narrative heading. Duplicate list/grid results are collapsed by issue ID, sequence and title. Raw credit strings preserve attribution qualifiers, uncertainty and adjacent credited names; they are not guessed into clean contributor lists. Whole-issue editor credits are not silently reassigned to individual substories.

**Metron:** no `METRON_USERNAME`, `METRON_PASSWORD` or `METRON_TOKEN` was present. Only their presence was checked; no secret values were printed. A single unauthenticated request to the documented issue endpoint returned HTTP 401 with an authentication-required response. Metron's robots file permitted the public catalogue/search routes for the research user agent, but the home page and a public search URL returned an Anubis challenge page with HTTP 200. HTTP status alone therefore does not prove usable catalogue access. No challenge was solved and no Metron metadata was imported. Exact indexed searches also returned no usable records for the sampled books.

The [official Metron API documentation](https://github.com/Metron-Project/metron/blob/master/api/README.md) describes authenticated read access, issue filters, role-specific creator credits, store and cover dates, page counts, characters, universes, arcs, reprints and GCD/Comic Vine identifiers. It also documents attribution and conditional-request fields. Those capabilities make Metron a reasonable next enrichment source **when authorized credentials are available**; the live sample establishes access requirements, not Batman catalogue coverage. Metron issue page counts are not documented as exact ranked-substory page counts, so they would still need scope checks.

## Measurement cautions

1. Narrative pages and physical issue pages remain separate. Covers, ads, columns and unrelated backups do not count toward ranked narrative length.
2. Fractional pages are retained. GCD records 14.17 pages for the original *Death Casts the Deciding Vote* while an indexed *Showcase Presents* reprint records 14.5. The original source is used; the values are not rounded to fourteen or silently reconciled. [Original](https://www.comics.org/issue/23317/), [reprint](https://www.comics.org/issue/901343/)
3. An on-sale date belongs to a particular issue/edition and may differ across direct-market and newsstand records. It is not a cover date, and collection publication dates are not imported as original story dates.
4. A same-title reprint can have changed pagination, coloring, translation or supplements. For example, discovered *Cacophony* collection records do not provide consistent per-part pagination across editions; they were not included in the checked sample. Edition alignment must precede totals.
5. The GCD sample was selected deliberately. A length/rank regression on these seventeen complete cases would mostly model selection decisions. The sample is useful for case studies and measurement checks, not a population claim.
6. Missing fields in an indexed excerpt mean unavailable evidence, not absence of a credit, reprint or character.

## Rights and attribution

GCD's first-party page footers license database content under **CC BY-SA 4.0**, excluding separately reserved material such as cover images. This enrichment includes bibliographic facts and short credit strings, not downloaded covers or copied plot summaries. Preserve GCD attribution, individual source URLs, the [license link](https://creativecommons.org/licenses/by-sa/4.0/) and change notices when redistributing adaptations. No license is inferred for other sources from GCD's terms. [GCD's own footer on a sampled record](https://www.comics.org/issue/23317/)

Creator award records belong in their own provenance-bearing enrichment. A person winning an Eisner, a series winning an Eisner and this particular narrative winning an Eisner are different variables; this catalogue sample does not conflate or invent them.

## Official publisher fallback

Five otherwise unresolved entries now have separate `publisher_*` features and evidence in `publisher_records`. These do **not** fill GCD narrative-page fields or imply complete wiki coverage. Public DC pages were available through ordinary browsing; direct Python requests received HTTP 403, which was not bypassed. Cached first-party page text supplies the parser.

| Ranked entry | Publisher physical pages | Edition on-sale date | Scope |
|---|---:|---|---|
| Through the Looking Glass | 112 | 2012-01-11 | Exact original graphic novel; Bruce Jones, Sam Kieth, colorists Sam Kieth/David Baron, DC Lettering. [Publisher](https://www.dc.com/graphic-novels/batman-through-the-looking-glass) |
| The Jiro Kuwata Batmanga Book 1 | 352 | 2014-12-03 | English restored collection, written and illustrated by Jiro Kuwata. The edition date is not its original Japanese serialization date. [Publisher](https://www.dc.com/graphic-novels/batman-the-jiro-kuwata-batmanga-2014/batman-the-jiro-kuwata-batmanga-book-1) |
| Injustice: Gods Among Us Vol. 1 | 192 | 2013-11-13 | Hardcover collecting print issues #1–6, written by Tom Taylor; credited artists Jheremy Raapack and Mike S. Miller. [Publisher](https://www.dc.com/graphic-novels/injustice-gods-among-us-2013/injustice-gods-among-us-vol-1) |
| Black and White Vol. 3 | 288 | 2007-05-16 | Anthology with separately listed writers/artists. Not the later Black & White miniseries. The product description does not specify a complete issue mapping. [Publisher](https://www.dc.com/graphic-novels/batman-black-and-white-1997/batman-black-and-white-vol-3) |
| Draining | 264 for its containing collection | 2020-02-05 | **Contains-ranked-story** match to *Batman Arkham: Victor Zsasz*. The publisher identifies a previously unpublished Devin Grayson/Roger Robinson story intended for Gotham Knights #12. The collection's length and edition date are not silently assigned as Draining's narrative length or original planned date. [Publisher](https://www.dc.com/graphic-novels/batman-arkham-victor-zsasz) |

These are product metadata facts and credited names only. Publisher descriptions and artwork are not reproduced in the canonical dataset. DC does not acquire GCD's CC BY-SA license by being included in the same JSON; the source-specific rights note remains explicit. Generic `Various` placeholders are excluded from creator names, and line-wrapped adjacent credits are split at their original source line markers.

## Checks

Seven focused tests cover fractional narrative versus physical page counts, comic versus text stories, clipped records, duplicate views, exact issue identity, reprint date isolation, complete versus partial reading-list coverage, publisher credit parsing and publisher anthology scope. The crosswalk rejects unknown canonical issue associations. For any future broader acquisition, authenticated APIs or approved GCD exports are preferable to scaling indexed search snapshots.

## Notebook domain fact-check

The rewritten notebooks were checked against the canonical rows and primary source records. The paired Batman #219 unit is 22.17 narrative pages; its *Silent Night* component alone is eight. *Undone* is twenty comic-story pages; *Clown at Midnight* is twenty-two text-story pages. The [publisher's 2013 retrospective](https://www.dc.com/blog/2013/09/05/5-2-reasons-dc-comics-the-new-52-anniversary-edition) explicitly identifies Batman and Robin #18 as a silent issue.

The Puckett/Parobeck comparison consists of comics tied to the animated continuity, including Barbara Gordon and Dick Grayson stories, not animated episodes. The Puckett/Scott comparison contains Cassandra Cain's introduction in Batman #567/Detective #734 and two Batgirl entries. It should not be described as a controlled same-character comparison. DC's [Batman Adventures Vol. 2 catalogue](https://www.dc.com/graphic-novels/batman-adventures-1992/batman-adventures-vol-2) identifies the animated-series connection; its [Scott retrospective](https://www.dc.com/blog/2023/02/23/power-on-page-six-dc-comics-by-black-creators) identifies Puckett, Scott, Cassandra and Batman #567.

The canonical Goodreads snapshot has *Red Rain* at 3.66 and *White Knight* at 4.28, against BatChat ranks 6 and 734. Their [Goodreads Red Rain](https://www.goodreads.com/book/show/72479.Batman_Dracula) and [White Knight](https://www.goodreads.com/book/show/37775321-batman) URLs should accompany those comparisons. They remain retrospective snapshot values. DC's [White Knight collected-edition page](https://www.dc.com/graphic-novels/batman-white-knight-2017/batman-white-knight) confirms that the collection contains all eight issues. The [original announcement quoting Murphy](https://www.dc.com/blog/2017/07/07/sean-murphy-s-batman-white-knight-arrives-october-4) supports the political premise, but announced seven issues before the completed series expanded to eight; it should not supply the final issue count.

The coloring comparison is supported by DC's [Absolute Killing Joke edition](https://www.dc.com/graphic-novels/absolute-batman-the-killing-joke), which includes the original colors and Bolland's later version. GCD's [2008 Deluxe Edition record](https://www.comics.org/issue/510483/) identifies John Higgins as the original colorist and Bolland's subsequent recoloring and reconstruction. Calling these the same narrative does not establish identical visual presentation or supplementary contents across Goodreads editions.
