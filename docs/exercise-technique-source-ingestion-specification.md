# Exercise technique source discovery, ingestion, and assistant integration

Status: partially executed source appraisal; ingestion is gated. This is a
supporting document; `docs/requirements.md` remains the canonical product
specification. It does not authorize new licences, restricted-source access,
external contact, or changes to the approved RAG contract.

Research checked: 2026-11-08. Source terms, catalogues, and page review dates
can change; recheck the exact page and item before every acquisition.

## 1. Objective

Expand the approved, reusable, technically reviewed corpus with useful,
plain-language instructions for exercise technique, then make eligible passages
available to the existing question flow at `http://localhost:5173/assistente`.
The assistant must be able to answer questions about an exercise whether or not
it appears in the client's plan, while considering that client's relevant
completed onboarding. It must identify the exercise variant and answer only
execution aspects supported by current retrieved passages.

“Every type of exercise performed in a gym” is an open-ended domain, not a
finite promise. Release coverage is measured against the repository's current
selectable exercise dictionary, all named equipment/modality variants, and a
versioned discovery matrix. Unknown or uncovered movements remain explicitly
unsupported; a source count, matching exercise name, or vector score never
counts as procedural coverage.

## 2. Canonical constraints and existing integration

Implementation must follow RF-15/RF-18/RF-19, CA-15.7–8, CA-18.6–12, the
approved RAG contract, EXT-CA-AI-02 source-use criteria, and RNF01/05/06 in
`docs/requirements.md`. In particular:

- Keep PostgreSQL/pgvector, BGE-M3 embeddings, the existing hybrid retrieval,
  source/citation contract, startup bootstrap, and provider adapters. Do not add
  another search service, database, model, or dependency.
- Only the existing allowed commercial-use licences can be indexed:
  `OGL-3.0`, `CC-BY-4.0`, and `CC-BY-SA-4.0`. Do not silently add MIT, CC0,
  CC-BY-SA-3.0, NC, or all-rights-reserved material to this list.
- Every source and passage must pass the existing source review, licence,
  freshness, integrity, and provenance checks. Exact passage and source IDs
  must resolve to canonical citations shown by the existing Portuguese
  “Fontes” UI.
- A retrieval match does not prove exercise/variant applicability. Add a
  reviewed applicability entry for each procedural chunk in
  `backend/app/modules/knowledge/applicability.py`; unsupported variants must
  not inherit instructions from a similar movement.
- Keep the response in pt-BR. Preserve source population, setup, equipment,
  movement phase, exclusions, limitations, attribution, and whether the text is
  a study protocol, general exercise guide, or individual clinical instruction.
  Never infer diagnosis, safety, or individual suitability from a source.
- Do not download or ingest user/client data, comments, plan contents, video of
  identifiable people, images, logos, or third-party media without separate
  documented rights. The candidate review below is primarily about text.

Current implementation entry points are `backend/app/modules/knowledge/
acquisition.py`, `acquisition_expansion.py`, `catalog.json`, `bootstrap.py`,
`service.py`, `applicability.py`, `procedural_answers.py`, and the RF-18 path
in `backend/app/modules/training/chat_service.py`. Acquisitions are pinned and
allowlisted; do not turn the existing fetchers into arbitrary URL crawlers.

## 3. Source discovery findings

Public availability and useful instructions do not by themselves grant reuse
rights. The following appraisal separates technical usefulness from licence
eligibility.

