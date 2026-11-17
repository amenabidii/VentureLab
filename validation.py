"""Phase 2 validation gate: the founder's observed results against the approved threshold.

The founder approves an exact experiment kit, including its success threshold and sample
size, before any result exists (the kit is fingerprinted and written only after that
approval). Afterwards the founder records what they observed, as cumulative counts. This
module decides, with fixed rules and no model, what those counts mean:

- VALIDATION_THRESHOLD_MET (GO): at least `threshold` of the planned participants showed
  the behaviour. GO means "go on to the next phase", never proof of demand.
- STOP_FAILED_VALIDATION_CONDITION (STOP): the threshold can no longer be reached even if
  every remaining planned participant succeeded. The recommendation is to stop this
  hypothesis or pivot back to Discover, not to lower the threshold or enlarge the sample.
- REPEAT_EXPERIMENT_INCOMPLETE (REPEAT): the result is still open; continue the experiment.

Rules that keep the result from being spun:
- the plan cannot be changed: more participants than the approved sample are refused;
- counts are cumulative and can only grow (successes never by more than participants);
- a GO or STOP result is final for that kit: a new experiment needs a new approved kit.

Every observation is labelled FOUNDER-REPORTED: VentureLab records what the founder says
they observed. It does not verify it and never invents or estimates observations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RESULT_SOURCE = "FOUNDER-REPORTED — entered by the founder, not independently verified"


class ResultRefused(ValueError):
    """The observation breaks a rule above (with the reason)."""


@dataclass(frozen=True)
class Plan:
    metric: str
    threshold: int
    sample_size: int


@dataclass(frozen=True)
class Outcome:
    decision: str  # GO, STOP or REPEAT
    rule: str
    meaning: str
    next_step: str

    def to_dict(self) -> dict[str, str]:
        return dict(self.__dict__)


def evaluate(plan: Plan, participants: int, successes: int) -> Outcome:
    remaining = plan.sample_size - participants
    if successes >= plan.threshold:
        return Outcome(
            "GO", "VALIDATION_THRESHOLD_MET",
            f"{successes} of {participants} participants met the condition; the approved threshold was "
            f"{plan.threshold} of {plan.sample_size}. This is one founder-reported experiment on a problem proxy, "
            "not proof of demand, of a market or of future sales.",
            "Go on to the next phase (design the business and a narrow MVP), and test willingness to pay before "
            "building more.")
    if successes + remaining < plan.threshold:
        return Outcome(
            "STOP", "STOP_FAILED_VALIDATION_CONDITION",
            f"{successes} of {participants} participants met the condition; even if all {remaining} remaining "
            f"planned participants did, the approved threshold of {plan.threshold} of {plan.sample_size} cannot "
            "be reached. The pre-set condition has failed.",
            "Stop this hypothesis, or pivot back to Discover with a different customer or problem. Do not lower "
            "the threshold or enlarge the sample after seeing the result; a new idea needs a new approved kit.")
    return Outcome(
        "REPEAT", "REPEAT_EXPERIMENT_INCOMPLETE",
        f"{successes} of {participants} participants so far; {plan.threshold - successes} more successes are "
        f"needed among the {remaining} remaining planned participants.",
        "Continue the experiment with the remaining planned participants, then record the new totals.")


def check_observation(plan: Plan, previous: list[dict[str, Any]], participants: int, successes: int) -> None:
    """Raise ResultRefused if this observation would bend the approved plan."""
    if not 0 <= successes <= participants:
        raise ResultRefused("Successes must be between 0 and the number of participants")
    if participants < 1:
        raise ResultRefused("Record at least one participant")
    if participants > plan.sample_size:
        raise ResultRefused(f"The approved plan was {plan.sample_size} participants; a larger sample after "
                            "seeing results is not allowed. Prepare and approve a new kit instead")
    if previous:
        last = previous[-1]
        if last["outcome"]["decision"] in ("GO", "STOP"):
            raise ResultRefused(f"This experiment already ended in {last['outcome']['decision']} "
                                f"({last['outcome']['rule']}); its result is final")
        if participants < last["participants"] or successes < last["successes"]:
            raise ResultRefused("Counts are cumulative totals and cannot go down")
        if successes - last["successes"] > participants - last["participants"]:
            raise ResultRefused("New successes cannot exceed new participants")
