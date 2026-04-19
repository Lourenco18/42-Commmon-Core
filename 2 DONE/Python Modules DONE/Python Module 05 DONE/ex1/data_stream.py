#!/usr/bin/env python3
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Union, Optional


class DataStream(ABC):

    def __init__(self, stream_id: str, stream_type: str) -> None:
        self.stream_id: str = stream_id
        self.stream_type: str = stream_type
        self.processed_count: int = 0

    @abstractmethod
    def process_batch(self, data_batch: List[Any]) -> str:
        pass

    def filter_data(
        self, data_batch: List[Any], criteria: Optional[str] = None
    ) -> List[Any]:
        if criteria is None:
            return data_batch
        return [
            item for item in data_batch
            if criteria.lower() in str(item).lower()
        ]

    def get_stats(self) -> Dict[str, Union[str, int, float]]:
        return {
            "stream_id": self.stream_id,
            "stream_type": self.stream_type,
            "processed_count": self.processed_count,
        }


class SensorStream(DataStream):

    def __init__(self, stream_id: str) -> None:
        super().__init__(stream_id, "Environmental Data")

    def process_batch(self, data_batch: List[Any]) -> str:
        if not isinstance(data_batch, list):
            return "Invalid batch: expected a list"

        try:
            valid_readings = [
                item for item in data_batch
                if isinstance(item, str) and ":" in item
            ]

            temps = [
                float(item.split(":")[1])
                for item in valid_readings
                if item.startswith("temp:")
            ]

            self.processed_count += len(valid_readings)

            avg_temp = sum(temps) / len(temps) if temps else 0.0

            return (
                f"Sensor analysis: {len(valid_readings)} readings processed, "
                f"avg temp: {avg_temp:.1f}°C"
            )
        except Exception as error:
            return f"Sensor stream error: {error}"

    def filter_data(
        self, data_batch: List[Any], criteria: Optional[str] = None
    ) -> List[Any]:
        if criteria == "high":
            return [
                item for item in data_batch
                if isinstance(item, str)
                and item.startswith("temp:")
                and float(item.split(":")[1]) > 30
            ]
        return super().filter_data(data_batch, criteria)


class TransactionStream(DataStream):

    def __init__(self, stream_id: str) -> None:
        super().__init__(stream_id, "Financial Data")

    def process_batch(self, data_batch: List[Any]) -> str:
        if not isinstance(data_batch, list):
            return "Invalid batch: expected a list"

        try:
            operations = [
                item for item in data_batch
                if isinstance(item, str) and ":" in item
            ]

            net_flow = 0
            for op in operations:
                action, value = op.split(":")
                amount = int(value)

                if action == "buy":
                    net_flow += amount
                elif action == "sell":
                    net_flow -= amount

            self.processed_count += len(operations)

            return (
                f"Transaction analysis: {len(operations)} operations, "
                f"net flow: {net_flow:+d} units"
            )
        except Exception as error:
            return f"Transaction stream error: {error}"

    def filter_data(
        self, data_batch: List[Any], criteria: Optional[str] = None
    ) -> List[Any]:
        if criteria == "large":
            return [
                item for item in data_batch
                if isinstance(item, str)
                and ":" in item
                and int(item.split(":")[1]) > 100
            ]
        return super().filter_data(data_batch, criteria)


class EventStream(DataStream):

    def __init__(self, stream_id: str) -> None:
        super().__init__(stream_id, "System Events")

    def process_batch(self, data_batch: List[Any]) -> str:
        if not isinstance(data_batch, list):
            return "Invalid batch: expected a list"

        try:
            events = [
                item for item in data_batch
                if isinstance(item, str)
            ]

            error_count = len(
                [event for event in events if event.lower() == "error"]
            )

            self.processed_count += len(events)

            return (
                f"Event analysis: {len(events)} events, "
                f"{error_count} error detected"
            )
        except Exception as error:
            return f"Event stream error: {error}"


def main() -> None:
    print("=== CODE NEXUS - POLYMORPHIC STREAM SYSTEM ===")

    print("\nInitializing Sensor Stream...")
    sensor = SensorStream("SENSOR_001")
    print(f"Stream ID: {sensor.stream_id}, Type: {sensor.stream_type}")

    sensor_batch = ["temp:22.5", "humidity:65", "pressure:1013"]
    print(f"Processing sensor batch: [{', '.join(sensor_batch)}]")
    print(sensor.process_batch(sensor_batch))

    print("\nInitializing Transaction Stream...")
    transaction = TransactionStream("TRANS_001")
    print(f"Stream ID: {transaction.stream_id},"
          f"Type: {transaction.stream_type}")

    transaction_batch = ["buy:100", "sell:150", "buy:75"]
    print(f"Processing transaction batch: [{', '.join(transaction_batch)}]")
    print(transaction.process_batch(transaction_batch))

    print("\nInitializing Event Stream...")
    event = EventStream("EVENT_001")
    print(f"Stream ID: {event.stream_id}, Type: {event.stream_type}")

    event_batch = ["login", "error", "logout"]
    print(f"Processing event batch: [{', '.join(event_batch)}]")
    print(event.process_batch(event_batch))

    print("\n=== Polymorphic Stream Processing ===")
    print("Processing mixed stream types through unified interface...")

    streams: List[DataStream] = [
        SensorStream("SENSOR_002"),
        TransactionStream("TRANS_002"),
        EventStream("EVENT_002"),
    ]

    batches: List[List[Any]] = [
        ["temp:35", "temp:40"],  # 2 high alerts
        ["buy:200", "sell:50", "sell:75", "buy:25"],
        ["login", "error", "logout"],
    ]

    print("\nBatch 1 Results:")

    streams[0].process_batch(batches[0])
    streams[1].process_batch(batches[1])
    streams[2].process_batch(batches[2])

    print(
       f"- Sensor data: {streams[0].processed_count} readings processed"
    )
    print(
        f"- Transaction data:"
        f" {streams[1].processed_count} operations processed"
    )
    print(
        f"- Event data: {streams[2].processed_count} events processed"
    )

    print("\nStream filtering active: High-priority data only")

    filtered_sensor = streams[0].filter_data(batches[0], "high")
    filtered_transaction = streams[1].filter_data(batches[1], "large")

    print(
        f"Filtered results: {len(filtered_sensor)} critical sensor alerts, "
        f"{len(filtered_transaction)} large transaction"
    )

    print("\nAll streams processed successfully. Nexus throughput optimal")


if __name__ == "__main__":
    main()
