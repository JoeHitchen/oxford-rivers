# Spec: Thames Water sewage discharge monitoring

Status: **DRAFT v6 - all questions decided, ready for final sign-off** - nothing has been implemented.

**Decided:** Q2 - include the Thames and its tributaries above Osney, the Cherwell catchment and the Seacourt Stream. All other recommendations agreed, except as superseded by the review feedback below.

**Review feedback applied (v3):**
* Event fields renamed to `start_at`, `start_seen`, `end_at`, `end_seen`, plus a virtual `latest_update_seen` (see below).
* `Station` is light-weight: no map data, no stored status. Current status is read from its linked events.
* Monitor `Offline` status is out of scope for this first pass. The feature answers "do we have evidence it is actively bad?", never "is it safe?". Q3 is withdrawn.
* Reconciliation and backfill are follow-ups (Q4 deferred), not part of this ticket.

**Review feedback applied (v4):**
* Index section goes at the bottom of the page, as a single list with different highlighting for active and ended events. History pagination uses Django's built-in paginator, 100 per page.
* The MCP main tool returns only counts. A new `get_recent_sewage_discharges` tool returns the details (section 3.5).
* "Recent" is 48 hours everywhere (Q8). Q1: assume Europe/London. Q5, Q6, Q7 agreed. Events show which river they are on (new `Station.river`).
* Stations: Horton-cum-Studley OUT, Boddington OUT, Beckley IN.

