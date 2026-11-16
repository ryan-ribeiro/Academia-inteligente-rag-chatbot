# Exercise knowledge retrieval for training chat — proposal

Status: implementation proposal; the RF-18 corpus-context amendment is approved.
This document proposes an extension to RF-18 and does not override
`docs/requirements.md`. No professional review of individual source passages is
assumed. Authoritative publications reduce uncertainty but cannot establish that
an exercise or substitution is safe for a particular person.

The user confirmed that no health professional will review individual passages.
Select sources using their reputation and reliability and their coverage of
exercise execution, load, repetitions, progression, and responses to pain.
Document coverage gaps; do not infer clinical validation from source reputation.

## Objective and boundaries

Enable authenticated clients to ask, in Brazilian Portuguese, about technique,
equipment, repetitions, load and progression for exercises in or outside their
current plan. Use naive RAG: a curated, versioned public corpus, chunking,
embeddings, similarity retrieval and a bounded set of passages supplied to the
existing provider-independent AI adapter. The chat remains informational;
retrieval does not approve a plan, diagnose an injury or validate safety.

For reported pain during exercise, instruct the client to stop the painful
activity and seek an appropriate health professional. Do not diagnose, prescribe
treatment, recommend a specific replacement for the painful exercise, or claim
that a replacement is safe. For potentially urgent symptoms, direct the client
to urgent local care. The existing plan-change and instructor-review flow
continues to govern any change. For non-pain questions, general alternatives
may be described as information, without presenting them as personalized plan
changes. Load and progression guidance is general, attributed, bounded by the
source's population and never overrides individual restrictions or the plan.

## Candidate sources, checked 2026-11-13

These are candidates, not permission to ingest. Public availability for download
does not establish permission for extraction, embeddings, storage, translation,
display, or commercial use. Verify and record rights for each use before
ingestion; exclude any source without sufficient rights. No proprietary book or
unverified copy is included.

