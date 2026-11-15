from collections import defaultdict
from typing import Any, Callable, Dict, List

Handler = Callable[[Dict[str, Any]], None]

class EventBus:
    """Synchronous in-process publish/subscribe bus.

    Handlers run in subscription order on the publisher's thread; exceptions
    propagate to the publisher, matching the previous direct-call behaviour.
    """
    def __init__(self):
        self._handlers: Dict[str, List[Handler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Handler) -> None:
        if handler not in self._handlers[event_name]:
            self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Handler) -> None:
        if handler in self._handlers.get(event_name, []):
            self._handlers[event_name].remove(handler)

    def publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        for handler in list(self._handlers.get(event_name, [])):
            handler(payload)

event_bus = EventBus()
