"""Hand-maintained lists over the generated effects.

``EXCLUDED`` is written by ``tools/curate.py``: seeds whose output fails the
quality gate (blank, frozen, a solid wall, or too slow). ``GALLERY`` is a hand-picked
selection of the best-looking ones, shown first in the browser.
"""

EXCLUDED: frozenset[int] = frozenset({142, 177, 219, 328, 432, 446, 775, 931})

# Picked by eye from the top-scoring seeds of `tools/curate.py --rank 100`.
GALLERY: tuple[int, ...] = (
    940, 435, 86, 409, 205, 75, 633, 874, 749, 990, 559, 671, 232, 55,
    804, 725, 883, 445, 744, 369, 979, 643, 531, 13, 875, 764, 610, 403,
    241, 842, 668, 736, 488, 546, 63, 879, 422, 674, 894, 602, 171, 793,
    690, 343, 714, 304, 355,
)  # fmt: skip
