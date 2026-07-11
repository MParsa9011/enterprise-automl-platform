"""Machine-learning subsystem.

Pure, framework-agnostic ML logic — data loading, profiling, EDA, feature
engineering and model training — lives here, decoupled from the web and
persistence layers so it can be unit-tested and reused from Celery workers.
"""
