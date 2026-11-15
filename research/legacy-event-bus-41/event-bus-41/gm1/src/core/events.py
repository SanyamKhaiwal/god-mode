from typing import Callable, Dict, Any, List

Handler = Callable[[Dict[str, Any]], None]

class EventBus:
    """Synchronous in-process event bus. Handlers run in subscription order."""

    def __init__(self):
        self._handlers: Dict[str, List[Handler]] = {}

    def subscribe(self, event_name: str, handler: Handler):
        handlers = self._handlers.setdefault(event_name, [])
        if handler not in handlers:
            handlers.append(handler)

    def unsubscribe(self, event_name: str, handler: Handler):
        handlers = self._handlers.get(event_name, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, event_name: str, payload: Dict[str, Any] = None):
        for handler in list(self._handlers.get(event_name, [])):
            handler(payload or {})

event_bus = EventBus()
