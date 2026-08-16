"""API layer: FastAPI routers and (in later phases) Pydantic schemas.

Per the approved FastAPI API Contract Specification, routes in this package
must remain thin: validate input, call a service function, return the
declared response model. No Excel/pandas/openpyxl logic belongs here.
"""
