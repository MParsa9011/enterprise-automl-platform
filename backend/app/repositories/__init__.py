"""Data-access layer implementing the Repository pattern.

Repositories are the *only* component that talks to the ORM. Services depend on
repository abstractions rather than on SQLAlchemy directly, which keeps business
logic persistence-agnostic and trivially testable with in-memory fakes.
"""
