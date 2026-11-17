# A primary calendar supplies conditional tasks, not a full work schedule

Columella's agricultural calendar, **De re rustica11.2**, is now recorded as
one Latin text witness:101 paragraphs and39 located task/calendar claims,
with90 independent literal-anchor/date/number checks. No modern date, model
bin, task-rate coefficient or additional workforce is adopted.

The useful finding is conditional timing: tasks vary with weather, soil,
crop development and region, while several duties compete for labor. This
supports retaining those conditions in a future schedule. It does not fill
the missing complete monthly Earth occupation or warehouse handling rate.

## Source identity and access

The declared Chicago/LacusCurtius English bookXI URL returned404. Its actual
index has both bookXI language links commented out as `not_online`; a printed
book label is not an available text. The index instead links a complete Latin
text at [The Latin Library](https://www.thelatinlibrary.com/columella/columella.rr11.shtml).
The [committed adapter](../calibration/urban_diagnosis_20261117/columella_calendar_latin_adapter.json)
kept the same primary chapter and registered exposure before fetching that body.
No unavailable English translation or scan was substituted.

The catalogue and page heading identify Columella/bookXI; chapterII lies between
explicit chapterI/III boundaries and has contiguous paragraphs1–101. The
publisher index describes the complete Latin text as unmodified Lundstrom,
but the Latin Library book page supplies no direct edition statement. **The
exact critical edition is not independently established.** Qualification is
faithful extraction of this retained site witness with that provenance limit.
All English descriptions are our paraphrases, not an attributed translation.

Raw whole-book HTML, including incidentally retrieved/partly visible chaptersI/
III, remains local/ignored. Analytical extraction is chapterII only. Public
artifacts contain paraphrases, brief Latin anchors, locators and paragraph
digests, not a republished text. The failed fetch and publisher metadata remain
in the packet. The two separately missing old farm-source caches were not
restored or assigned new hashes.

## What the calendar can actually support

| Located prescription | Constraint it suggests | What remains unknown |
|---|---|---|
| Weather governs tasks; spring need not begin on one astronomical day (1–3) | Conditional opportunities | A global modern date/bin mapping |
| Ploughing differs by soil, moisture and season (8,32,46) | Soil-dependent task order and effort | Calibrated soil classes, modern hours and animal requirements |
| Cereal hoeing uses a development marker; barley work depends on available labor (9,26) | Crop-state and competing-work conditions | Modern growth-stage code and complete labor availability |
| Prepare threshing floor, harvest/thresh barley and preserve straw (47,50) | Postharvest tasks belong in the work account | Measured hours per grain/handling unit |
| Temperate/coastal harvest and subsequent straw clearing (54) | Regional task sequence | A universal harvest deadline or storage residence time |
| Work during cooler hours and at night; recurrent animal feeding (55,90–101) | Other duties and time-of-day constraints | A complete human/animal occupation budget |
| Colder places sow earlier, warmer places later (74,80) | Qualitative regional ordering | Cell-level dates or temperature cutoffs |

The thirty-day statement in54 concerns gathering cut straw after harvest.
It is **not** a thirty-day cereal warehouse limit or a universal reaping-work
window. Paragraph47's explicit solstice deadline applies to vine work in the
same paragraph; the export does not recast it as a threshing-floor deadline.

Several new numbers are prescriptions in original units, not observations.
Examples include two `operae` per rich-soil iugerum under the stated conditions,
different ploughing effort on difficult/easier soil, and seed quantities per
iugerum. No `opera` is converted to an eight-hour day and no modius becomes
edible output or hectares. The witness's `modios tres una opera` in26 retains
its seed-volume expression. The `lirantur ... bis ... opera` construction in46
is not repaired into a rate.

## Calendar and interpretation limits

Paragraph94 retains **two winter-solstice identifiers**, `XVI Kal. Ian.` and
`VIIII Kal. Ian.`, attributed respectively to Hipparchus and Chaldean practice.
Both stay in the ledger. Neither is selected, modernized or aligned to the
solstice-origin model calendar. Source daylength/horae are likewise not a
measurement of modern working-day capacity.

The `quattuor fibrarum` development expression in9 is preserved without forcing
a modern botanical stage. Paragraph6's interval term `semestrium` is not used
to calculate a duration. Paragraph82 contrasts its own work prescription with
an older norm the author hesitates to affirm. This is a warning against turning
all agronomic advice into one homogeneous rate table.

Estate delegation in72 is a prescription about supervision and duties. It does
not estimate a population fraction, gendered workforce share, collective access
right or actual rural-to-port assignment. Other crops and animals occur as
competing-duty context, not new model/calibration cohorts.

## Checks and next step

An independent tag-stripping parser reproduces all101 paragraph digests and
checks all39 exports, source markers and numeric tokens. The
[claims](../output/urban_columella_calendar_20261117/claims.csv),
[coverage](../output/urban_columella_calendar_20261117/coverage.csv),
[identity](../output/urban_columella_calendar_20261117/source_identity.json),
[limits](../output/urban_columella_calendar_20261117/limits.json) and
[review](../output/urban_columella_calendar_20261117/review.json)
are pinned by the [qualification](../output/urban_columella_calendar_20261117/qualification.json).
All1103 protected identities remain exact;zero model/solver calls,new Earth
food/staff cases,fit or atlas/default changes occurred. This is development
source evidence,not independent historical validation.

The [next declaration](../calibration/urban_diagnosis_20261117/columella_calendar_concordance.json)
limits further work to one identified public-domain witness of the same chapter
and six already-exposed expressions. It will check edition and literal variants
without silently editing this packet or adopting rates/dates. A matching second
witness still cannot supply measured staffing or a complete occupation schedule.

Climate/steppe, reserved pools and site-survey workbook remain deferred/unopened.
For reproduction,restore the ignored raw files from recorded URLs/digests before
`scripts/qualify_columella_calendar.py`, `scripts/review_columella_calendar.py`
and `scripts/seal_columella_calendar.py` in an empty isolated OUT. Changed source
bytes need fresh source review. Completed packets refuse overwrite.
