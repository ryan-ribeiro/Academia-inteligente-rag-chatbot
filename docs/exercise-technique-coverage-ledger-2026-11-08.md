# Exercise technique coverage ledger — 2026-11-08, updated 2026-11-09

Scope: the 18 identities in `backend/app/modules/training/owner-rag-exercises.json`
and selected additional variants. The source dictionary is version
`2026-10-25-owner-rag-4`. No client plan, onboarding or conversation was used.
`Partial` identifies only the aspects listed below; it is not an approval of
individual suitability. Independent professional review of the Portuguese
adaptations remains pending.

| Identity / pt-BR name | Equipment; pattern; mode | Status | Supported aspects or explicit gap |
| --- | --- | --- | --- |
| `bodyweight_squat` / Agachamento com peso corporal; alias Agachamento | Bodyweight; lower knee; resistance | Partial | `santarem-bodyweight-squat-2025-deep-procedure`: deep variant only, stance and descent position. An unspecified depth needs clarification; the return phase is not detailed. |
| `goblet_squat` / Agachamento goblet com halter | Dumbbell; lower knee; resistance | Missing | No applicable goblet procedure. |
| `stationary_lunge` / Afundo estacionário | Bodyweight; lower knee; resistance | Missing | No applicable stationary-lunge procedure. |
| `dumbbell_rdl` / Levantamento terra romeno com halteres | Dumbbells; lower hip; resistance | Missing | Barbell and single-leg studies do not establish this exact variant. |
| `hip_bridge` / Elevação de quadril no solo | Bodyweight; lower hip; resistance | Partial | `oliva-lozano-muyor-core-2020-bridge`: supine setup, bent knees, feet on floor and hip elevation. Full return, breathing and individual suitability are not established. |
| `push_up` / Flexão de braços | Bodyweight; upper push; resistance | Partial | `oliva-lozano-muyor-core-2020-pushup`: foot spacing and elbow movement. Hand placement is not stated; wall, knees and suspended variants are excluded. |
| `dumbbell_floor_press` / Supino no solo com halteres | Dumbbells; upper push; resistance | Missing | The barbell-bench passage does not cover the floor/dumbbell variant. |
| `dumbbell_row` / Remada curvada com halteres | Dumbbells; upper pull; resistance | Missing | Barbell-row descriptions are not proof of the dumbbell variant. |
| `dumbbell_overhead_press` / Desenvolvimento de ombros com halteres | Dumbbells; upper push; resistance | Missing | No acquired, rights-reviewed exact procedure. |
| `abdominal_curlup` / Abdominal curto | Bodyweight; trunk; resistance | Partial | `oliva-lozano-muyor-core-2020-curlup`: supine setup, upper-body lift and return. Other abdominal variants and individual suitability are not established. |
| `standing_calf_raise` / Elevação de panturrilhas em pé | Bodyweight; lower accessory; resistance | Partial | `nhs-strength-2` supports controlled movement only. It does not explain setup or phases and is not enabled as a complete procedure. |
| `dumbbell_curl` / Rosca direta com halteres | Dumbbells; upper accessory; resistance | Partial | `parpa-dumbbell-curl-2025-procedure`: standing bilateral supinated grip, start, lift and lowering in trained men aged 20–40. Cable, barbell, hammer and alternating variants are excluded. |
| `standing_calf_stretch` / Alongamento de panturrilha em pé | No external load; lower flexibility; flexibility | Missing | No reviewed exact stretch procedure. |
| `standing_quadriceps_stretch` / Alongamento de quadríceps em pé | No external load; lower flexibility; flexibility | Missing | No reviewed exact stretch procedure. |
| `seated_hamstring_stretch` / Alongamento de posterior de coxa sentado | No external load; lower flexibility; flexibility | Missing | No reviewed exact seated stretch procedure. |
| `chest_stretch` / Alongamento de peitoral | No external load; upper flexibility; flexibility | Missing | No reviewed exact stretch procedure. |
| `cross_body_shoulder_stretch` / Alongamento de ombro com braço cruzado | No external load; upper flexibility; flexibility | Missing | No reviewed exact stretch procedure. |
| `seated_trunk_rotation_stretch` / Alongamento de tronco com rotação sentada | No external load; trunk flexibility; flexibility | Missing | No reviewed exact seated rotation procedure. |

The denominator is **18 identities**: five have partial descriptions, one has
only a partial movement-quality statement, and 12 have no applicable
procedure. No identity has direct, comprehensive coverage. The partial count
does not imply that a generic or unspecified variant can be answered without
clarification.

| Additional variant / synthetic question | Status | Evidence or gap |
| --- | --- | --- |
| Horizontal barbell bench press / “Como fazer supino?” | Partial | `muyor-bench-press-2023-technique`: study setup, grip, descent and extension; other bench variants are excluded. |
| Barbell back squat / “Como fazer agachamento com barra?” | Partial | `papadakis-back-squat-older-adults-2024-procedure`: setup and phases from an older-adult clinical perspective. |
| Bodyweight squat without depth | Clarification | The indexed bodyweight passage covers the deep variant only. |
| Wall or knee-supported push-up | Missing | The standard push-up passage is not applied. |
| Alternating, hammer, cable or barbell curl | Missing | The standing bilateral dumbbell passage is not applied. |
| Cable/machine row, leg press, carries, Olympic lifts and plyometrics | Missing | No exact reviewed procedure is registered for these examples. |

Synthetic tests cover a question with and without a current plan, client
isolation, onboarding context, request replay, and actual pgvector retrieval.
The set of possible exercises and equipment variants remains open-ended; these
rows are not a claim of exhaustive gym coverage.
