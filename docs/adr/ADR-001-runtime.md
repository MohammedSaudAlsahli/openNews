# ADR-001: embedded subprocess and Unix-domain IPC

Status: accepted for the initial vertical slice. Date: 2026-10-11.

## Decision

Use a relocatable CPython 3.12.13 inside the `.app`, launched and stopped by Swift. Use a private Unix socket with JSON Lines and SQLite-owned durable job state. Do not ship AgentOS in the runtime dependency set for this milestone. Agno remains the model/agent framework.

## Evidence

The Agno 3.1.2 AgentOS spike instantiated an agent without API credentials, assembled `AgentOS(..., telemetry=False).get_app()`, entered the FastAPI TestClient lifespan, and returned HTTP 200 from `/health`. Measured one-shot startup/import/lifespan/test duration was 4,415 ms on this host; 28 top-level routes were registered. This is an in-process feasibility measurement, not a production HTTP load benchmark. Initial assembly required installing `python-multipart` in addition to FastAPI; it was then successful.

The subprocess spike built and signed a full bundle, copied it to a new temporary path, invoked only its bundled Python with an isolated import path and minimal environment, loaded SQLite/sqlite-vec, served health, and completed import → local analysis → exact evidence → explicit DNA approval. Clean termination removed the socket. No system Python, Docker, uv or developer PATH was used at runtime. A separate clean Mac/VM is still required for AC-01.

AgentOS offers serving/session/tracing capabilities, but these are additional surfaces for a single-user native app whose durable editorial data and job gating must stay in its own repository. Direct IPC proves the needed lifecycle without a TCP listener, HTTP authentication layer or control-plane routes. This justifies the smaller runtime now; it does not imply AgentOS is unsuitable generally.

## Consequences

The application implements its own cancellation, replay and job recovery. Current UI uses event polling. Model calls use Agno agents within deterministic Python orchestration; full Agno Workflows/Teams and Skills are not yet implemented. Reconsider AgentOS when measured benefits from advanced orchestration exceed packaging/authentication costs, and rerun signing/lifecycle/network-exposure tests before adopting it.

Sources reviewed at implementation: [AgentOS runtime](https://docs.agno.com/agent-os/overview), [Agno agents](https://docs.agno.com/agents/overview), [model providers](https://docs.agno.com/models/providers/model-index). Installed package source, not unversioned documentation defaults, drives provider construction.
