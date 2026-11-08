"""Describing the building blocks of a recipe.

Every layer, warp and filter kind declares its parameters once, here, as
:class:`Param` objects. That single description drives validation of saved
files, default values, the Effect Studio's controls and the docs, so the
four can never disagree.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

Params = dict[str, Any]


@dataclass(frozen=True)
class Param:
    """One tunable value.

    Numeric params have ``low``/``high`` bounds and a ``step`` for the Studio;
    ``integer`` params are rounded. Choice params list their ``choices``.
    """

    name: str
    label: str
    default: Any
    low: float = 0.0
    high: float = 1.0
    step: float = 0.1
    integer: bool = False
    choices: tuple[str, ...] = ()

    def clean(self, value: Any) -> Any:
        """Coerce ``value`` into range; raises ``ValueError`` if it can't be."""
        if self.choices:
            if value not in self.choices:
                raise ValueError(f"{self.name} must be one of {', '.join(self.choices)}")
            return value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{self.name} must be a number")
        number = min(self.high, max(self.low, float(value)))
        return round(number) if self.integer else number

    def nudge(self, value: Any, direction: int) -> Any:
        """The next value up (``direction`` = 1) or down (-1), as the Studio steps it."""
        if self.choices:
            index = self.choices.index(value) if value in self.choices else 0
            return self.choices[(index + direction) % len(self.choices)]
        return self.clean(round(value + direction * self.step, 6))

    def format(self, value: Any) -> str:
        if self.choices or self.integer:
            return str(value)
        return f"{value:.2f}"


@dataclass(frozen=True)
class Kind:
    """A kind of layer, warp or filter: its name, its params and how to build it.

    ``build(params, t)`` returns the function for time ``t``: ``(x, y) -> value``
    for layers, ``(x, y) -> (x, y)`` for warps and ``value -> value`` for filters.
    """

    name: str
    label: str
    build: Callable[[Params, float], Callable]
    params: tuple[Param, ...] = ()
    summary: str = ""
    nouns: tuple[str, ...] = field(default=(), compare=False)  # for generated names

    def defaults(self) -> Params:
        return {p.name: p.default for p in self.params}

    def clean(self, given: Params) -> Params:
        """Defaults overlaid with ``given`` (validated); unknown keys are ignored."""
        params = self.defaults()
        for p in self.params:
            if p.name in given:
                params[p.name] = p.clean(given[p.name])
        return params


def registry(*kinds: Kind) -> dict[str, Kind]:
    return {kind.name: kind for kind in kinds}
