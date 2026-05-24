# Phase 4 Probe Notes — pronotepy 2.14.6

**Captured:** (fill in after running probe — e.g. 2026-05-24)
**Source instance:** katiramona.ac-noumea.nc (direct `?login=true` URL — Phase 3 UAT finding #6)
**pronotepy version:** 2.14.6
**Script:** `scripts/probe_config_flow.py`

Append-only. One section per probe STEP, one section per pronotepy version.

---

## STEP 5 — `client.lessons(date_from, date_to)` shape

> Confirm `Lesson` attribute names + types Phase 4 mocks depend on:
> - `lesson.date` / `lesson.start` / `lesson.end` (naive datetime — pronotepy returns naive in school local time; Phase 2 `_lesson_from_raw` localises with `school_tz`)
> - `lesson.subject.name` (not just `lesson.subject`)
> - `lesson.teacher_name` (single string; multi-teacher pronotepy versions may use `lesson.teachers`)
> - `lesson.classroom`
> - `lesson.canceled` (bool)
> - `lesson.status` (free-form string — may contain "Cours annulé", "Cours déplacé", etc.)

(Paste relevant probe STEP 5 output here.)

---

## STEP 6 — `client.current_period.grades` + `Period.overall_average`

> **Critical for GRADE-01..03** — confirm:
> - `Grade.grade` (raw value string, e.g. `"15"` or `"14,5"`)
> - `Grade.out_of` (string, e.g. `"20"`)
> - `Grade.coefficient` (string, e.g. `"2"` or `"1"`)
> - `Grade.average` (class average string) — **IS IT POPULATED on the NC instance?**
> - `Grade.max` (class max string) — **IS IT POPULATED?**
> - `Grade.min` (class min string) — **IS IT POPULATED?**
> - `Grade.comment` (teacher free-text) — string vs None?
> - `Grade.subject.name` shape
> - `Grade.date` (datetime.date)
> - `Period.overall_average` — comma-decimal string `"14,50"`? Or `"-1"` (pronotepy sentinel for "not computed")? Or `""`?
> - `Period.name` — e.g. `"Trimestre 2"` or `"T2"`?

(Paste relevant probe STEP 6 output here.)

---

## STEP 7 — `client.information_and_surveys()` shape

> Confirm `Information` attribute names:
> - `info.id` (string)
> - `info.title` (string)
> - `info.author` (string — sender)
> - `info.content` (string — body; Phase 2 caps excerpt at 500 chars in `_info_from_raw`)
> - `info.read` (bool)
> - `info.start_date` or `info.creation_date` (datetime — Phase 2 prefers `start_date`, falls back to `creation_date`)

(Paste relevant probe STEP 7 output here.)

---

## STEP 9 — `client.periods` (informational, future Phase 6 multi-period)

> Confirm `Period` list shape — ordering, name format, attributes.

(Paste relevant probe STEP 9 output here.)

---

## STEP 11 — `ClientInfo` attributes

> **Critical for ENT-01** — confirm:
> - `ClientInfo.class_name` returns the class level string (e.g. `"3ème A"`, `"5e1"`, `"Terminale S"`)
> - OR returns `""` if not exposed by this Pronote build
> - List of other ClientInfo attrs available (`name`, `id`, ...)

(Paste relevant probe STEP 11 output here.)

---

## Sign-Off

Check each box once the corresponding probe output has been verified against the NC instance:

- [ ] `Grade.average` / `.max` / `.min` populated on NC instance → mocks in Plans 04-05 / 04-07 reflect real pronotepy data; no field-name drift
- [ ] `Grade.comment` is a string (never None) → no defensive `or ""` needed beyond what `_grade_from_raw` already does in Phase 4
- [ ] `ClientInfo.class_name` returns non-empty string on NC instance → `const.py:CLASS_LEVEL_ATTR = "class_name"` is correct (Plan 04-04)
- [ ] `Period.overall_average` returns comma-decimal string on NC instance with active grades (not `"-1"` sentinel) → Plan 04-05 grades sensor `_to_float` handles real values + edge cases
- [ ] `Information.read` is a bool → unread count math in Plan 04-05 is sound

---

*Sign-off date: __________*
*Signed by: __________*
