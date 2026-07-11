# Next Task

## ✅ Roadmap complete

All nine milestones (M1–M9) are implemented, tested, containerised, documented
and CI-gated. See [ROADMAP.md](ROADMAP.md) and [PROJECT_STATUS.md](PROJECT_STATUS.md)
for the full picture.

The project is production-ready and runnable:

```bash
docker compose up -d --build   # full stack
```

### Potential future enhancements (not on the current roadmap)

- Clustering task support (KMeans/DBSCAN + silhouette-based selection).
- S3/GCS implementation of the `Storage` interface.
- Playwright end-to-end tests for the frontend.
- Partial-dependence plots in the explainability view.
- Real-time training progress via WebSockets.
- Per-project collaborator roles (sharing beyond ownership).

Pick one and start a new vertical slice per the [Developer Guide](docs/developer-guide.md).
