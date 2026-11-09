# Stream format

`staticfx stream` writes animation frames to standard output for another
program to draw. It runs until the reader closes the pipe (or after
`--count N` frames).

```bash
staticfx stream plasma --size 120x40 --fps 20 --theme ocean
```

Every option from the "what to show" group works: `--effect`, `--theme`,
`--look`, `--speed`, the filters, `--seed`, `--ascii`.

## Format

The output is UTF-8. The first line is a header:

```
STATICFX-STREAM 1 <width> <height>
```

`1` is the format version. Each frame then starts with a line holding just
`F`, followed by exactly `<height>` row lines.

A row is a list of runs separated by the unit separator character (`0x1F`):

- `RRGGBB` followed by text: those characters, in that 24-bit colour
- `_N`: N empty (transparent) cells

Runs cover the row from left to right. Cells past the last run are empty.
Every character is one cell wide.

Example row: `_3` `1f` `ff8800##` `1f` `_2` `1f` `ffffff*` is three empty
cells, two orange `#`, two empty cells and a white `*`.

Frames come at the requested rate. A reader that only wants the latest frame
can read everything available and draw the last complete one.

## Stopping

Close the pipe or send `SIGTERM`. StaticFX exits with status 0 when the
reader goes away.
