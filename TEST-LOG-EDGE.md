# Edge-Case Test Log — Personalized Triage (web UI)

Date: 2026-10-10. All cases run against the final app.py. Deterministic: same inputs -> same outputs.

## Data expansion
- Recognized conditions: 18 -> 30 display names (added Sleep Apnea, GERD, Osteoporosis,
  Parkinson's Disease, Epilepsy, Thyroid Disorder, Anemia, Back Pain, Fibromyalgia,
  Atrial Fibrillation, Eczema/Psoriasis, IBS, Gout). Every mapped condition has a real
  care-plan section (30/30 verified: 3 in demo.py CONDITION_PLAYBOOKS + 27 in app.py).
- Example chips: 6 -> 10.

## Fixes applied during hardening
1. `_read_json`: malformed JSON no longer kills the connection (returns {}).
2. `run_custom`: non-dict params coerced to {} (was AttributeError -> dead connection).
3. Recognition is now multi-match per phrase: "diabetes high blood pressure" (no comma)
   yields Type 2 Diabetes + Hypertension (was: only the first match).
4. Negation stripping: "no diabetes, high blood pressure" -> Hypertension only;
   "no chest pain" no longer escalates to URGENT (Gate 1 is negation-aware).
5. Critical patterns: added "cannot breathe" and plural "seizures" (both were missed before).

## 21-case adversarial battery — ALL PASS
| Input | Tier |
|---|---|
| cancer 4th stage / stage 4 lung cancer / chest pain / cannot breathe / having seizures / i want to kill myself / overdose on pills | URGENT (7/7) |
| no chest pain, just a headache | NEEDS REVIEW (denial, not a symptom) |
| diabetes high blood pressure (no comma) | MEDIUM (both recognized) |
| type 2 diabetes, hypertension, sleep apnea | MEDIUM (3 recognized) |
| no diabetes, high blood pressure | LOW (negation honored) |
| sleep apnea and loud snoring / thyroid problems / back pain and sciatica / gout in my big toe / epilepsy / atrial fibrillation | LOW, real sections (6/6) |
| xyzzyblarg / it hurts everywhere | NEEDS REVIEW + honesty note |
| i feel fine | LOW (wellness path) |
| (empty) | safe "type your conditions" prompt, no crash |

No critical input ever scored LOW. No char-splitting artifacts. No tracebacks in any response.

## HTTP battery (live server, port 8001) — ALL PASS
- Malformed JSON / empty body / 10KB junk / wrong types / JSON array / JSON null -> HTTP 200, no traceback.
- 24 concurrent requests -> all 200.
