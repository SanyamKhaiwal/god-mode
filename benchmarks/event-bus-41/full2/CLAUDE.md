# Project notes

## Learnings
- Event-bus subscribers are registered on import of `src/services` (its `__init__.py`); new subscribing services must be added there or their handlers never fire.
