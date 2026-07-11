# API Reference

The full, always-current API reference is the OpenAPI schema served by the
application:

- **Swagger UI:** `/docs`
- **ReDoc:** `/redoc`
- **OpenAPI JSON:** `/api/v1/openapi.json`

All endpoints are versioned under `/api/v1`. Responses use a uniform error
envelope, and list endpoints share a common pagination shape.

## Conventions

### Pagination

List endpoints accept `page`, `size`, `sort_by`, `order` and `search`, and return:

```json
{
  "items": [ ... ],
  "meta": { "page": 1, "size": 20, "total": 42, "pages": 3, "has_next": true, "has_prev": false }
}
```

### Error envelope

```json
{
  "error": { "code": "not_found", "message": "Project not found.", "details": null },
  "request_id": "b3f1c2..."
}
```

## Endpoint overview

| Area | Method & path | Permission |
|------|---------------|------------|
| Auth | `POST /auth/register` · `POST /auth/login` · `POST /auth/refresh` · `POST /auth/logout` · `GET /auth/me` | public / bearer |
| Projects | `GET/POST /projects` · `GET/PATCH/DELETE /projects/{id}` | `project:*` |
| Datasets | `POST /projects/{id}/datasets` · `GET /datasets/{id}` · `POST /datasets/{id}/versions` · `GET /datasets/{id}/versions/{v}` · `.../download` | `dataset:*` |
| EDA | `GET /datasets/{id}/versions/{v}/eda` · `POST /datasets/{id}/versions/{v}/feature-preview` | `dataset:read` |
| Experiments | `GET/POST /projects/{id}/experiments` · `GET /experiments/{id}` · `GET /experiments/{id}/runs` · `.../runs/{run}` · `.../runs/{run}/explain` | `experiment:*` |
| Models | `POST /models` · `GET /projects/{id}/models` · `GET /models/{id}` · `POST /models/{id}/deploy` · `PATCH /models/{id}/stage` · `GET /models/compare` · `POST /models/{id}/predict` | `model:*`, `prediction:create` |
| Notifications | `GET /notifications` · `GET /notifications/unread-count` · `POST /notifications/{id}/read` · `POST /notifications/read-all` | bearer |
| Audit | `GET /audit-logs` | `audit:read` |
| Health | `GET /health/live` · `GET /health/ready` | public |

## Authentication

Obtain a token pair from `POST /auth/login`, then send the access token as a
bearer header:

```http
Authorization: Bearer <access_token>
```

When the access token expires, exchange the refresh token at `POST /auth/refresh`
— the platform rotates refresh tokens, so each one is single-use.

## Example: predict

```bash
curl -X POST http://localhost:8000/api/v1/models/$MODEL_ID/predict \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"records": [{"age": 42, "income": 88000, "gender": "F"}]}'
```

```json
{
  "model_id": "…", "model_version": 1, "task_type": "classification",
  "predictions": [{ "prediction": "1", "probabilities": { "0": 0.18, "1": 0.82 } }]
}
```
