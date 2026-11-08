"""The hand-written effects, and the catalogue that names and groups them."""

from __future__ import annotations

from functools import partial

from staticfx.core.glyphs import BINARY, HEX
from staticfx.effects.builtin.fields import (
    Aurora,
    BlackHole,
    Galaxy,
    GridWave,
    HeatHaze,
    Kaleidoscope,
    LavaLamp,
    Nebula,
    OceanWaves,
    Plasma,
    RipplePond,
    Tunnel,
    Wormhole,
)
from staticfx.effects.builtin.particles import (
    ColumnRain,
    DriftParticles,
    Fireworks,
    Fountain,
    MeteorShower,
    OrbitalParticles,
    Starfield,
)
from staticfx.effects.builtin.shapes import Cube, DNAHelix, Lissajous, Spirograph, Tesseract
from staticfx.effects.builtin.signals import (
    ElectricStorm,
    SignalScramble,
    StaticNoise,
    TVGlitch,
    WaveBars,
)
from staticfx.effects.builtin.simulations import Fire, LangtonAnt, LifeLike, Maze, Rule30, Smoke
from staticfx.effects.builtin.terminal import BarcodeScan, Circuit, DecryptScramble, TerminalBoot
from staticfx.effects.spec import EffectSpec

RAIN = "Rain"
PARTICLES = "Particles"
SPACE = "Space"
FIELDS = "Waves & Fields"
GEOMETRY = "Geometry"
SIMULATIONS = "Simulations"
RETRO = "Retro Tech"

CATEGORIES = (RAIN, PARTICLES, SPACE, FIELDS, GEOMETRY, SIMULATIONS, RETRO)

# Drifting-particle presets, kept here so the catalogue below stays one row per effect.
snow = partial(
    DriftParticles, pool="*.+", speed=(1.5, 4.0), sway=1.5, density=0.035, tone=(0.7, 1.0)
)
sakura = partial(
    DriftParticles, pool="*@o", speed=(2.5, 6.0), sway=3.5, density=0.03, tone=(0.55, 0.95)
)
embers = partial(
    DriftParticles,
    pool=".,'`*",
    direction=-1,
    speed=(2.0, 7.0),
    sway=2.0,
    density=0.015,
    twinkle=True,
    tone=(0.3, 1.0),
)
bubbles = partial(
    DriftParticles, pool="oO0.", direction=-1, speed=(2.0, 5.0), sway=2.5, density=0.012
)
confetti = partial(
    DriftParticles, pool="#%@&=+", speed=(4.0, 10.0), sway=3.0, density=0.02, multicolor=True
)

