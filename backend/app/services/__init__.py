"""Service layer — application business logic.

Services orchestrate repositories, security primitives and domain rules. They are
the transaction boundary for use-cases and the only layer the API endpoints call
into, keeping HTTP concerns out of business logic and vice versa.
"""
