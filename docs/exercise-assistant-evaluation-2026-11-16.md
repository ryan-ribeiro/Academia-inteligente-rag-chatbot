# Exercise assistant evaluation — 2026-11-16

Status: **incomplete**. This is not a catalog-wide evaluation. Each case below
used `Como fazer o exercício X?` with the English catalog title as X, submitted
through `TrainingChatService.submit_for_subject` using the running application's
Ollama configuration, an isolated in-memory client database, the semantic index,
and actual embedding and translation providers. This exercises the service
behind `/assistente`, not its browser or authenticated HTTP route.

| Exercise | Outcome | Observation |
| --- | --- | --- |
| 3/4 Sit-Up | Failed | The assistant could not confirm all movement steps. |
| Ab Crunch Machine | Answered | The response gave three steps and cited the matching Free Exercise DB entry. The steps have not been independently reviewed by a professional. |
| Alternating Floor Press | Failed | The assistant could not confirm a response with the available references. |

The two failures need investigation, new sources where appropriate, and
retesting. No source was added or indexed during this evaluation. The remaining
2,079 catalog entries have not been tested in this evaluation; the two failures
above are not a complete failure list. Earlier retrieval-only checks used a
different prompt and cannot substitute for this service-level evaluation.
