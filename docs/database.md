# Database schema

PostgreSQL is the system of record. The schema is managed by Alembic; the initial
migration creates every table below. All primary keys are UUIDs and every table
carries `created_at` / `updated_at` audit timestamps.

## Entity–relationship diagram

```mermaid
erDiagram
    users ||--o{ refresh_tokens : has
    users }o--o{ roles : "user_roles"
    roles }o--o{ permissions : "role_permissions"

    users ||--o{ projects : owns
    projects ||--o{ datasets : contains
    datasets ||--o{ dataset_versions : "versions"

    projects ||--o{ experiments : contains
    datasets ||--o{ experiments : "trained on"
    experiments ||--o{ runs : "fans out to"

    projects ||--o{ models : registers
    experiments ||--o{ models : "promoted from"

    users ||--o{ notifications : receives
    users ||--o{ audit_logs : "acted"

    users {
        uuid id PK
        string email UK
        string hashed_password
        bool is_superuser
        datetime last_login_at
    }
    roles {
        uuid id PK
        string name UK
        bool is_system
    }
    permissions {
        uuid id PK
        string name UK
        string resource
        string action
    }
    projects {
        uuid id PK
        string slug
        uuid owner_id FK
        datetime deleted_at
    }
    datasets {
        uuid id PK
        string slug
        uuid project_id FK
        int latest_version
    }
    dataset_versions {
        uuid id PK
        uuid dataset_id FK
        int version
        string storage_key
        int n_rows
        int n_columns
        json statistics
    }
    experiments {
        uuid id PK
        uuid project_id FK
        uuid dataset_id FK
        string task_type
        string target_column
        string status
        uuid best_run_id
    }
    runs {
        uuid id PK
        uuid experiment_id FK
        string algorithm
        string status
        float primary_score
        json metrics
        string artifact_key
    }
    models {
        uuid id PK
        uuid project_id FK
        uuid run_id
        int version
        string stage
        string artifact_key
    }
    notifications {
        uuid id PK
        uuid user_id FK
        string type
        datetime read_at
    }
    audit_logs {
        uuid id PK
        uuid user_id FK
        string action
        int status_code
    }
```

## Notes

- **RBAC** — `users` acquire capabilities through `roles`; roles bundle
  `permissions` (`resource:action`). Nothing grants a permission to a user
  directly.
- **Soft deletes** — `projects`, `datasets` and `models` carry a nullable
  `deleted_at`; repositories exclude soft-deleted rows from every read.
- **Immutable versions** — `dataset_versions` and registered `models` are never
  mutated in place, underpinning reproducibility.
- **`experiments.best_run_id`** is an unconstrained UUID (not a foreign key) to
  avoid a circular dependency with `runs.experiment_id`; integrity is enforced in
  the service layer.
