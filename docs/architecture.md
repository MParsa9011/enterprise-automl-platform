# Architecture

The platform follows **Clean Architecture** with the dependency rule pointing
inward: the API depends on services, services depend on repositories, and
repositories depend on the ORM models. Cross-cutting concerns (config, logging,
security) live in `core`, and the framework-agnostic ML logic lives in `ml`.

## Layers

```mermaid
flowchart TB
    subgraph HTTP["API layer (app/api)"]
        R[Routers / endpoints]
        D[Dependencies · DI]
        MW[Middleware · errors]
    end
    subgraph SVC["Service layer (app/services)"]
        S[Use-cases]
    end
    subgraph REPO["Repository layer (app/repositories)"]
        Q[Data access]
    end
    subgraph MODEL["Models (app/models)"]
        M[SQLAlchemy ORM]
    end
    subgraph SUP["Supporting"]
        SC[schemas · DTOs]
        ST[storage]
        ML[ml · profiling/EDA/features/training]
    end

    R --> D --> S --> Q --> M
    MW -.-> R
    S --> ML
    S --> ST
    R --> SC
    S --> SC
```

**The dependency rule:** arrows point inward. An endpoint never touches the ORM
directly; it calls a service, which orchestrates repositories and domain logic.
This keeps business rules independent of FastAPI and SQLAlchemy, and makes every
collaborator overridable in tests.

## Request lifecycle

```mermaid
sequenceDiagram
    participant C as Client
    participant N as Nginx
    participant A as FastAPI
    participant Svc as Service
    participant DB as Postgres
    participant Q as Celery/Redis

    C->>N: HTTP request (/api/...)
    N->>A: proxy
    A->>A: request-id + security middleware
    A->>A: authn/z dependency (JWT + RBAC)
    A->>Svc: call use-case
    Svc->>DB: repository query (async session)
    Svc-->>A: DTO
    A->>Q: (training) enqueue Celery task
    A-->>C: JSON (uniform envelope)
    Q->>DB: worker persists runs/metrics
```

## Asynchronous training

Training is CPU-bound and can run for minutes, so it never executes inside a
request. The API enqueues a Celery task; a worker builds its own async session
and drives the shared `ExperimentService.run_experiment` orchestration — a single
code path used by both inline (test) and worker (production) execution.

## Key design decisions

- **Repository pattern** — a generic async `BaseRepository` provides pagination,
  filtering, sorting, search and a soft-delete hook; concrete repositories add
  only aggregate-specific queries.
- **Uniform error envelope** — every error (domain, validation, HTTP, unexpected)
  is rendered as one JSON shape with a correlation id.
- **Graceful ML degradation** — optional native libraries (XGBoost/LightGBM/
  CatBoost) are imported defensively; a missing library simply drops that
  algorithm from the registry.
- **Reproducibility** — datasets are immutably versioned; an experiment always
  references the exact version it trained on, and the fitted preprocessing +
  estimator pipeline is persisted together to eliminate training/serving skew.
