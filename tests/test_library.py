"""Settings, the user's effects and looks: saving, loading, and surviving bad files."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from staticfx.effects.engine import generate
from staticfx.library import config
from staticfx.library.config import Settings
from staticfx.library.effects import EffectLibrary, UserEffect, export, parse
from staticfx.library.files import atomic_write, clean_name, slugify
from staticfx.library.looks import BUILTIN_LOOKS, Look, LookStore, find_look

FIXTURES = Path(__file__).parent / "fixtures"


def test_atomic_write_replaces_and_leaves_no_temp_files(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "file.json"
    atomic_write(target, "one")
    atomic_write(target, "two")
    assert target.read_text() == "two"
    assert [p.name for p in target.parent.iterdir()] == ["file.json"]


@pytest.mark.parametrize(
    ("name", "slug"), [("Neon Sunrise!", "neon_sunrise"), ("   ", "effect"), ("../../etc", "etc")]
)
def test_slugify_makes_safe_file_names(name: str, slug: str) -> None:
    assert slugify(name) == slug


def test_clean_name() -> None:
    assert clean_name("  a   b\tc ") == "a b c"
    assert len(clean_name("x" * 100)) == 40


def test_missing_config_gives_defaults(tmp_path: Path) -> None:
    assert config.load(tmp_path / "config.json") == (Settings(), [])


def test_settings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    settings = Settings(
        effect="plasma", theme="ocean", fps=45, favorites=["matrix"], keybinds={"y": "crt"}
    )
    config.save(settings, path)
    assert config.load(path) == (settings, [])


@pytest.mark.parametrize("content", ["{not json", "[1, 2]", "\xff\xfe", ""])
def test_unreadable_config_falls_back_to_defaults(tmp_path: Path, content: str) -> None:
    path = tmp_path / "config.json"
    path.write_bytes(content.encode("latin-1"))
    settings, warnings = config.load(path)
    assert settings == Settings() and len(warnings) == 1


def test_each_bad_value_is_dropped_with_a_warning(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "version": 3,
                "theme": "plaid",
                "fps": "fast",
                "crt": "yes",
                "favorites": "matrix",
                "keybinds": ["y"],
                "characters": "emoji",
                "speed": 99,
                "effect": "plasma",
            }
        )
    )
    settings, warnings = config.load(path)
    assert settings.theme == "matrix" and settings.fps == 30 and settings.crt is False
    assert settings.favorites == [] and settings.characters == "auto"
    assert settings.speed == 5.0  # clamped, not rejected
    assert settings.effect == "plasma"
    assert len(warnings) == 6  # theme, fps, crt, favorites, keybinds, characters


def test_version_1_config_is_migrated() -> None:
    settings, warnings = config.load(FIXTURES / "v1_config.json")
    assert warnings == []
    assert settings.theme == "mono"  # renamed theme
    assert settings.recolour is True  # was "rainbow"
    assert settings.colour == "256"  # was "use_256_color"
    assert settings.characters == "katakana"  # was "unicode"
    assert settings.keybinds == {"y": "crt"}
    assert settings.favorites == ["matrix", "gen_007", "plasma"]  # unknown keys are dropped later


def test_library_save_load_delete(tmp_path: Path) -> None:
    library = EffectLibrary(tmp_path / "effects")
    recipe, _ = generate(7)
    effect = UserEffect(library.unique_id("Neon"), "Neon", recipe, "my first")
    library.save(effect)
    assert library.unique_id("Neon") == "neon_2"
    loaded, problems = library.load()
    assert problems == [] and len(loaded) == 1
    assert loaded[0].key == "my_neon" and loaded[0].recipe.to_dict() == recipe.to_dict()
    library.delete("neon")
    library.delete("neon")  # deleting twice is fine
    assert library.load() == ([], [])


def test_bad_files_are_reported_not_fatal(tmp_path: Path) -> None:
    folder = tmp_path / "effects"
    folder.mkdir()
    (folder / "broken.sfx").write_text("{nope")
    (folder / "wrong.sfx").write_text('{"format": "something-else"}')
    (folder / "future.sfx").write_text('{"format": "staticfx-effect", "version": 99}')
    (folder / "binary.sfx").write_bytes(b"\xff\xfe\x00")
    EffectLibrary(folder).save(UserEffect("good", "Good", generate(1)[0]))
    effects, problems = EffectLibrary(folder).load()
    assert [e.id for e in effects] == ["good"]
    assert len(problems) == 4
    assert any("newer StaticFX" in p for p in problems)


def test_version_2_studio_file_from_staticfx_1_loads() -> None:
    effect = parse((FIXTURES / "v1_studio_effect.sfx").read_text(), "old")
    assert effect.name == "Old Studio Effect"
    assert effect.recipe.layers and effect.recipe.seed == 4242


def test_1x_plugin_converts_to_a_layer() -> None:
    effect = parse((FIXTURES / "v1_plugin.sfx").read_text(), "wavy")
    assert effect.name == "Wavy Plugin"
    assert effect.recipe.layers[0].kind == "grid"
    assert effect.recipe.palette.kind == "duo"


def test_legacy_plugins_folder_is_imported(tmp_path: Path) -> None:
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    shutil.copy(FIXTURES / "v1_plugin.sfx", plugins / "wavy.sfx")
    (plugins / "bad.sfx").write_text("nope")
    library = EffectLibrary(tmp_path / "effects")
    count, problems = library.import_legacy_plugins(plugins)
    assert count == 1 and len(problems) == 1
    assert [e.name for e in library.load()[0]] == ["Wavy Plugin"]
    assert library.import_legacy_plugins(tmp_path / "missing") == (0, [])


def test_import_and_export_round_trip(tmp_path: Path) -> None:
    library = EffectLibrary(tmp_path / "effects")
    source = export(UserEffect("x", "Shared", generate(3)[0]), tmp_path / "shared.sfx")
    first = library.import_file(source)
    second = library.import_file(source)
    assert (first.id, second.id) == ("shared", "shared_2")  # never overwrites
    with pytest.raises(ValueError, match="can't read"):
        library.import_file(tmp_path / "missing.sfx")


def test_looks_store_round_trip(tmp_path: Path) -> None:
    store = LookStore(tmp_path / "looks.json")
    assert store.put(Look("Calm", "plasma", "ocean", 0.5)) is False
    assert store.put(Look("calm", "fire", "fire")) is True  # same name, any case
    reloaded = LookStore(tmp_path / "looks.json")
    assert reloaded.load() == []
    assert [(look.name, look.effect) for look in reloaded.looks] == [("calm", "fire")]
    reloaded.remove("CALM")
    assert reloaded.looks == []


def test_1x_looks_file_loads_and_skips_broken_entries(tmp_path: Path) -> None:
    store = LookStore(FIXTURES / "v1_looks.json")
    problems = store.load()
    assert len(problems) == 1
    assert store.looks[0].recolour is True and store.looks[0].theme == "cyberpunk"


def test_unreadable_looks_file(tmp_path: Path) -> None:
    path = tmp_path / "looks.json"
    path.write_text("[]")
    store = LookStore(path)
    assert store.load() and store.looks == []


def test_find_look_prefers_yours() -> None:
    store = LookStore(None)
    store.put(Look("Synthwave", "plasma"))
    assert find_look("synthwave", store).effect == "plasma"
    assert find_look("Campfire", store) in BUILTIN_LOOKS
    assert find_look("nope", store) is None
