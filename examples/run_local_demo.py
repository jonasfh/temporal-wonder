"""Interaktivt demo-skript som demonstrerer Temporal Wonder orkestrering lokalt.

Kjør med:
    uv run python examples/run_local_demo.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import yaml
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from temporal_wonder.activities.legacy.logic_app import call_legacy_logic_app
from temporal_wonder.activities.native.native_step import execute_native_step
from temporal_wonder.testing.harness import get_test_runtime
from temporal_wonder.testing.mock_server import LogicAppMockServer
from temporal_wonder.workflows.orchestrator import IntegrationOrchestratorWorkflow


async def main() -> None:
    manifest_path = Path("examples/sample-manifest.yaml")
    print("\n" + "=" * 70)
    print("🚀 TEMPORAL WONDER - LOKAL DEMO AV STRANGLER FIG ORKESTRERING")
    print("=" * 70)
    print(f"📖 Leser integrasjonsmanifest: {manifest_path}")

    manifest_dict: dict[str, Any] = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    steps = manifest_dict.get("steps", [])

    print(f"📋 Manifest ID: {manifest_dict.get('identifier')} (v{manifest_dict.get('version')})")
    print(f"   Tittel: {manifest_dict.get('title')}")
    print(f"   Totalt antall steg: {len(steps)}")
    print("\nSteg i DAG-en:")
    for step in steps:
        step_type = "⚡ NATIVE (Moderne)" if step["type"] == "native" else "🏛️  LEGACY (Logic App)"
        deps = (
            f"avhenger av: {step['dependsOn']}"
            if step.get("dependsOn")
            else "ingen avhengigheter (starter umiddelbart)"
        )
        print(f"   - [{step['id']}] {step['name']}")
        print(f"     Type: {step_type} | {deps}")

    print("\n" + "-" * 70)
    print("1️⃣  Starter in-process Logic App Mock Server...")
    with LogicAppMockServer() as mock_server:
        import os

        from temporal_wonder.config import get_settings

        os.environ["LOGIC_APP_BASE_URL"] = mock_server.base_url
        get_settings.cache_clear()
        print(f"   Mock-server lytter på: {mock_server.base_url}")

        print("\n2️⃣  Starter lokalt Temporal testmiljø (WorkflowEnvironment)...")
        async with await WorkflowEnvironment.start_time_skipping(runtime=get_test_runtime()) as env:
            task_queue = "demo-integration-queue"
            print(f"   Temporal klient tilkoblet. Task queue: '{task_queue}'")

            print("\n3️⃣  Starter Temporal Worker med arbeidsflyt og aktiviteter...")
            async with Worker(
                env.client,
                task_queue=task_queue,
                workflows=[IntegrationOrchestratorWorkflow],
                activities=[call_legacy_logic_app, execute_native_step],
            ):
                print("   Worker poller oppgaver. Eksekverer DAG-arbeidsflyt...")
                print("\n4️⃣  Kjører IntegrationOrchestratorWorkflow...")

                result = await env.client.execute_workflow(
                    IntegrationOrchestratorWorkflow.run,
                    manifest_dict,
                    id=f"demo-run-{manifest_dict.get('identifier')}",
                    task_queue=task_queue,
                )

                print("\n" + "=" * 70)
                print("✅ WORKFLOW FULLFØRT MED STATUS: " + result["status"])
                print("=" * 70)
                print(f"⏱️  Beregnet kjøretid: {result['duration_seconds']:.2f}s (tidsspoling)")
                print(f"📊 Utførte topologiske lag: {result['executed_layers']}")
                print("\nResultater per steg:")

                for step_id, res in result["step_results"].items():
                    status_icon = "✅" if res.get("status") == "COMPLETED" else "❌"
                    step_type = res.get("type", "unknown")
                    msg = res.get("message", "")
                    print(f"   {status_icon} Steg '{step_id}' ({step_type}):")
                    print(f"      Melding: {msg}")

                # Verifiser mock-forespørsler
                recorded = mock_server.recorded_requests
                print(f"\n🌐 HTTP-kall fanget opp av Logic App Mock Server ({len(recorded)} stk):")
                for req in recorded:
                    print(f"   - {req.method} {req.path} -> action: {req.action}")

    print("\n" + "=" * 70)
    print("🎉 Demo fullført uten feil!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
