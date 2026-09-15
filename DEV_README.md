# Developer Guide: Temporal Wonder

Denne veiledningen beskriver utvikleroppsett, arkitektur og retningslinjer for utvikling på `temporal-wonder`.

---

## 1. Utviklingsflyt & Git-rutiner

Dette prosjektet følger en streng GitHub issue-drevet utviklingsmodell som spesifisert i [common-agent-instructions/WORKFLOW.md](file:///./.agents/common-agent-instructions/WORKFLOW.md):

1. **Issue før kode**: Alt arbeid forankres i et GitHub Issue (`gh issue view <id>`).
2. **Branching**: Jobb alltid på dedikert gren i formatet `gh-issue/<id>` (f.eks. `gh-issue/1`), utgått fra `main`.
3. **Commit-format**: Commits skal starte med `(#<id>)`, for eksempel: `(#1) Add agent guidelines...`.
4. **Pull Requests**: Åpne PR mot `main` med tittel `(#<id>) <Tittel>` og `Closes #<id>` i beskrivelsen.
5. **Merge**: Bruk alltid **Rebase and merge** (`gh pr merge <id> --rebase --delete-branch`).

---

## 2. Arkitektur og kodestandarder

- **Arkitektur**: Les [AGENTS.md](file:///./AGENTS.md) for detaljert beskrivelse av Temporal-prinsipper, determinismeregler og Strangler Fig-mønsteret.
- **Python**: Følg [python-agent-instructions](file:///./.agents/python-agent-instructions/README.md) for miljøhåndtering, Pydantic v2-modellering, strict typing og `ruff`.
- **Formatering & Hygiene**: Kjør formateringsverktøy før commit:
  - Ingen trailing whitespace på noen linjer.
  - Nøyaktig én trailing newline (`\n`) på slutten av hver fil.

---

## 3. Utviklingsmiljø & Devcontainers

- **Devcontainer**: Prosjektet tilbyr en ferdig `.devcontainer/`-konfigurasjon basert på Python 3.14 med `uv`, `docker-outside-of-docker` og anbefalte utvidelser for VS Code / Codespaces.
- **Lokal installasjon med `uv`**:
  ```bash
  # Opprett virtuelt miljø og installer pakken med utvikleravhengigheter
  uv venv
  source .venv/bin/activate
  uv pip install -e ".[dev]"
  ```
- **Lokal stack (Temporal & Azurite)**:
  ```bash
  docker compose up -d
  cp .env.example .env
  ```
- **Kjøre worker lokalt**:
  ```bash
  uv run python -m temporal_wonder.worker
  ```
- **Starte testflyt**:
  ```bash
  uv run python -m temporal_wonder.starter --manifest examples/sample-manifest.yaml
  ```
  Web UI er tilgjengelig på [http://localhost:8233](http://localhost:8233).

---

## 4. Testing & Kvalitetssikring

- **Kjør tester**:
  ```bash
  pytest
  ```
- **Type-sjekking (Mypy)**:
  ```bash
  mypy src tests
  ```
- **Linting og formatering (Ruff)**:
  ```bash
  ruff format --check .
  ruff check .
  ```
- Workflows testes deterministisk ved hjelp av Temporals `TestWorkflowEnvironment`.
- Eksterne tjenester (Logic Apps, Altinn, registre) mockes ut under test.
