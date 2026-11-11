from collections import defaultdict
from typing import Any, Callable, Dict, List

Handler = Callable[[Dict[str, Any]], None]

class EventBus:
    """Synchronous in-process publish/subscribe bus."""

    def __init__(self):
        self._handlers: Dict[str, List[Handler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Handler) -> None:
        if handler not in self._handlers[event_name]:
            self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Handler) -> None:
        if handler in self._handlers.get(event_name, []):
            self._handlers[event_name].remove(handler)

    def publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        # Handlers run in subscription order; exceptions propagate to the
        # publisher, matching the old direct-call behaviour.
        for handler in list(self._handlers.get(event_name, [])):
            handler(payload)

    def handlers(self, event_name: str) -> List[Handler]:
        return list(self._handlers.get(event_name, []))

event_bus = EventBus()
