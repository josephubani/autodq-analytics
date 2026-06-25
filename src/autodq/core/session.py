from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SessionEvent:
    step: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class AutoDQSession:
    dataset_path: str
    started_at: datetime = field(default_factory=datetime.now)
    events: list[SessionEvent] = field(default_factory=list)

    def log(
        self,
        step: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            SessionEvent(
                step=step,
                message=message,
                metadata=metadata or {},
            )
        )

    @property
    def steps_completed(self) -> list[str]:
        return [event.step for event in self.events]

    @property
    def event_count(self) -> int:
        return len(self.events)

    def to_dict(self) -> dict:
        return {
            "dataset_path": self.dataset_path,
            "started_at": self.started_at.isoformat(),
            "event_count": self.event_count,
            "steps_completed": self.steps_completed,
            "events": [event.to_dict() for event in self.events],
        }

    def summary(self) -> None:
        print("\n=== AutoDQ Session Summary ===")
        print(f"Dataset: {self.dataset_path}")
        print(f"Started: {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Steps completed: {self.event_count}")

        print("\nWorkflow History:")

        if not self.events:
            print("- No workflow events recorded yet.")
            return

        for event in self.events:
            time = event.timestamp.strftime("%H:%M:%S")
            print(f"- [{time}] {event.step}: {event.message}")

            if event.metadata:
                for key, value in event.metadata.items():
                    print(f"    {key}: {value}")