| Source | Access and potential contribution | Limitation |
| --- | --- | --- |
| [WHO guidelines on physical activity and sedentary behaviour (2020)](https://www.who.int/publications/i/item/9789240015128) | Downloadable institutional guideline; population-level activity recommendations. | Not an exercise technique manual; check publication licence and intended use. |
| [ACSM resistance training overview (2026), downloadable infographic](https://www.acsm.org/wp-content/uploads/2026/03/Resistance-Training-Position-Stand-infographic.pdf) | Current institutional summary of evidence for healthy adults, including resistance training variables. | Summary only; rights and full-text access require verification. |
| [ACSM muscle recovery information sheet](https://www.acsm.org/docs/default-source/files-for-resource-library/a-road-map-to-effective-muscle-recovery.pdf) | Downloadable institutional guidance including stopping exercise that causes pain. | Check rights; not a source for individualized substitutions. |

### Additional exercise sources and licence findings

Licence statements checked 2026-11-13; third-party provenance and fitness for a
specific deployment remain separate questions from the stated licence.

| Material and download | Declared rights and suitability |
| --- | --- |
| [Exercise Delivery, University of Queensland (2022)](https://uq.pressbooks.pub/exercisedelivery/) | A specialist university textbook covering named exercises including squats, deadlifts, rows and presses. CC BY-NC-SA 4.0, except where otherwise noted. Noncommercial use only, attribution and share-alike apply; embedded material may have different rights. Available online; a downloadable whole-book edition was not confirmed. Seek commercial permission if needed. |
| [Free Exercise DB](https://github.com/yuhonas/free-exercise-db), [combined JSON](https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json) | Over 800 structured exercise records with instructions; repository declares [Unlicense](https://github.com/yuhonas/free-exercise-db/blob/main/LICENSE.md), allowing reuse. Derived from an earlier dataset; independently verify upstream rights and provenance, especially images. Community-maintained and not established as professionally validated. |
| [LogPress exercise dataset](https://github.com/hasaneyldrm/exercises-dataset), [JSON](https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/main/data/exercises.json) | [NOTICE](https://github.com/hasaneyldrm/exercises-dataset/blob/main/NOTICE.md) declares MIT for non-media instructions and metadata, requiring preservation of copyright and licence notices. Images and GIFs have separate rights and must be excluded unless separately licensed. An [upstream provenance issue](https://github.com/hasaneyldrm/exercises-dataset/issues/5) raises questions about the original data; resolve before production ingestion. |
| [Resistance training technique review (2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10801605/) | Peer-reviewed narrative review, CC BY 4.0, downloadable from the publication page; attribution required. Useful for general technique principles, not a comprehensive step-by-step catalogue. |
| [RepDB free exercise dataset](https://github.com/RepDB/exercise-dataset) | Downloadable 650-record catalogue; its [custom licence](https://github.com/RepDB/exercise-dataset/blob/main/LICENSE-DATA.md) permits attributed commercial in-app use but restricts redistribution and image-based generative AI. Whether embedding text and sending retrieved passages to a third-party model are permitted is not explicit; obtain written clarification before RAG ingestion. |

These sources provide promising breadth, but exercise counts do not demonstrate
coverage of the gym's actual catalogue or the correctness of its instructions.
Measure coverage against the actual exercise list, evaluate citations and
translations, and abstain where evidence is missing. Do not treat community
catalogues as equivalent to professionally reviewed reference material.

## Proposed functional acceptance criteria

1. An authenticated client can ask about an exercise in or outside their current
   plan. The response is in pt-BR and distinguishes general source-backed
   information from that client's authorized plan data.
2. When sufficient relevant evidence exists, the response cites the source title,
   publication date or version, URL and page or section for each substantive
   exercise claim. Citations must refer to passages actually retrieved. If no
   sufficiently relevant, applicable passage exists, say so and do not invent
   instructions or citations.
3. Pain reports follow the safety boundary above even if retrieval, embeddings,
   or the AI provider fail. Exercise substitution for pain is deferred to an
   appropriate professional; the chat does not alter the plan.
4. Retrieval failure, empty results, stale or revoked sources, and provider
   failure produce a controlled pt-BR response; none silently falls back to
   unsupported exercise advice. Existing chat and plan data remain intact.
5. Only the authenticated client's authorized context is accessible. The shared
   corpus contains no client data; chat messages, onboarding and plan content
   are never inserted into it. Minimize sensitive data sent to any external
   embedding or generation provider.
6. Each ingested passage is traceable to source, version, page/section, licence
   decision, extraction date and content hash. Ingestion is repeatable; source
   withdrawal or rights revocation removes its passages from retrieval.
7. Test Portuguese exercise synonyms, in-plan and out-of-plan questions, missing
   evidence, attribution, prompt injection in retrieved text, pain and urgent
   scenarios, provider failures, and cross-client isolation. Use fixed source
   fixtures and mocked providers; no live services are required by tests.

## Implementation decisions and remaining limitations

- The local implementation uses the existing Ollama integration with the
  multilingual `embeddinggemma:300m-qat-q4_0` model, a read-only SQLite vector
  index, one passage per response and a configurable similarity threshold. Exercise
  records and research paragraphs are individual chunks. For Ollama, exercise
  statements are translated in the backend with the dedicated `translategemma:4b`
  model; the model must be available in the configured Ollama instance. Retrieval
  smoke checks cover 13 queries, including Bulgarian split squat, generic squat,
  and generic bench press, and live translation checks cover those three examples.
  These small checks are not representative of all users, exercises or health
  conditions.
- The user authorized indexing the downloaded corpora. The sources' stated
  licences and known provenance disputes are recorded in the corpus README;
  third-party rights and operational source ownership remain unresolved for
  production. Source revocation is configurable without rebuilding the index.
- Define and run an evaluation set covering the requested question types and
  unavailable evidence. Automated tests and authoritative sources cannot
  guarantee clinical safety without qualified review.
- This feature adds no editing authority: the existing single-draft rule and
  approved-plan review and versioning boundaries continue to apply.
