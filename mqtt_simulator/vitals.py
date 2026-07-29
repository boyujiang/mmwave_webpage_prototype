"""Contract-valid, stateful simulated mmWave vital-sign readings."""

import random
from dataclasses import dataclass


ACTIVITIES = ("standing", "sitting", "walking", "lying_down")
SCENARIOS = ("normal", "fall", "departure", "mixed")


@dataclass
class RoomState:
    heart_rate: float
    respiration: float


class VitalsSimulator:
    """Maintain gently changing measurements for each simulated room."""

    def __init__(self, seed=None):
        self.random = random.Random(seed)
        self._rooms = {}

    def payload(self, room_number, scenario, timestamp):
        if scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}")

        state = self._rooms.setdefault(
            str(room_number),
            RoomState(
                heart_rate=self.random.uniform(64, 78),
                respiration=self.random.uniform(13, 18),
            ),
        )
        selected = self._select_scenario(scenario)

        if selected == "fall":
            activity = "lying_down"
            in_bed = False
            in_room = True
            heart_target, respiration_target = 105, 24
        elif selected == "departure":
            activity = "walking"
            in_bed = False
            in_room = False
            heart_target, respiration_target = 86, 19
        else:
            activity, in_bed = self._normal_activity(timestamp.hour)
            in_room = True
            heart_target = {
                "lying_down": 68,
                "sitting": 74,
                "standing": 80,
                "walking": 91,
            }[activity]
            respiration_target = {
                "lying_down": 14,
                "sitting": 16,
                "standing": 17,
                "walking": 20,
            }[activity]

        state.heart_rate += (
            (heart_target - state.heart_rate) * 0.35
            + self.random.uniform(-1.5, 1.5)
        )
        state.respiration += (
            (respiration_target - state.respiration) * 0.35
            + self.random.uniform(-0.5, 0.5)
        )

        return {
            "heart_rate": round(max(45, min(150, state.heart_rate)), 1),
            "respiration": round(
                max(8, min(35, state.respiration)),
                1,
            ),
            "activity_status": activity,
            "in_bed": in_bed,
            "in_room": in_room,
            "timestamp": timestamp.isoformat(),
        }

    def _select_scenario(self, scenario):
        if scenario != "mixed":
            return scenario

        roll = self.random.random()
        if roll < 0.05:
            return "fall"
        if roll < 0.10:
            return "departure"
        return "normal"

    def _normal_activity(self, hour):
        overnight = hour >= 22 or hour <= 6
        if overnight:
            activity = self.random.choices(
                ACTIVITIES,
                weights=(2, 4, 2, 92),
                k=1,
            )[0]
            return activity, activity == "lying_down"

        activity = self.random.choices(
            ACTIVITIES,
            weights=(15, 40, 25, 20),
            k=1,
        )[0]
        in_bed = (
            activity == "lying_down"
            and self.random.random() < 0.7
        )
        return activity, in_bed
