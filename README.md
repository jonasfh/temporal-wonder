# Temporal Wonder

En test- og evalueringsplattform for å utforske **Temporal** som orkestreringsmotor for integrasjonsplattformen hos Finanstilsynet.

Repositoryet demonstrerer hvordan komplekse integrasjonsflyter kan orkestreres pålitelig, med spesiell vekt på **Strangler Fig-mønsteret** for gradvis migrering bort fra legacy Azure Logic Apps til moderne native aktiviteter.

---

## Kjernekonsepter

```mermaid
flowchart TD
    M[YAML / JSON Manifest] -->|Leser DAG & Avhengigheter| O[Temporal Master Orchestrator]
    O -->|Steg A: Legacy| L[HTTP Activity: Kall Logic App]
    O -->|Steg B: Migrert| N[Native Activity: Python / C#]
    L -->|Kjører| LA[Azure Logic App]
    N -->|Kaller direkte| E[Altinn 3 / Ereg / Blob]
```

1. **Manifest-drevet orkestrering**: Integrasjoner defineres deklarativt som rettede asykliske grafer (DAG) i JSON/YAML.
2. **Strangler Fig-migrering**: Eksisterende Azure Logic Apps kalles via standardiserte HTTP-aktiviteter frem til de erstattes steg for steg med native kode.
3. **Temporal determinisme**: Orkestreringslogikken er 100 % deterministisk og gjenskapbar fra hendelseslogg, mens all I/O og eksterne kall isoleres i aktiviteter.

---

## Agent- og utviklerretningslinjer

For fullstendige instruksjoner og retningslinjer:
- 🤖 **AI-agenter & Copilot**: Se [AGENTS.md](file:///./AGENTS.md) og [.github/copilot-instructions.md](file:///./.github/copilot-instructions.md)
- 🛠️ **Utviklerveiledning**: Se [DEV_README.md](file:///./DEV_README.md)
- 📦 **Generelle fellesregler**: [`.agents/common-agent-instructions/`](file:///./.agents/common-agent-instructions/README.md)
- 🐍 **Python-regler**: [`.agents/python-agent-instructions/`](file:///./.agents/python-agent-instructions/README.md)
