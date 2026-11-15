import time
from typing import Dict, Any, List
from contextlib import contextmanager

class MetricsCollector:
    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.timers: Dict[str, List[float]] = {}
        self.events: List[Dict[str, Any]] = []
        self.gauges: Dict[str, float] = {}

    def increment(self, metric: str, value: int = 1):
        self.counters[metric] = self.counters.get(metric, 0) + value

    def record_time(self, metric: str, duration_ms: float):
        self.timers.setdefault(metric, []).append(duration_ms)

    def set_gauge(self, metric: str, value: float):
        self.gauges[metric] = value

    def log_event(self, event_name: str, payload: Dict[str, Any] = None):
        entry = {'name': event_name, 'timestamp': time.time()}
        if payload:
            entry.update(payload)
        self.events.append(entry)

    @contextmanager
    def timer(self, metric: str):
        start = time.time()
        try:
            yield
        finally:
            elapsed_ms = (time.time() - start) * 1000
            self.record_time(metric, elapsed_ms)

    def summary(self) -> Dict[str, Any]:
        return {
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'timers': {k: {'count': len(v), 'avg_ms': sum(v)/len(v) if v else 0} for k, v in self.timers.items()},
            'event_count': len(self.events),
        }

    def reset(self):
        self.counters.clear()
        self.timers.clear()
        self.events.clear()
        self.gauges.clear()

telemetry = MetricsCollector()
