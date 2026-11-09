# Exercise technique coverage audit — 2026-11-09

Scope: RF-18 explanations; technical content and reuse review only. This matrix
does not certify clinical safety, suitability or prescription quality. It is a
snapshot of the packaged catalogue, not a claim about every exercise or client.
No client record, plan, onboarding information or conversation is reproduced.

Source checked: Muyor, Rodríguez-Ridao and Oliva-Lozano, DOI
`10.5114/jhk/161468`, `muyor-bench-press-2023-technique`, procedures section;
CC BY 4.0, Portuguese adaptation with attribution, technical review 2026-11-08,
deadline 2027-11-08. It describes one horizontal barbell-bench protocol in 20
physically active adults; it does not establish individual safety or suitable
load. It provides only partial setup and movement details. The source is
already approved for technical reuse in `docs/requirements.md`.

| Movement or variant | Coverage | Basis and limitation |
| --- | --- | --- |
| Supino horizontal com barra | Partial | Muyor procedure: body position, grip, descent and extension; no individual suitability or comprehensive safety assessment. |
| Supino unspecified | Partial, clarification needed | The indexed source addresses the horizontal barbell variant, not every meaning of supino. |
| Supino com halteres, no solo, inclinado, declinado or máquina | Missing | The barbell-bench passage does not support these variants. |
| Agachamento com peso corporal | Partial | Santarém et al., DOI `10.3390/s25072018`, describe the deep bodyweight variant in 15 recreationally active adults. Other depths require clarification; the source does not detail every phase. |
| Agachamento goblet | Missing | The bodyweight and barbell descriptions do not establish the goblet technique. |
| Agachamento posterior com barra | Partial | Papadakis et al., DOI `10.3390/jfmk9040224`, Section 2: setup, descent and ascent in a clinical perspective concerning older adults. It is not a universal or individualized instruction. |
| Afundo estacionário | Missing | No reviewed technique passage identified in this audit. |
| Levantamento terra romeno com halteres | Missing | A general review mentions movements but does not establish a complete technique. |
| Elevação de quadril no solo | Partial | Oliva-Lozano and Muyor, DOI `10.3390/ijerph17124306`, Table 2 “Bridge”: position and hip extension described in studies of healthy adults. It does not establish every execution aspect or individual suitability. |
| Flexão de braços | Partial | The same review, Table 2 “Push-Up”: position and elbow movement; hand placement is not specified. Wall, knee-supported and other variants are excluded. |
| Remada curvada com halteres | Missing | A general mention is not a technique guide. |
| Desenvolvimento de ombros com halteres | Missing | No reviewed technique passage identified in this audit. |
| Abdominal curto | Partial | The same review, Table 2 “Curl-Up or Crunch”: position, lifting the upper body and return. Other abdominal variations are not automatically supported. |
| Elevação de panturrilhas em pé | Partial | `nhs-strength-2` supports controlled movement only; it does not explain the full procedure. |
| Rosca direta com halteres | Partial | Parpa et al., DOI `10.3390/muscles4040045`: standing bilateral dumbbell-curl procedure in a study of healthy trained men aged 20–40. Other equipment and variants are not supported. |
| Alongamento de panturrilha, quadríceps, posterior de coxa, peitoral, ombro e rotação de tronco | Missing | Six flexibility identities in the current dictionary; general stretching evidence does not establish each procedure. |
| Cable, machine and unrecognized exercises | Missing | No general inference from an exercise family or another variant is permitted. |

Denominator: all 18 identities in `owner-rag-exercises.json`: five now have
partial procedural descriptions (deep bodyweight squat, floor hip bridge,
push-up, curl-up and standing dumbbell curl), one has only a partial
movement-quality statement (standing calf raise), and 12 lack an identified
applicable technique passage.
The separate barbell bench and
back-squat variants are partial and are not among those 18 identities. These
passages describe published procedures rather than comprehensive individual
instructions. Independent professional review of the Portuguese adaptations
remains pending. A source mentioning an exercise is not classified as a
technique source solely on that basis.

Candidates described in `exercise-question-reliability-specification.md` require
separate exact-text, license, provenance and professional review before any
new safety claim. The University of Queensland candidate is NC and excluded by
the canonical reuse policy.

The production database on 2026-11-09 UTC contained 67 public indexed chunks;
65 were within their source review deadline. The two expired NHS balance chunks
remain excluded from answers. These counts do not measure technique coverage.
No test involving a real client's data was performed for this audit. The live
writer probe used only synthetic question and onboarding context. Three local
model generations included two citation-bearing but indirect responses and one
prompt echo; further repetitions also produced prompt echoes. This is why the
reported bench-press procedure now uses a deterministic response built only
from its reviewed passage after mandatory pgvector retrieval. Other exercise
questions remain subject to writer quality and evidence limitations.

## Implementation verification and remaining work

- Privacy-safe turn metadata now distinguishes question routing, retrieval
  status and bounded passage count, missing/provided/invalid citations,
  reassessment and fallback. These fields do not contain client content.
- Question fallback wording distinguishes unavailable retrieval, stale sources
  and insufficient evidence. It does not claim that an outage proves a lack of
  evidence.
- A conservative applicability registry now allows only the reviewed barbell
  bench-press procedure to support a procedural answer. Retrieved anatomy,
  another exercise, and unsupported bench variants do not count as technique
  evidence. The answer names the study's variant and limitations, and the
  backend resolves its canonical citation. A prompt echo from other model
  answers is discarded rather than shown to the client.
- The supine barbell bench question now gets a deterministic explanation after
  vector retrieval; the client's own health onboarding is considered only as a
  general individual-adaptation caveat, without inferring a relationship to the
  movement. No training plan is changed.
- Focused backend tests: 254 passed, one skipped. Isolated PostgreSQL/pgvector tests: seven
  passed. Chat/source frontend tests: 25 passed. These are technical checks, not
  professional approval or proof of the writer's clinical reliability.
- **Coverage remains limited:** 12 of 18 catalogue exercises lack an
  identified technique passage; standing calf raises have only a partial
  movement-quality statement. Five other identities and two additional
  barbell variants have partial descriptions. The Portuguese adaptations need
  independent professional review; they do not establish clinical suitability.
- The exact question's vector retrieval was verified against the running
  PostgreSQL/pgvector database. The live writer probe exposed instability and
  is not counted as a reliability pass; the reported bench-press question no
  longer depends on that writer path.
