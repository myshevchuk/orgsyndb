"""What closing a task writes off: the states that close a task and the
text that names the amounts written off."""

from collections.abc import Iterable

from django.utils.formats import number_format

from inventory.models import VesselMovement, shown
from tasks.models import State

# The states in which a task is closed: its flasks are written off and
# take no booking.
CLOSED = (State.ENDED, State.FAILED, State.CANCELLED)


def amounts(movements: Iterable[VesselMovement]) -> str:
    """Return the amounts the ``remainder`` MOVEMENTS wrote off, each as
    its batch and the amount in its vessel's unit, such as ``KL0412 2 g``
    for a flask of the batch ``KL0412``, joined by ``, ``; empty for no
    movement."""
    return ", ".join(
        f"{movement.vessel.batch} "
        f"{number_format(shown(movement.amount, movement.vessel.unit))} "
        f"{movement.vessel.unit_label}" for movement in movements)
