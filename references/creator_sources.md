# Creator attributes: sources, identity and precision

Reviewed 2026-10-21. Creator identity is resolved independently of demographic values. Public names in a credit are not evidence of age or gender.

## Practical acquisition

**Current source: DC Database Staff Template through the existing MediaWiki API.** The root extractor's live samples returned HTTP 200 and explicit `Gender`, `YearOfBirth`, `MonthOfBirth`, `DayOfBirth`, corresponding death components, `CountryOfBirth`, `CityOfBirth`, `OfficialWebsite`, `First`, `Employers`, `Titles`, `RealName` and `Pseudonyms` fields. Retain the page ID, exact template value, revision ID/timestamp and permanent revision URL. A matched `Staff Template` provides much better comics-specific identity context than a generic same-name web result. A non-staff page or a missing page does not supply person metadata.

Staff pages are community-maintained secondary sources, not first-person declarations or publisher personnel records. They can be incomplete and unreferenced. For example, [Richmond Lewis's staff page](https://dc.fandom.com/wiki/Richmond_Lewis) explicitly records Female and Colorist, without a birth date; it provides no visible references supporting those fields. Preserve that source distinction. Wiki categories, pronouns, photographs, names and occupation are not substitutes for an explicit demographic field. Historical creator credits do not make today's gender statement a historical observation at publication.

**Optional structured supplement: Wikidata.** A single live `wbgetentities` request successfully resolved seven exact English Wikipedia titles and returned labels, descriptions, sitelinks, revisions and claims. A subsequent sample also succeeded. Later requests received HTTP 429, including attempts with `maxlag=5`; further probing stopped. The successful original raw JSON was not retained before its process exited, so there is no reproducible raw snapshot for this probe. The identity examples below are research observations, not a claim of Wikidata enrichment coverage in the released tables. Root acquisition owns any subsequent requests and caching.

Use the documented [Wikidata data-access interfaces](https://www.wikidata.org/wiki/Wikidata:Data_access): batch known titles/IDs, use an informative user agent, cache, keep requests serial, and honor `Retry-After`. API errors need inspection even when HTTP succeeds. Structured Wikidata data is CC0; this does not change the license of copied Wikipedia prose or Fandom content.

The successful request shape was:

```python
params = {
    "action": "wbgetentities", "sites": "enwiki",
    "titles": "Grant Morrison|Frank Miller|Darwyn Cooke|Doug Moench|Richmond Lewis|Lynn Varley|Rachel Pollack",
    "props": "info|labels|descriptions|claims|sitelinks",
    "languages": "en", "format": "json",
}
# GET https://www.wikidata.org/w/api.php
```

Useful claim fields are `P569` (birth), `P570` (death), `P21` (sex or gender), `P166` (award received), `P106` (occupation), and `P31` (instance of). Keep statement IDs, ranks, qualifiers, reference snaks, entity revision and retrieval time alongside extracted values. References may contain `P854` URLs, `P248` source items, `P143` Wikimedia imports and `P813` retrieval dates. A nonempty reference list is not necessarily an independent primary citation.

## Live examples that should shape the parser

| Creator | Verified Wikidata ID | Observed issue |
|---|---|---|
| Grant Morrison | [Q943047](https://www.wikidata.org/wiki/Q943047) | Two normal-rank P21 values: non-binary (`Q48270`) and genderqueer (`Q12964198`). Preserve both. Birth is 1960-01-31, day precision. |
| Frank Miller | [Q207676](https://www.wikidata.org/wiki/Q207676) | Comics writer/artist/director; birth 1957-01-27, day precision. Exact enwiki title is `Frank Miller`, not a guessed disambiguation title. |
| Darwyn Cooke | [Q1166960](https://www.wikidata.org/wiki/Q1166960) | Birth has a preferred day-precision 1962-11-16 statement and a normal year-precision 1962 statement. Death is 2016-05-14. The sampled DC staff template supplied only birth year/month. Do not force sources to agree by inventing a day. |
| Doug Moench | [Q718507](https://www.wikidata.org/wiki/Q718507) | Birth 1948-02-23, day precision; comics-writer identity corroborates the credit. |
| Richmond Lewis | [Q7330907](https://www.wikidata.org/wiki/Q7330907) | No P569 birth statement. P21 female exists but has no references. Unknown birth stays unknown; record this gender value as a Wikidata assertion, not a sourced first-person declaration. |
| Lynn Varley | [Q5361569](https://www.wikidata.org/wiki/Q5361569) | Wikidata supplied 1958-03-11; the sampled DC template had no birth date. Source-specific values and coverage must remain distinguishable. |
| Rachel Pollack | [Q434138](https://www.wikidata.org/wiki/Q434138) | Preferred DOB 1945-08-17 and normal year-only 1945; death 2023-04-07. P21 is trans woman (`Q1052281`) with references. Preserve the actual public label rather than silently converting it to a binary variable. |

Wikidata's [date model](https://www.wikidata.org/wiki/Help:Dates) carries explicit precision and calendar information. Precision 9 means year, 10 month, 11 day; `+1962-01-01` with precision 9 does **not** establish a January 1 birthday. Do not pass arbitrary placeholder days into an exact-age calculation. Prefer a year-based age proxy when either the book date or birth date has only year precision, and label it accordingly. Posthumous publication or reprints do not establish the age at which the original work was made.

The [rank documentation](https://www.wikidata.org/wiki/Help:Ranking) permits multiple preferred values. For a point estimate, select non-deprecated preferred statements if available, otherwise non-deprecated normal statements. If incompatible values remain, preserve the alternatives or mark the scalar unresolved; never take the first statement. Rank is not a source-quality score.

`P21` is explicitly [sex or gender](https://www.wikidata.org/wiki/Property:P21), with multiple permitted labels; it is not a uniform binary measurement across people. Keep raw values and source evidence. Missing, unknown-value and no-value snaks are distinct API states. A current source statement need not describe public disclosure, identity or categorization at the time a historical comic appeared. Do not infer disclosure dates from snapshot dates.

`P166` claims can include award-year (`P585`) and for-work (`P1686`) qualifiers; the probe contained both dated and undated awards. They are incomplete career records and may mix honors, prizes for work and other recognition. Keep the project's reviewed award-event table authoritative for its existing features rather than replacing it with a count of arbitrary P166 statements.

## Name collisions observed during research

These errors survive an overly broad “human + writer/editor occupation” check:

- [Scott Peterson (writer)](https://en.wikipedia.org/wiki/Scott_Peterson_(writer)) and Wikidata `Q7437050` identify the foreign correspondent Scott Daniel Peterson. The Batman editor is [Scott Peterson (comics)](https://en.wikipedia.org/wiki/Scott_Peterson_(comics)), Scott James Peterson. The undifferentiated name also identifies a convicted murderer.
- [Bill Oakley (comics)](https://en.wikipedia.org/wiki/Bill_Oakley_(comics)) is the letterer; plain Bill Oakley / `Q862352` identifies the television writer.
- [Dave Stewart (comics)](https://en.wikipedia.org/wiki/Dave_Stewart_(comics)) redirects to Dave Stewart (artist), the colorist. Musician entities `Q384206` and `Q325389` are wrong for these credits.
- [Alan Grant (writer)](https://en.wikipedia.org/wiki/Alan_Grant_(writer)) is the Batman writer. `Q2543708` identifies the Jurassic Park character, and `Q130602907` is another Alan Grant, not a verified comics match.
- A Mark Doyle search returned physicist `Q109375486`; do not attach it to DC's editor merely because a name matches.

`references/creator_matches.json` keeps only positively reviewed QID mappings and a few verified title/disambiguation rules. Its provenance supports identity links, not a guarantee that all demographic statements on an entity are correct. Exact canonical staff-page matching, reviewed aliases and explicit missingness are safer than accepting an external search engine's highest result.