# key, label, category, description, factory
CATALOGUE = (
    ("matrix", "Matrix Rain", RAIN, "The classic: falling glyphs with bright heads", ColumnRain),
    (
        "binary_rain",
        "Binary Rain",
        RAIN,
        "Ones and zeros pouring down",
        partial(ColumnRain, pool=BINARY, speed=11.0),
    ),
    (
        "hex_rain",
        "Hex Rain",
        RAIN,
        "Hexadecimal digits pouring down",
        partial(ColumnRain, pool=HEX, speed=13.0),
    ),
    (
        "glitch_cascade",
        "Glitch Cascade",
        RAIN,
        "Fast rain with blocks of corruption",
        partial(ColumnRain, speed=22.0, corrupt=True),
    ),
    ("snowfall", "Snowfall", PARTICLES, "Gently swaying snow", snow),
    ("sakura_rain", "Sakura Rain", PARTICLES, "Cherry blossom petals drifting down", sakura),
    ("embers", "Embers", PARTICLES, "Twinkling sparks rising from a fire", embers),
    ("bubbles", "Bubbles", PARTICLES, "Bubbles wobbling up to the surface", bubbles),
    ("confetti", "Confetti", PARTICLES, "A party in every colour of the theme", confetti),
    ("fireworks", "Fireworks", PARTICLES, "Rockets launching and bursting overhead", Fireworks),
    ("fountain", "Fountain", PARTICLES, "A jet of droplets arcing under gravity", Fountain),
    (
        "orbit_dance",
        "Orbit Dance",
        PARTICLES,
        "Counter-rotating rings of planets",
        partial(OrbitalParticles, mode="orbit"),
    ),
    (
        "vortex",
        "Vortex",
        PARTICLES,
        "Particles spiralling into a drain",
        partial(OrbitalParticles, mode="vortex"),
    ),
    (
        "gravity_well",
        "Gravity Well",
        PARTICLES,
        "Bodies slingshotting around a hidden mass",
        partial(OrbitalParticles, mode="well"),
    ),
    ("starfield", "Starfield", SPACE, "Flying forward through the stars", Starfield),
    (
        "meteor_shower",
        "Meteor Shower",
        SPACE,
        "Shooting stars across a twinkling sky",
        MeteorShower,
    ),
    ("nebula", "Nebula", SPACE, "Slow cosmic clouds among the stars", Nebula),
    ("galaxy", "Galaxy", SPACE, "A spiral galaxy turning", Galaxy),
    (
        "black_hole",
        "Black Hole",
        SPACE,
        "Accretion disk and photon ring around the void",
        BlackHole,
    ),
    ("wormhole", "Wormhole", SPACE, "Falling into a twisting tunnel of light", Wormhole),
    ("plasma", "Plasma", FIELDS, "Old-school demoscene plasma", Plasma),
    ("aurora", "Aurora", FIELDS, "Northern lights rippling across the sky", Aurora),
    ("ocean_waves", "Ocean Waves", FIELDS, "A rolling sea seen side-on", OceanWaves),
    ("ripple_pond", "Ripple Pond", FIELDS, "Raindrops landing on still water", RipplePond),
    ("lava_lamp", "Lava Lamp", FIELDS, "Blobs merging and splitting, slowly", LavaLamp),
    ("heat_haze", "Heat Haze", FIELDS, "Shimmering air above hot ground", HeatHaze),
    ("kaleidoscope", "Kaleidoscope", FIELDS, "Six-fold mirrored patterns", Kaleidoscope),
    ("tunnel", "Tunnel", FIELDS, "A checkered tunnel rushing past", Tunnel),
    ("grid_wave", "Grid Wave", FIELDS, "A synthwave floor scrolling to the horizon", GridWave),
    ("cube", "Cube", GEOMETRY, "A wireframe cube tumbling in 3D", Cube),
    ("tesseract", "Tesseract", GEOMETRY, "A 4D hypercube rotating through itself", Tesseract),
    ("spirograph", "Spirograph", GEOMETRY, "Hypotrochoid curves drawn by a pen", Spirograph),
    ("lissajous", "Lissajous", GEOMETRY, "Oscilloscope figures tracing themselves", Lissajous),
    ("dna_helix", "DNA Helix", GEOMETRY, "A rotating double helix", DNAHelix),
    ("game_of_life", "Game of Life", SIMULATIONS, "Conway's automaton, reseeding itself", LifeLike),
    ("rule30", "Rule 30", SIMULATIONS, "Wolfram's chaotic one-dimensional automaton", Rule30),
    ("langtons_ant", "Langton's Ant", SIMULATIONS, "Simple rules, emergent highway", LangtonAnt),
    (
        "turmite",
        "Turmite",
        SIMULATIONS,
        "Two ants with a four-colour rule",
        partial(LangtonAnt, rule="RLLR", ants=2),
    ),
    ("maze", "Maze", SIMULATIONS, "A maze carved live by depth-first search", Maze),
    ("fire", "Fire", SIMULATIONS, "The classic demoscene fire", Fire),
    ("smoke", "Smoke", SIMULATIONS, "Plumes drifting in a changing wind", Smoke),
    ("terminal_boot", "Terminal Boot", RETRO, "A computer booting up, endlessly", TerminalBoot),
    (
        "decrypt_scramble",
        "Decrypt",
        RETRO,
        "Scrambled text resolving into a message",
        DecryptScramble,
    ),
    ("barcode_scan", "Barcode Scan", RETRO, "A laser sweeping a barcode", BarcodeScan),
    ("circuit", "Circuit", RETRO, "Signals tracing paths across a circuit board", Circuit),
    ("static_noise", "Static", RETRO, "Untuned television snow", StaticNoise),
    ("tv_glitch", "TV Glitch", RETRO, "A test card with a failing signal", TVGlitch),
    (
        "signal_scramble",
        "Signal Scramble",
        RETRO,
        "Oscilloscope traces breaking up",
        SignalScramble,
    ),
    ("electric_storm", "Electric Storm", RETRO, "Forked lightning and crackle", ElectricStorm),
    ("wave_bars", "Spectrum", RETRO, "A bouncing audio spectrum analyser", WaveBars),
)


def builtin_specs() -> list[EffectSpec]:
    return [
        EffectSpec(key, label, description, category, factory)
        for key, label, category, description, factory in CATALOGUE
    ]