**Review feedback applied (v5):**
* There is no stored `last_seen`. A single virtual property on the event, `latest_update_seen = end_seen or station.last_reading_at`, merges the old `last_seen` and `end_seen` into "when our latest information about this event is from": continued discharge while active, the ending once ended. `end_seen` remains only as the stored field that backs this (and records when we noticed the ending); it is **not displayed or returned separately anywhere**. The UI label is "Last updated" (the property name is internal and can stay clunky).
* `Station.checked_at` is renamed `Station.last_reading_at` and only advances on a real reading (`Discharging` or `Not discharging`), never on `Offline`. `out_of_date` is based on the **newest** `last_reading_at` across stations.
Items marked **[Q#]** are open questions; my recommendation is given for each so you can just reply "agreed" where you are happy.

## 1. Goal

Track sewage discharge events (storm overflows etc.) at Thames Water monitors upstream of Oxford, and show them alongside the flags, differentials and boards.

For each event we record:

| What | Field | Source |
|---|---|---|
| When the discharge started | `start_at` | Thames Water |
| When we first noticed it | `start_seen` | our clock |
| When our latest information on it is from | `latest_update_seen` (virtual) | our clock: `end_seen` if ended, else the station's last reading |
| When it ended (if it has) | `end_at` | Thames Water |
| When we noticed it had ended | `end_seen` (stored, feeds the above) | our clock |

Surfaces: a recent-events list on the index page, a full-history page, and the existing `get_river_conditions` MCP tool.

Explicitly **not** required: a full per-station status history (as for flags/boards). Only events that have occurred or are occurring are stored.

## 2. The Thames Water Open Data API

Reference: [API docs](https://docs.api.thameswater.co.uk/s/communityasset/a08Pz00000PCH8OIAX/apiexpopendatarest?groupId=d2e00707-fa02-453b-af2a-ff387546960e&assetId=api-exp-opendata-rest&minorVersion=2.0&tabset-45338=2). The portal is a JS app, so the details below were confirmed by calling the live API on 2026-10-26.

* Base URL `https://api.thameswater.co.uk/opendata/v2`, JSON, **no authentication or API key needed** (older third-party write-ups mention `client_id`/`client_secret`; that is the v1 API and not required here).
* Licence: see `meta.licence` in every response (<https://data.thameswater.co.uk/s/terms-of-service>). Attribution wording on the site to be checked against it.
* Rate limiting: community docs mention ~5 requests/second; in testing a burst of calls returned `429 {"error": "Quota has been exceeded"}`. The client must back off and never loop over stations quickly.

### `GET /discharge/status` - current state of every monitor
One call returns all ~573 monitors (about 240 KB, default `limit` is 1000, supports `limit`/`offset`).

```json
{"locationName": "Cassington", "permitNumber": "TEMP.2457", "locationGridRef": "...",
 "x": 446440, "y": 210010, "receivingWaterCourse": "River Thames",
 "alertStatus": "Offline", "statusChanged": "2026-10-24T04:30:00",
 "alertPast48Hours": false, "uniqueId": "TWL00075"}
```
(Real record, with the grid reference elided. `x`/`y` are OS eastings/northings.)

`alertStatus` is one of `Discharging`, `Not discharging`, `Offline`. `statusChanged` is when it entered that state.
About half of all monitors (290 of 573) were `Offline` when I looked. This first pass deliberately ignores `Offline` (see section 3.3).

### `GET /discharge/alerts` - event log (newest first)
Items: `locationName`, `permitNumber`, `receivingWaterCourse`, `alertType` (`Start`, `Stop`, `Offline start`, `Offline stop`), `datetime`.
Supports `limit`, `offset` and a direct `permitNumber=<permit>` filter (tested: returns only that monitor's alerts). Generic column filters (`col_1`/`operand_1`/`value_1`) are described in third-party posts but did not visibly filter in my test, so the design does not rely on them. Data begins April 2022.

### Timestamps
Naive ISO strings (no offset). I **assume Europe/London local time**; this must be verified against a BST-period event (not possible today, as BST ended 25 Oct) and the implementation should centralise the parsing so it can be corrected in one place. **[Q1]**

## 3. Design

### 3.1 Which stations? (config, not code)
"Upstream of Oxford" needs an explicit, reviewable list. Proposal: a fixture `discharges/fixtures/stations.json` (same pattern as `flags/fixtures/flags.json`) listing the permit numbers to monitor with a name and watercourse for display. Only listed stations are stored.

Appendix A is a first-pass list of the 53 monitors in a box west of Oxford, with my rough "Yes/No/Question" judgement of whether each drains to the Thames above Oxford. That judgement is from my own geography knowledge, **not verified** - please correct it. **[Q2]**

### 3.2 Data model (new `discharges` app)

`Station` - `permit_number` (unique), `name`, `watercourse` (the receiving watercourse as named by Thames Water, e.g. "Bletchingdon Stream"), `river` (which river this ultimately belongs to, assigned in the fixture, e.g. "Thames", "Cherwell", "Seacourt Stream"), and `last_reading_at` (the last poll that gave a real reading for this station, i.e. `Discharging` or `Not discharging`; never advanced by `Offline`. Nullable; see 3.5). No map/grid data and no stored status. A station's current status is derived from its linked events (an open event means it is currently discharging).

`DischargeEvent` - FK `station`, and four stored timestamps: `start_at`, `start_seen`, `end_at` (nullable), `end_seen` (nullable). Ordering `-start_at`. Properties:
* `is_active` (= no `end_at`) and `duration`.
* `latest_update_seen = end_seen or station.last_reading_at`. This is correct for active events because an open event means the last real reading was `Discharging` (a `Not discharging` reading would have closed it), and it freezes when a monitor goes offline or our poller fails. Query code should `select_related('station')` to avoid N+1.

### 3.3 Collection logic
A Celery task + management command `fetch_thames_water_discharges` (same shape as `scrape_ea_boards`), run **every 15 minutes** (monitor timestamps fall on 15-minute marks). One `/discharge/status` call per run, filtered to the configured stations. For each station:

1. **`Discharging`**: set `station.last_reading_at = now`. If there is no open event, create one with `start_at = statusChanged`, `start_seen = now`.
2. **`Not discharging`**: set `station.last_reading_at = now`. If there is an open event, close it - `end_at = statusChanged`, `end_seen = now`.
3. **`Offline`**: ignored. No event is created, updated or closed. (Consequence: an event open when a monitor goes offline stays open, with `latest_update_seen` frozen at the last time we saw it discharging, until the monitor next reports `Not discharging`. The UI shows it so the staleness is visible.) `last_reading_at` is not advanced.
4. Network/API failure (including 429): log, keep existing data, and rely on `latest_update_seen` / an "out of date" indicator (as used by flags/boards, 2 hours) to show staleness. Never fabricate an end.

Only the status endpoint is used. Consequently a discharge that starts and stops between two 15-minute polls will be missed. Reconciling against `/discharge/alerts` and backfilling the history since April 2022 are **follow-ups**, not part of this ticket.

### 3.4 UI

* **Index page**: new "Sewage Discharges" section **below the last existing element** (EA Advisories). A single list ordered active-first then newest-first, containing active events and those that ended in the last 48 hours. Active events are highlighted (danger styling), ended events in a muted style, as with the existing cards. Columns: station, river (and watercourse), started, ended or "Active", and "Last updated" (`latest_update_seen`: whether continued discharge or the end). Empty state reads "No discharge events recorded at monitored stations in the last 48 hours", worded as evidence of discharges and not a safety assurance. Links to the full history, plus the Thames Water data attribution.
* **History page** `/discharges/`: all events at all monitored stations, newest first, showing station, river, `start_at`, `start_seen`, `end_at` and "Last updated" (`latest_update_seen`); optional `?station=<permit>` filter. Uses Django's built-in `Paginator` (`ListView.paginate_by = 100`). New "Discharges" entry in `nav.html`.
* Templates live in the new app, extending `flags/base.html`.

### 3.5 MCP
**Agreed approach:** `get_river_conditions` stays a compact overview and gains only counts; a new tool carries the detail. That fits the existing tool's "current state at a glance" role and keeps its payload small when the Cherwell catchment is busy. Yes, that makes sense to me.

`get_river_conditions` gains a new additive `discharges` key (existing keys unchanged):

```json
"discharges": {
  "active": 1,            // events with no end_at
  "recent": 2,            // events that ended in the last 48 hours
  "out_of_date": false,
  "details_tool": "get_recent_sewage_discharges"
}
```

New tool `get_recent_sewage_discharges` (no arguments) returns, newest first:

```json
{
  "out_of_date": false,
  "window_hours": 48,
  "active":  [ {station, river, watercourse, start_at, start_seen, latest_update_seen} ],
  "recent":  [ {station, river, watercourse, start_at, start_seen, end_at, latest_update_seen} ]
}
```
Times are Europe/London ISO strings via `local_isoformat`. Both docstrings say an empty result is not evidence the river is safe. Both build on the same query helpers as the index view, so they cannot drift (as with the existing tool).

**On `available`:** I agree that hanging it off the most recent event update does not work: no discharges is the normal case, so that time can legitimately be days old while polling is fine. Options:
1. Drop it. Simple, but then a broken poller silently looks like "no discharges", which is exactly the misleading case.
2. **(Recommended)** Replace it with `out_of_date`, driven by `Station.last_reading_at`. `out_of_date` is true when the **newest** `last_reading_at` across stations is more than 2 hours old (or none exists yet). Newest, not oldest, so monitors that are simply offline for days do not make the whole feed look stale; if the poller or API fails, every station stops advancing and the newest goes stale too. It is the equivalent of the existing `out_of_date` on flags and boards. Cost: one timestamp column on `Station`. This replaces `available`, which I have removed from the spec.
**Decided (Q9): option 2.**

### 3.6 Other changes
README (new commands, schedule, data source), `.env.template` unchanged (no credentials), `INSTALLED_APPS`, Celery beat entry.

## 4. Tests
Following the repo's patterns (`flags/tests`, mocked `requests`, saved JSON fixtures from the real API):

* Collection logic: new event, repeat poll advances `last_reading_at` (and so an active event's `latest_update_seen`) only, `latest_update_seen` equals `end_seen` once ended, close on `Not discharging`, `Offline` ignored (including while an event is open: `last_reading_at` and `latest_update_seen` frozen, `out_of_date` unaffected), API error / 429 leaves data untouched, non-monitored stations ignored, timestamp localisation.
* Views: index section (active, recent within 48h, older excluded, empty), history page (pagination at 100 per page, station filter).
* MCP: real JSON-RPC calls as in `flags/tests/test_mcp.py` covering the new counts key and the new `get_recent_sewage_discharges` tool, including `out_of_date`.
* flake8 clean.

## 5. Out of scope
Per-station status history; monitor offline status; alerts-endpoint reconciliation and history backfill (follow-ups); downstream/other-company sewage data (e.g. Severn Trent, Anglian); alerting/notifications; maps; Environment Agency EDM annual returns; adding discharges to the transit rules (see Q7); the `data_health` endpoint (see Q6).

## 6. Caveats to show honestly
* Thames Water's monitors report that an overflow *may* be operating; they are not confirmed pollution events and are sometimes inaccurate.
* Absence of an alert is not evidence of safety. Many monitors are offline (about half when checked), and short events between polls can be missed. The site only reports evidence that a discharge is active or recent.

## 7. Open questions

| # | Question | Recommendation |
|---|---|---|
| Q1 | Are `datetime`/`statusChanged` local time or UTC? | **DECIDED:** assume Europe/London (keep parsing in one place; verify on the first BST-period event). |
| Q2 | **DECIDED: include Cherwell catchment and Seacourt Stream.** Which stations count as "upstream of Oxford"? Specifically: the Cherwell catchment (joins in the Isis reach), the Seacourt Stream side channel, and anything discharging *within* Oxford (e.g. Oxford STW, which I have not looked for). | Include the Thames and its tributaries above Osney; include Cherwell and Seacourt if you want anything that reaches the rowing water. Excluded stations are only a fixture edit away. |
| Q3 | ~~What happens to an open event when the monitor goes `Offline`?~~ | **Withdrawn** - offline ignored for this pass (section 3.3). |
| Q4 | Backfill history since 2022 for the history page? | **Deferred** to a follow-up. The history page starts from deploy day. |
| Q5 | Separate `discharges` app, or inside `flags`? | **DECIDED:** new app. |
| Q6 | Include discharge freshness in `/flags/api/data-health/`? | **DECIDED:** not in this ticket. |
| Q7 | Should discharges ever affect the Transits "allowed" logic? | **DECIDED:** no. |
| Q8 | Index window for "recent" events? | **DECIDED:** 48 hours. |
| Q9 | Replace the MCP `available` flag with an `out_of_date` flag based on `Station.last_reading_at`, or drop it? | **DECIDED:** replace (section 3.5). |

## Appendix A - candidate stations (first pass)
Monitors within roughly 380000-452500 E / 185000-225000 N, state on 2026-10-26. "Suggested" is my unverified judgement.

| Permit | ID | Name | Watercourse | Status (26 Oct) | Suggested |
|---|---|---|---|---|---|
| CTCR.1804 | TWL00004 | Abingdon | Odhay Hill Ditch | Not discharging | No - joins below Oxford |
| CSSC.2453 | TWL00013 | Appleton | Marcham Brook | Offline | No - joins below Oxford |
| CATM.3651 | TWL00155 | Didcot | Moor Ditch | Not discharging | No - joins below Oxford |
| CNTD.0030 | TWL00162 | Drayton (Oxon) | Ginge Brook | Not discharging | No - joins below Oxford |
| CTCR.2011 | TWL00257 | Kingston Bagpuize | Bagpuize Brook | Not discharging | No - joins below Oxford |
| CSSC.2317 | TWL00387 | Stanford-In-The-Vale | River Ock | Not discharging | No - joins below Oxford |
| UCSO.0374 | TWL00806 | Tubney | Marcham Brook | Not discharging | No - joins below Oxford |
| TEMP.2979 | TWL00419 | Uffington | Uffington Brook | Offline | No - joins below Oxford |
| TEMP.2989 | TWL00425 | Wantage | Letcombe Brook | Not discharging | No - joins below Oxford |
| CTCR.1722 | TWL00043 | Bletchingdon | Bletchingdon Stream | Offline | Yes - Cherwell (decided) |
| CAWM.0638 | TWL00403 | Tackley | Tributary of River Cherwell | Offline | Yes - Cherwell (decided) |
| TEMP.2973 | TWL00411 | The Willows, North Hinksey Lane | Seacourt Stream | Offline | Yes - Seacourt (decided) |
| TEMP.3035 | TWL00439 | West Way, Botley (Syphon) | Seacourt Stream | Offline | Yes - Seacourt (decided) |
| TEMP.2457 | TWL00075 | Cassington | River Thames | Offline | Yes - on the Thames |
| UCSO.0357 | TWL00575 | Faringdon House CSO | River Thames | Offline | Yes - on the Thames |
| CSSC.2452 | TWL00010 | Ampney St Peter | Ampney Brook | Not discharging | Yes - upstream tributary |
| CNTD.0001 | TWL00011 | Andoversford | River Coln | Offline | Yes - upstream tributary |
| TEMP.2373 | TWL00024 | Bampton | Shill Brook | Offline | Yes - upstream tributary |
| TEMP.2395 | TWL00042 | Bledington | Bledington Brook | Not discharging | Yes - upstream tributary |
| TEMP.2400 | TWL00046 | Blunsdon | Tributary of Share Ditch | Offline | Yes - upstream tributary |
| CTCR.2036 | TWL00049 | Bourton-On-The-Water | Groundwater | Offline | Yes - upstream tributary |
| CTCP.0026 | TWL00063 | Burford | River Windrush | Offline | Yes - upstream tributary |
| CATM.3521 | TWL00074 | Carterton | Shill Brook | Offline | Yes - upstream tributary |
| CNTD.0064 | TWL00079 | Chadlington | Chadlington Stream | Offline | Yes - upstream tributary |
| TEMP.2466 | TWL00083 | Charlbury | River Evenlode | Not discharging | Yes - upstream tributary |
| CSSC.5783 | TWL00098 | Church Hanborough | Hanborough Stream | Not discharging | Yes - upstream tributary |
| CTCR.1750 | TWL00102 | Cirencester | Shorncote Ditch | Offline | Yes - upstream tributary |
| CSSC.1001 | TWL00103 | Clanfield | Marsh Lane West Ditch | Offline | Yes - upstream tributary |
| CSSC.1091 | TWL00110 | Combe | River Evenlode | Not discharging | Yes - upstream tributary |
| CSSC.2470 | TWL00119 | Cricklade | Tributary of River Thames | Offline | Yes - upstream tributary |
| CATM.3518 | TWL00178 | Fairford | River Coln | Not discharging | Yes - upstream tributary |
| CSSC.2343 | TWL00180 | Faringdon | Faringdon Stream | Offline | Yes - upstream tributary |
| CSSC.2347 | TWL00184 | Finstock | River Evenlode | Offline | Yes - upstream tributary |
| TEMP.2675 | TWL00130 | Hannington | Bydemill Ditch | Offline | Yes - upstream tributary |
| EPRFB3198RS | TWL00600 | Hattchets Cricklade | Tributary of River Thames | Not discharging | Yes - upstream tributary |
| CNTD.0075 | TWL00227 | Highworth | Westrop Brook | Not discharging | Yes - upstream tributary |
| RET/TH/24 | TWL00226 | Highworth Eastrop | Groundwater | Not discharging | Yes - upstream tributary |
| CATM.3520 | TWL00246 | Kempsford | Dudgrove Stream | Offline | Yes - upstream tributary |
| TEMP.1250 | TWL00249 | Kilda Road | Westrop Brook | Not discharging | Yes - upstream tributary |
| CTCR.1981 | TWL00252 | Kingham | Cornwell Brook | Not discharging | Yes - upstream tributary |
| CTCR.1797 | TWL00263 | Lechlade | River Leach | Not discharging | Yes - upstream tributary |
| TEMP.2776 | TWL00303 | Milton-Under-Wychwood | Littlestock Brook | Offline | Yes - upstream tributary |
| CNTD.0012 | TWL00314 | Northleach | River Leach | Offline | Yes - upstream tributary |
| CNTD.0051 | TWL00337 | Purton | Tributary of River Key | Not discharging | Yes - upstream tributary |
| CSSC.1425 | TWL00362 | Sevenhampton Village | Tributary of River Cole | Offline | Yes - upstream tributary |
| TEMP.2893 | TWL00368 | Shrivenham | Tuckmill Brook | Not discharging | Yes - upstream tributary |
| CNTD.0016 | TWL00377 | South Leigh | Limb Brook | Offline | Yes - upstream tributary |
| TEMP.2906 | TWL00385 | Standlake | River Windrush | Offline | Yes - upstream tributary |
| CSAC.0876 | TWL00723 | Stanton Fitzwarren STW | Groundwater | Not discharging | Yes - upstream tributary |
| CSSC.1439 | TWL00389 | Stanton Harcourt | Harcourt Brook | Not discharging | Yes - upstream tributary |
| CNTD.0017 | TWL00402 | Swindon (Rodbourne) | River Ray | Offline | Yes - upstream tributary |
| CATM.3134 | TWL00457 | Witney | Curbridge Ditch | Not discharging | Yes - upstream tributary |
| CSSC.2321 | TWL00462 | Woodstock | River Glyme | Not discharging | Yes - upstream tributary |

## Appendix B - Cherwell catchment candidates
Added after Q2 was decided (Cherwell and Seacourt Stream are in). These are the 51 monitors further north and east of Appendix A's box, which covers the Cherwell, Ray, Sor Brook and Banbury area. The Cherwell catchment is large, so this is the main driver of station count. Judgements are again unverified.

| Permit | ID | Name | Watercourse | Status (26 Oct) | Suggested |
|---|---|---|---|---|---|
| CSSC.2332 | TWL00446 | Wheatley | Wheatley Ditch | Not discharging | No - Thame catchment |
| CSSC.1429 | TWL00363 | Shabbington | Shabbington Brook | Not discharging | No - Thame catchment |
| TEMP.2597 | TWL00188 | Forest Hill | Polecat End Ditch | Not discharging | No - Thame catchment |
| CTCR.1781 | TWL00276 | Long Crendon | Crendon Stream | Offline | No - Thame catchment |
| CTCR.1975 | TWL00464 | Worminghall | Worminghall Brook | Offline | No - Thame catchment |
| CAWM.1403 | TWL00113 | Beckley | Otmoor Lane Ditch | Offline | IN (decided) |
| CNTD.0008 | TWL00238 | Horton-Cum-Studley | Danes Brook | Offline | OUT (decided) |
| CTCR.1313 | TWL00244 | Islip | River Ray | Not discharging | Yes - Cherwell catchment |
| CSSC.0465 | TWL00160 | Dorton | Dorton Brook | Offline | No - Thame catchment |
| TEMP.2467 | TWL00085 | Charlton-On-Otmoor | River Ray | Not discharging | Yes - Cherwell catchment |
| TEMP.2220 | TWL00442 | Weston-On-The-Green | Gallos Brook | Offline | Yes - Cherwell catchment |
| TEMP.3002 | TWL00443 | Weston-On-The-Green STW | Gallos Brook | Not discharging | Yes - Cherwell catchment |
| CSSC.1406 | TWL00283 | Ludgershall | Ludgershall Brook | Not discharging | Yes - Cherwell catchment |
| TEMP.2626 | TWL00204 | Grendon Underwood | River Ray | Offline | Yes - Cherwell catchment |
| CNTD.0023 | TWL00038 | Bicester | Langford Brook | Not discharging | Yes - Cherwell catchment |
| TEMP.2765 | TWL00294 | Marsh Gibbon | Summerstown Ditch | Not discharging | Yes - Cherwell catchment |
| TEMP.2773 | TWL00300 | Middleton Stoney | Gagle Brook | Not discharging | Yes - Cherwell catchment |
| CTCR.1850 | TWL00298 | Middle Barton | River Dorn | Offline | Yes - Cherwell catchment |
| TEMP.2658 | TWL00223 | Heyford | River Cherwell | Not discharging | Yes - Cherwell catchment |
| CNTM.0214 | TWL00498 | Bucknell | Town Brook | Not discharging | Yes - Cherwell catchment |
| TEMP.0707 | TWL00105 | Clifton | Clifton Brook | Offline | Yes - Cherwell catchment |
| CTCR.1796 | TWL00234 | Hook Norton | Hook Norton Brook | Not discharging | Yes - Cherwell catchment |
| CSSC.2339 | TWL00255 | Kings Sutton | Kings Sutton Stream | Not discharging | Yes - Cherwell catchment |
| CSSC.2458 | TWL00045 | Bloxham | Bloxham Brook | Offline | Yes - Cherwell catchment |
| CNTD.0021 | TWL00025 | Banbury | River Cherwell | Offline | Yes - Cherwell catchment |
| CATM.3189 | TWL00281 | Lower Cherwell St, Banbury | River Cherwell | Offline | Yes - Cherwell catchment |
| CSSC.1434 | TWL00369 | Shutford | Shutford Stream | Offline | Yes - Cherwell catchment |
| CAWM.0083 | TWL00299 | Middleton Cheney | Washle Brook | Offline | Yes - Cherwell catchment |
| TEMP.2606 | TWL00183 | Fergusson Road, Banbury | Tributary of River Cherwell | Not discharging | Yes - Cherwell catchment |
| CNTW.0472 | TWL00479 | Banbury Rd Middleton Cheney | Middleton Brook | Not discharging | Yes - Cherwell catchment |
| UCSO.0366 | TWL00803 | Marston St Lawrence | Tributary of Farthinghoe Stream | Offline | Yes - Cherwell catchment |
| CSSC.7686 | TWL00202 | Greatworth | Tributary of Farthinghoe Stream | Not discharging | Yes - Cherwell catchment |
| TEMP.2667 | TWL00235 | Horley (Oxon) | Sor Brook | Not discharging | Yes - Cherwell catchment |
| TEMP.2648 | TWL00214 | Hanwell | Hanwell Brook | Not discharging | Yes - Cherwell catchment |
| CTCR.1766 | TWL00078 | Chacombe | Chacombe Brook | Offline | Yes - Cherwell catchment |
| CSSC.1383 | TWL00236 | Hornton | Hornton Stream | Not discharging | Yes - Cherwell catchment |
| TEMP.2892 | TWL00367 | Shotteswell | Hanwell Brook | Not discharging | Yes - Cherwell catchment |
| CTCR.1851 | TWL00122 | Cropredy | River Cherwell | Offline | Yes - Cherwell catchment |
| TEMP.2512 | TWL00148 | Culworth | Tributary of Culworth Brook | Not discharging | Yes - Cherwell catchment |
| CTCR.1833 | TWL00427 | Wardington | Tributary of River Cherwell | Not discharging | Yes - Cherwell catchment |
| TEMP.2851 | TWL00342 | Ratley | Tributary of Sor Brook | Offline | Yes - Cherwell catchment |
| CSSC.1451 | TWL00429 | Warmington | Hanwell Brook | Offline | Yes - Cherwell catchment |
| CTCR.1793 | TWL00095 | Chipping Warden | Tributary of River Cherwell | Not discharging | Yes - Cherwell catchment |
| CSSC.1006 | TWL00020 | Avon Dassett | Hanwell Brook | Not discharging | Yes - Cherwell catchment |
| CSSC.1369 | TWL00181 | Farnborough (Warks) | Tributary of Hanwell Brook | Offline | Yes - Cherwell catchment |
| CNTD.0010 | TWL00305 | Moreton Pinkney | Ashby Brook | Offline | Yes - Cherwell catchment |
| CSSC.1370 | TWL00177 | Eydon | Ashby Brook | Not discharging | Yes - Cherwell catchment |
| CNTD.0040 | TWL00018 | Aston Le Walls | Tributary of Highfurlong Brook | Offline | Yes - Cherwell catchment |
| CTCR.1853 | TWL00461 | Woodford Halse | River Cherwell | Offline | Yes - Cherwell catchment |
| CNTW.0359 | TWL00047 | Boddington | Feeder to Boddington Canal | Offline | OUT (decided) |
| CTCR.1776 | TWL00067 | Byfield | Byfield Brook | Offline | Yes - Cherwell catchment |
