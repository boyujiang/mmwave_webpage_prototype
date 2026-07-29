import json
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from mqtt_simulator import orchestrator
from mqtt_simulator import publisher
from mqtt_simulator.vitals import SCENARIOS, VitalsSimulator


class SimulatorTests(unittest.TestCase):
    def test_all_scenarios_match_contract(self):
        simulator = VitalsSimulator(seed=7)
        timestamp = datetime(2026, 7, 22, 12, tzinfo=timezone.utc)

        for scenario in SCENARIOS:
            payload = simulator.payload("101", scenario, timestamp)
            self.assertTrue(orchestrator.valid_payload(payload), scenario)

    def test_alert_states(self):
        simulator = VitalsSimulator(seed=7)
        timestamp = datetime(2026, 7, 22, 12, tzinfo=timezone.utc)

        fall = simulator.payload("101", "fall", timestamp)
        self.assertEqual(fall["activity_status"], "lying_down")
        self.assertFalse(fall["in_bed"])

        departure = simulator.payload("101", "departure", timestamp)
        self.assertFalse(departure["in_bed"])
        self.assertFalse(departure["in_room"])

    def test_dry_run_emits_each_room(self):
        options = publisher.build_parser().parse_args([
            "--dry-run",
            "--count",
            "1",
            "--room",
            "101",
            "--room",
            "102",
        ])
        rooms = publisher.validate_options(
            publisher.build_parser(),
            options,
        )
        output = []
        publisher.run(options, rooms, output.append)

        self.assertEqual(len(output), 2)
        for line in output:
            topic, raw_payload = line.split(" ", 1)
            self.assertTrue(topic.startswith("esp/room/"))
            self.assertTrue(
                orchestrator.valid_payload(json.loads(raw_payload))
            )

    @patch("mqtt_simulator.publisher.mqtt.Client")
    def test_publisher_uses_expected_topic(self, client_factory):
        client = client_factory.return_value
        result = MagicMock()
        result.rc = 0
        client.publish.return_value = result

        def connect(*args):
            client.on_connect(client, None, None, 0, None)

        client.connect.side_effect = connect
        options = publisher.build_parser().parse_args([
            "--count",
            "1",
            "--interval",
            "0",
            "--room",
            "101",
        ])
        publisher.run(options, ["101"], output=lambda _: None)

        topic, raw_payload = client.publish.call_args.args
        self.assertEqual(topic, "esp/room/101/vitals")
        self.assertTrue(
            orchestrator.valid_payload(json.loads(raw_payload))
        )


if __name__ == "__main__":
    unittest.main()
