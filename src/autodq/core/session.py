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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionEvent":
        if not isinstance(data, dict):
            raise ValueError("Session event must be a dictionary.")

        try:
            timestamp = datetime.fromisoformat(str(data["timestamp"]))
            step = str(data["step"])
            message = str(data["message"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Invalid session event data.") from error

        metadata = data.get("metadata", {})

        if not isinstance(metadata, dict):
            raise ValueError("Session event metadata must be a dictionary.")

        return cls(
            step=step,
            message=message,
            timestamp=timestamp,
            metadata=metadata,
        )


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AutoDQSession":
        if not isinstance(data, dict):
            raise ValueError("Session data must be a dictionary.")

        try:
            dataset_path = str(data["dataset_path"])
            started_at = datetime.fromisoformat(str(data["started_at"]))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Invalid AutoDQ session data.") from error

        events_data = data.get("events", [])

        if not isinstance(events_data, list):
            raise ValueError("Session events must be a list.")

        return cls(
            dataset_path=dataset_path,
            started_at=started_at,
            events=[
                SessionEvent.from_dict(event)
                for event in events_data
            ],
        )

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