| Candidate | Exercise coverage and accessibility | Reuse finding | Disposition |
| --- | --- | --- | --- |
| [Papadakis et al., back squat in older adults](https://pmc.ncbi.nlm.nih.gov/articles/PMC11587132/) | Peer-reviewed clinical perspective with detailed starting position, descent, and upward phase for barbell back squat; explicitly framed for older adults. It does not cover other squat equipment/variants or generalize to every client. | The full-text article identifies CC BY 4.0. NCBI BioC supplied machine-readable item licence, DOI, authors, section and passage. An allowed licence does not replace independent professional review of an adapted procedure. | **Acquired and indexed as one original-English evidence passage.** The assistant uses a deterministic pt-BR summary only when the user explicitly names a barbell back squat, states the older-adult population limitation, and distinguishes the source description from universal or individual advice. Translation has not received independent professional review; this is recorded in source metadata and remains a review limitation. |
| [Oliva-Lozano and Muyor, core muscle activity systematic review](https://pmc.ncbi.nlm.nih.gov/articles/PMC7345922/) | Table 2 describes exercise procedures used in studies involving healthy adults, including curl-up, floor bridge and push-up. It is an electromyography review, not a comprehensive exercise manual. | The article states CC BY 4.0. Item identity, authors, licence and selected table-row hashes are pinned in the acquisition recipe. | **Acquired and indexed as three original-English excerpts.** Responses describe the selected research protocols and their limits; different variants remain excluded. Independent professional review of the pt-BR adaptations is pending. |
| [Parpa et al., dumbbell and cable biceps curls](https://pmc.ncbi.nlm.nih.gov/articles/PMC12550948/) | Provides the standing bilateral dumbbell-curl setup, grip, lifting and lowering phases. The study involved healthy, physically active men aged 20–40 with resistance-training experience. | The exact article states CC BY 4.0. The BioC recipe pins the DOI, authors, source paragraph and selected dumbbell-curl excerpt; other exercise and dosage text is excluded. | **Acquired and indexed as one original-English excerpt.** The assistant identifies the study population and limits the description to the standing bilateral dumbbell variant. Independent professional review of the pt-BR adaptation is pending. |
| [Santarém et al., six bodyweight squat variations](https://pmc.ncbi.nlm.nih.gov/articles/PMC11991476/) | Describes the deep bodyweight squat used in a study of 15 recreationally active adults, including foot spacing, body position and a laboratory depth reference. The description does not detail every phase. | The article states CC BY 4.0. Its exact BioC article identity, authors and deep-squat paragraph are pinned in the acquisition recipe. | **Acquired and indexed as one original-English excerpt.** The assistant describes the study only for the explicit deep bodyweight variant and asks for clarification when depth is unspecified. Other equipment and variants are excluded. Independent professional review of the pt-BR adaptation is pending. |
| [Abdelraouf et al., dumbbell overhead press](https://pmc.ncbi.nlm.nih.gov/articles/PMC13116542/) | Describes the standing dumbbell press setup and phases in trained collegiate weightlifters. | The article states CC BY, but attributes its instruction form to an NSCA manual; the review did not establish whether the exact text incorporates separately restricted material. | **Candidate only.** Verify the exact passage's third-party rights, provenance and professional applicability before acquisition or indexing. |
| [Upper-limb function in recreational strength training](https://pmc.ncbi.nlm.nih.gov/articles/PMC10889156/) | Mentions bent-over dumbbell row and initiation of lifting, but does not describe a complete setup, lifting and return sequence. | The article states CC BY 4.0. | **Partial research lead only.** Do not count the mention as a complete dumbbell-row procedure. |
| [Romanian, step-Romanian and stiff-leg deadlift comparison](https://pmc.ncbi.nlm.nih.gov/articles/PMC8835508/) | Describes a Romanian deadlift performed with a barbell. | The exact study procedure uses a barbell, whereas the selectable dictionary identity specifies dumbbells. | **Variant mismatch.** Do not substitute it for the dumbbell Romanian deadlift. |
| [Optimizing Resistance Training Technique to Maximize Muscle Hypertrophy](https://pmc.ncbi.nlm.nih.gov/articles/PMC10801605/) | Open-access narrative review on technique variables such as kinematics, contraction type, tempo, and range of motion. It discusses exercise families but is not a complete step-by-step library for selectable movements. | The article states CC BY 4.0. It cites specialist manuals for movement-specific technique rather than reproducing a full catalogue. | **Supplemental context only.** It may support carefully scoped general principles after professional review; it does not establish direct procedure coverage for the exercise dictionary. |
| [UGA PEDB, Weight Training chapter](https://open.online.uga.edu/weighttraining/) | Curated OER listing describes a focused chapter on weight training fundamentals, technique, safety, and programming. The publisher page returned HTTP 403 during this check, so exact text, authorship, chapter-level license statement, and exercise-specific procedures were not verified. | A secondary OER catalogue labels the chapter CC BY 4.0, but that is not sufficient item-level rights evidence for acquisition. | **Unverified lead only.** Recheck the publisher source and chapter license before fetching or indexing. |
| [NHS Strength exercises](https://www.nhs.uk/live-well/exercise/strength-exercises/) | Public, step-by-step text for sit-to-stand, mini-squat, calf raise, sideways leg lift, leg extension, wall press-up, and biceps curls. It is simple home-based guidance for a gentle/older or less active population, not a catalogue of barbell, cable, or machine gym variants. | NHS site terms release eligible content under OGL, but exclude third-party items, images, identifiable audio/video, logos and medical devices. They require specific attribution/linking and a visible OGL notice. Translations count as adaptations and may invalidate formal clinical approval; adapted/updated/non-refreshed NHS content must not be attributed to NHS in the manner allowed for unchanged content. | **Conditional text-only candidate.** Do not ingest or expose translated procedural claims until the exact terms, the existing canonical citation UI, refresh/date-at-copy obligations, adaptation language, and review policy are reconciled. If these terms cannot be met without changing the canonical contract, exclude it pending a human decision. The NHS page reports review 2024-02-28 and next review 2027-02-28; capture and verify current dates at acquisition. |
| [NHS Strength and Flex how-to videos](https://www.nhs.uk/live-well/exercise/strength-and-flex-exercise-plan-how-to-videos/) | Lists variants such as standing press-up, squat, wide squat, pull-up, bench dip and stretches; the webpage text mainly says the video shows the exercise rather than giving the steps. Media review dates are published. | NHS terms exclude identifiable video/audio and third-party visuals. A page title or video description is not the actual procedural instruction. | **Do not download media or infer steps from its title.** Use only eligible textual instructions or obtain rights and complete a separate media/privacy/accessibility review. |
| [wger exercise API and dataset](https://wger.readthedocs.io/en/latest/api/api.html) | Public API offers exercise records and translations; potentially useful for movement names, aliases, equipment, and a first-pass coverage map. Record quality, language, detail, and contributor expertise vary. The initial exercise data is stated as CC BY-SA 3.0. | wger describes exercise data as Creative Commons with licence details associated with individual entries; its published initial-data licence is CC BY-SA 3.0, which is not in the current allowlist. An API response or project-wide “free” statement is not sufficient to establish the licence of a row. | **Metadata/discovery only initially.** Acquire no descriptions unless the exact record supplies verifiable author, source URL, commercial-use permission, and one of the existing allowed licences. Reject CC BY-SA 3.0 and missing/ambiguous per-item rights. Even eligible records need technical and professional content review; community text is not assumed authoritative. |
| [ACE Exercise Library](https://www.acefitness.org/resources/everyone/exercise-library/) | Broad public exercise library; each entry has a detailed description and images. A sampled close-grip bench-press entry contains setup, grip, descent, and return steps. | ACE terms state that site content belongs to ACE or its suppliers, restrict commercial copying/exploitation without prior written consent, and reserve copyright. The site contains third-party images as well. | **High-value permission request candidate only.** Do not scrape, embed, translate, or send content to the writer unless written permission expressly covers machine acquisition, vector indexing, model processing, derivative pt-BR answers, storage duration, display, and citations. |
| [NASM Exercise Library](https://www.nasm.org/workout-exercise-guidance) | Public listing reports 75 exercises and promises step-by-step instructions across strength, machines, bodyweight, cables, and stretches. | NASM terms characterize its materials as proprietary and prohibit copying, entering them into a database, distribution, and derivatives absent granted rights. | **High-value permission request candidate only.** No acquisition or indexing without a written licence covering all intended uses. |
| [ExerciseLibrary.com](https://www.exerciselibrary.com/) | Public site advertises 863 exercises, step-by-step instructions, videos, and coaching tips across 23 groups. | Page states “all rights reserved”; no reusable licence was identified in this review. API terms and item-level rights were not established. | **Discovery only; exclude** unless rights are documented in a signed grant compatible with the existing contract. |
| [FUJF exercise library](https://fujf.net/en/exercises/) / its linked dataset | Public catalogue advertises 1,324 movements and step-by-step English/Chinese instructions. | The site says text/data use an MIT licence; the current approved source allowlist does not include MIT. The separate images have separate permission/attribution. | **Discovery only; exclude** unless a human approves a canonical licence-policy change. Do not ingest its images. |
| [HPRC physical-training resources](https://www.hprc-online.org/physical-fitness/training-performance/resources-physical-training) | Useful educational and training resources, largely guidance/programming rather than a comprehensive movement-by-movement gym technique encyclopedia. | This source review did not establish that the exact exercise text is licensed under one of the project's allowed licences. Requests to cite/reuse are not themselves a licence. | **Background/discovery only** until exact content reuse terms and procedural coverage are established. |

The source research establishes promising breadth but also a material gap:
the most extensive clearly specialized catalogues found (ACE and NASM) are not
openly reusable under the current contract. The NHS written page is a narrow,
population-specific candidate with adaptation/attribution conditions. wger may
provide a legally eligible subset, but per-record licences and text quality must
be proven individually. Do not present this shortlist as a blanket grant of
permission or as enough to cover the whole gym dictionary.

## 4. Required source and coverage workflow

1. Create a versioned coverage ledger from every current selectable exercise
   identity in the owner/exercise dictionaries and a synthetic sample of
   assigned and unassigned plan names. Do not use/export client plans to build
   the sample. Record aliases, language, equipment, movement pattern, modality,
   and variants separately (for example: squat/goblet/smith; bench barbell,
   dumbbells, incline, machine; cable/machine row; bodyweight and assisted
   pull-ups; leg press; hinges; curls/extensions; calf work; carries; Olympic
   and plyometric movements; flexibility and mobility).
2. For every candidate source, record exact page/entry and locator, fetch date,
   content hash, authors/contributors, source and item licence URLs, commercial
   rights, permitted adaptation/translation, attribution wording, third-party
   exceptions, language, review dates, intended population, equipment/variant,
   technical content reviewer, professional reviewer where applicable, and
   disposition. Record explicit rejection reasons. Source-level blanket
   metadata must never overwrite item-level restrictions.
3. Acquire only from an exact HTTPS host/path/API allowlist with bounded
   pagination, response sizes, redirects, request frequency and retries. Store
   reproducible raw artifacts in the existing ignored acquisition cache, not in
   source control. Never include credentials or user data in acquisition.
4. Extract text-only procedural material into reviewed chunks. Exclude menus,
   comments, ads, uncontrolled user content, unrelated programming advice,
   tables/figures/media with unclear rights, and duplicate/contradictory
   passages. Preserve the exact source locator, meaning, variant and population;
   do not invent missing setup or safety steps. Create an accurate pt-BR
   adaptation only if the source permits it and the translation/adaptation has
   the review required to support its claims.
5. Classify coverage per exercise, variant, and question aspect as `direct`,
   `partial`, `not_applicable`, `expired`, `blocked_license`, or `missing`.
   Record which steps are actually supported (setup, start position, concentric
   phase, eccentric phase, breathing, spotting, equipment, modifications),
   which are absent, and why. A mention of a movement or muscle is not direct
   procedural evidence.
6. Keep source indexing and procedural applicability separate. Only direct or
   explicitly partial reviewed procedures may enter the applicability registry.
   Preserve claim/chunk provenance and conservative limitations at retrieval and
   display. Partial support may answer only that portion and must state the gap.
7. Obtain a qualified strength-and-conditioning professional's review of the
   adapted procedural claims, variant mapping, setup/phase descriptions, and
   population boundaries before marking a procedure `direct` or presenting it
   as general instruction. Clinical restrictions, rehabilitation, pregnancy,
   injury, pain, and special populations require appropriate clinical expertise
   and must not be inferred from a general-gym source.
8. Add only approved, eligible entries to the packaged knowledge catalogue and
   the existing reproducible acquisition recipe. Bootstrap must be idempotent:
   changed hashes re-extract/re-embed; removed, revoked, or expired material is
   removed from new retrieval; prior user messages and plan history are not
   rewritten. Batch embedding and database writes within measured local resource
   limits.
9. Use the existing RF-18 question route: authenticated client's own message,
   relevant own onboarding, mandatory hybrid retrieval, applicability filtering,
   canonical citation resolution, and existing `Fontes` UI. Assigned and
   unassigned variants use the same evidence requirements. Do not replace
   unsupported answers with a similar exercise or generic model knowledge.

## 5. Acceptance criteria

- **ESI-01 Coverage ledger:** every currently selectable exercise and known
  variant has a ledger row and denominator. Each row is classified with a reason
  and source locator or explicit gap. Do not claim support for the open-ended
  set of every exercise that could exist in a gym.
- **ESI-02 Source rights:** 100% of indexed sources and chunks have verified
  item-level allowed licence, commercial reuse, attribution, exact provenance,
  permitted adaptation, content hash, review owner/date, and non-expired review
  deadline. No discovery-only or blocked source reaches vector storage.
- **ESI-03 Instruction quality:** every procedural chunk has reviewed exact
  movement/variant/population/execution aspects and limitations. The reviewer
  marks `direct` or `partial`; unsupported claims and absent steps are not
  filled from model prior knowledge. There is no invented professional approval.
- **ESI-04 Searchability:** acquire, chunk, and vectorize approved text with
  BGE-M3 using the current service; a new pgvector query retrieves applicable
  procedure passages within the six-passage bound for representative natural
  pt-BR aliases. Unrelated anatomy and other variants cannot count as applicable.
- **ESI-05 Assistant behavior:** through `/assistente`, synthetic assigned and
  unassigned questions produce a concise pt-BR answer only for retrieved,
  current, applicable instructions; exact canonical sources appear under
  “Fontes”. Own relevant onboarding is considered without exposing another
  client's information or inferring safety. Unsupported, ambiguous, stale, and
  unavailable cases produce distinct honest limitations/clarification.
- **ESI-06 No side effects:** questions never alter training plans, proposals,
  onboarding, or prior messages. Same request UUID replays the stored answer;
  a new request UUID retrieves current evidence.
- **ESI-07 Reproducibility:** unit tests cover license gates, hashes, item-level
  source metadata, chunk limits, duplicate IDs, allowed-host redirects, idempotent
  startup, stale/revoked removal, and expected embedding calls. Isolated real
  PostgreSQL tests exercise hybrid retrieval and tenant scope without a live
  writing model. UI/integration tests cover citations, fallback, and pt-BR.
- **ESI-08 Live development verification:** after ingestion, use only synthetic
  clients and onboarding. Repeat representative questions for covered,
  partially covered, unsupported, assigned, unassigned, equipment and variant
  cases against the actual local retrieval and writer. Manually compare every
  material instruction with its cited passage; report source IDs, disposition,
  latency, and memory without logging prompts or health data. A citation alone
  is not a quality pass.
- **ESI-09 Operational visibility:** report coverage numerator/denominator by
  movement family, blocked licences, missing variants, review dates, chunks and
  source counts, embedding time, database growth, retrieval outcomes, and live
  probe failures. Never report aggregate chunk count as exercise coverage.

## 6. Explicit non-goals and gates

- No scraping of ACE, NASM, ExerciseLibrary.com, FUJF, or other restricted
  catalogues. Their licensing gate requires a human-approved written licence or
  an explicit requirements/decision change before implementation.
- No mass download of videos/images and no attempt to remove access controls.
- No global claim that a movement is safe or appropriate for a particular
  client, no prescriptions or plan edits, and no automatic equivalence between
  similar-looking variants.
- No adding new dependency or changing the allowed source licences as part of
  this spec. A conflict with the canonical requirements is a decision gate.

## 7. Research links

- [Papadakis et al. — Back squat in older adults (CC BY 4.0)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11587132/)
- [Oliva-Lozano and Muyor — Core exercise review (CC BY 4.0)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7345922/)
- [Parpa et al. — Dumbbell and cable biceps curls (CC BY 4.0)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12550948/)
- [Santarém et al. — Bodyweight squat variations (CC BY 4.0)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11991476/)
- [NCBI PMC BioC API documentation](https://pmc.ncbi.nlm.nih.gov/tools/developers/)
- [Resistance training technique narrative review (CC BY 4.0)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10801605/)
- [UGA PEDB Weight Training chapter](https://open.online.uga.edu/weighttraining/)
- [NHS Strength exercises](https://www.nhs.uk/live-well/exercise/strength-exercises/)
- [NHS Strength and Flex how-to videos](https://www.nhs.uk/live-well/exercise/strength-and-flex-exercise-plan-how-to-videos/)
- [NHS Terms and Conditions](https://www.nhs.uk/our-policies/terms-and-conditions/)
- [NHS Content Policy](https://www.nhs.uk/our-policies/content-policy/)
- [wger API documentation](https://wger.readthedocs.io/en/latest/api/api.html)
- [wger licence statement](https://wger.readthedocs.io/en/latest/)
- [ACE Exercise Library](https://www.acefitness.org/resources/everyone/exercise-library/)
- [ACE Terms of Use](https://www.acefitness.org/legal/terms-of-use/)
- [NASM Exercise Library](https://www.nasm.org/workout-exercise-guidance)
- [NASM Terms and Conditions](https://www.nasm.org/policies/terms-and-conditions)
- [ExerciseLibrary.com](https://www.exerciselibrary.com/)
- [FUJF Exercise Library and source/licence disclosure](https://fujf.net/en/exercises/)
- [HPRC physical-training resources](https://www.hprc-online.org/physical-fitness/training-performance/resources-physical-training)

## 8. Execution checkpoint — 2026-11-08 to 2026-11-09

The source audit identified the Papadakis et al. back-squat paper, the
Oliva-Lozano and Muyor systematic review, the Parpa et al. biceps-curl study,
and the Santarém et al. bodyweight-squat study as reusable CC BY 4.0 sources
with specific procedure descriptions. The first
concerns an older-adult clinical context; the second compiles protocols from
studies of healthy adults; the third concerns trained men aged 20–40; and the
fourth describes several bodyweight squat variants in recreationally active
adults. The separate resistance-technique narrative review offers general principles, not
a complete exercise-by-exercise manual. The UGA chapter remains an unverified
lead: its publisher page returned HTTP 403 during this check.

The Europe PMC JATS endpoint returned HTTP 500. Acquisition was completed
through NCBI's official PMC BioC API instead. The checked-in recipe and
`acquisition_bioc.py` pin the exact article, DOI, authors, CC BY 4.0 notice,
section type and paragraph hash; bounded downloads and redirects are validated.
The 95,904-byte source artifact is stored under the ignored
`backend/.cache/training-evidence/bioc/` cache, SHA-256
`f5064671d5fca89ad368954ba10970c19aba430917438f30a2caf21e014f90df`. One
original-English chunk is packaged with attribution and the older-adult scope.
The core-exercise review was acquired in the same manner: three selected rows
have exact source and excerpt hashes, and the source artifact SHA-256 is
`9646508b37ab110a5f1bca8f8f2e93e92c2c4e635dec0d79b8c1b388bfc923ad`.
The biceps-curl source artifact SHA-256 is
`0fb95bbd7736615774857700f35d4d48cf8e25fa9c3bc5aee3b0245cc2d0acf7`.
The bodyweight-squat artifact SHA-256 is
`a7c8de718b8a646ab17586ff319d884441004db6940a8d4b915dadff86e130d8`.
Bootstrap embedded all six new chunks with BGE-M3 into PostgreSQL/pgvector;
the catalogue contains 73 chunks.

Execution is **partial**. The detailed identity, equipment, movement-pattern,
source and missing-aspect ledger is
`docs/exercise-technique-coverage-ledger-2026-11-08.md`. Of the 18 selectable
exercise identities, five now have partial descriptions (deep bodyweight squat, curl-up, floor bridge,
push-up and standing dumbbell curl); standing calf raise has only a
movement-quality statement; and 12 have no applicable
procedure passage. Horizontal barbell bench and back squat are additional,
partially described variants outside those 18 identities. Synthetic live
pgvector checks retrieved the applicable passages for the three core exercises,
dumbbell curl, deep bodyweight squat, barbell back squat and bench press. The
applicability filter
rejected wall push-ups, alternating curls and unsupported squat variants even
when similar passages were found. An HTTP chat check used synthetic clients and
onboarding against the real local database and embeddings, checked citation,
request replay, client isolation, bodyweight-squat clarification and a short
affirmative follow-up, then rolled back the synthetic records.

Focused tests cover the pinned BioC extraction, author/licence/identity checks,
artifact caching, deterministic response, and assigned/unassigned questions.
The related backend suite passed 211 tests with three opt-in PostgreSQL tests
skipped in the local Python run. A separate opt-in run against isolated
PostgreSQL schemas passed 16 tests, including tenant isolation and retrieval
failure behavior.
They do not replace the independent professional review of the Portuguese
adaptation required by ESI-03. Consequently, broad coverage and professional
approval remain incomplete. ACE/NASM rights, NHS adaptation/citation
compatibility, and wger item-level licences also remain unresolved. No
unsupported squat variant receives this source as evidence.
