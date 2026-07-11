# Next Task

## ▶ M7 — Model Registry, Prediction, Notifications, Audit

**Goal:** Promote trained runs into a versioned model registry, serve predictions
from deployed models, notify users of events, and record an audit trail.

### Scope (delivered as vertical slices)
1. **Model registry** (`Model` model + repo + service)
   - Register a completed run as a versioned `Model` in a project.
   - Stages: none → staging → production → archived (deploy = promote to
     production, demoting the previous production model).
   - List, get, compare models (metrics side-by-side), delete.
2. **Prediction API**
   - `POST /models/{id}/predict` — validate a JSON payload against the model's
     feature schema, run the persisted pipeline, return predictions (+ class
     probabilities for classifiers).
3. **Notifications**
   - `Notification` model + repo + service; list, unread count, mark-read.
   - Emitted on experiment completion and model deployment.
4. **Audit logs**
   - `AuditLog` model + service + middleware capturing mutating requests
     (actor, action, resource, status, ip). Admin-only listing endpoint.
5. **Tests** — registry promotion & compare, prediction round-trip, notification
   lifecycle, audit-log capture.

### Definition of done
- Deployed model serves predictions from JSON.
- Notifications and audit entries recorded and queryable.
- Unit + integration tests green; full suite passing.
- Atomic Conventional Commits; `PROJECT_STATUS.md` + this file updated.
