# Using StaticFX

- [The main view](#the-main-view)
- [Finding effects](#finding-effects)
- [Themes, filters and looks](#themes-filters-and-looks)
- [Screensaver mode](#screensaver-mode)
- [Settings and key bindings](#settings-and-key-bindings)
- [Command line](#command-line)
- [Where your things are saved](#where-your-things-are-saved)
- [Troubleshooting](#troubleshooting)

## The main view

Run `staticfx`. The first time, a welcome card lists the most useful keys; any
key dismisses it. After that StaticFX opens on whatever you were watching
last, with the theme and filters you had on.

Press `?` at any time for every key. That screen is built from your current
key bindings, so it stays correct after you rebind something.

Group | Keys | Action
--- | --- | ---
Browse | `→` `Space` | Next effect
Browse | `←` | Previous effect
Browse | `x` | Random effect
Browse | `b` | Back to the last effect
Browse | `a` | Auto-cycle through effects
Menus | `m` `Enter` | Browse and search effects
Menus | `t` | Choose a theme
Menus | `l` | Saved looks
Menus | `o` | Settings and key bindings
Menus | `?` `h` | All keys
Create | `n` | New effect in the Studio
Create | `e` | Edit this effect in the Studio
Create | `f` | Add to / remove from favourites
Create | `s` | Save effect + theme + filters as a look
Look | `c` | Next theme
Look | `v` | CRT scanlines filter
Look | `g` | Glitch filter
Look | `w` | Rainbow recolour filter
Playback | `p` | Pause
Playback | `z` | Restart the effect
Playback | `↑` `+` `=` | Faster
Playback | `↓` `-` | Slower
Playback | `i` | Show or hide the status bar
Playback | `q` | Quit

These work everywhere and can't be rebound:

Key | Action
--- | ---
`Esc` | Close the current menu. In the main view, press it twice to quit.
`Ctrl-C` | Close the current menu (the Studio asks first if you have unsaved changes), or quit from the main view.
`Ctrl-Z` | Suspend to your shell; `fg` brings StaticFX back.

The status bar (`i`) shows the effect, its group, the theme, the speed and
which filters are on.

## Finding effects

There are 50 hand-written effects, about a thousand generated ones, and
whatever you make yourself. Press `m` to open the browser:

- **Left column: groups.** All, Favourites, Recent, My Effects, Gallery (the
  best of the generated effects, picked by hand), the seven groups of
  built-ins, and Generated.
- **Right column: effects.** The highlighted one plays live behind the panel,
  so you can scroll and watch. Nothing changes until you press `Enter`.

Browser key | Action
--- | ---
`↑` `↓` `PgUp` `PgDn` `Home` `End` | Move
`←` `→` | Switch between the groups and the effects
`Tab` / `Shift-Tab` | Next / previous group
`Enter` | Play the highlighted effect
`/` | Search the selected group. Best matches (name first) come first. While you type, the arrows still move through the results, `Enter` plays, `Tab` keeps the filter and goes back to the list, and `Esc` clears it.
`f` | Add to / remove from favourites
`e` | Open in the Studio (generated effects and your own)
`n` | Start a new effect
`d` or `Del` | Delete one of your own effects (asks first)
`Esc` or `q` | Close

Every menu closes with `Esc` or `q`, and letters work with or without Shift.

Generated effects are numbered (`proc_042`) and stay the same forever, so a
favourite or a script that plays `proc_042` always gets the same picture.

## Themes, filters and looks

**Themes** colour everything: `t` opens the list, with a strip of each
theme's colours, and previews each one as you move; `Enter` keeps it and `Esc` goes back to the one you had. `c`
steps to the next theme without the menu. Rainbow is animated.

**Strobe** flashes rapidly, which can trigger seizures in people with
photosensitive epilepsy, so it's hidden until you turn on *Allow flashing* in
Settings (`o`).

**Filters** sit on top of any effect and theme: `v` CRT scanlines, `g`
glitch, `w` rainbow recolour (which keeps the effect's shading).

**Looks** save an effect together with its theme, speed and filters under a
name. Press `s` to save the current one; press `l` to browse yours and a dozen
built-in ones, with live preview. In the looks list, `s` saves too and
`d` deletes one of yours.

## Screensaver mode

`a` turns on auto-cycle, which moves to a new effect every 12 seconds (change
the interval in Settings). It picks from your favourites if you have at least
two, otherwise from the built-ins and the Gallery. It pauses while a menu is
open.

From the command line:

```bash
staticfx --auto 30                  # a new effect every 30 seconds
staticfx --auto 30 --duration 600   # ...and quit after ten minutes
staticfx --look "Deep Space"        # start from a look
```

## Settings and key bindings

Press `o`. Changes apply straight away and are saved.

Setting | What it does
--- | ---
Frame rate | Lower it if your terminal can't keep up (big windows over SSH, for example).
Characters | `auto` uses Unicode if your terminal supports it; `katakana` adds katakana to the rain effects; `ascii` is plain ASCII only.
Colours | `auto` guesses from `$COLORTERM`; pick `256` if colours look wrong, or `truecolor` to force full colour.
Auto-cycle every | How long each effect plays in auto-cycle.
Allow flashing | Unlocks the Strobe theme, after a warning.

Below those is every action in the main view. Select one and press `Enter`,
then press the key you want; it replaces the action's current keys. If that
key was doing something else, StaticFX tells you what it no longer does. `Backspace` unbinds an action. *Reset all
keys* puts everything back.

Only your changes are saved (as `"keybinds"` in `config.json`), so new default
keys in future versions reach you automatically.

## Command line

`staticfx` with no command runs the app. Everything else is a subcommand:

Command | What it does
--- | ---
`staticfx [play]` | Run the app. Options below.
`staticfx list [WORDS] [--kind builtin\|generated\|mine\|gallery] [--favorites]` | List or search effects.
`staticfx themes` | List themes.
`staticfx looks` | List your looks and the built-in ones.
`staticfx new NAME [--seed N]` | Create a random effect in My Effects.
`staticfx import FILE` | Add a `.sfx` file to My Effects.
`staticfx export EFFECT FILE` | Save one of your effects, or a generated one, as a `.sfx` file.
`staticfx render [EFFECT] [--size WxH] [--frames N] [--ansi] [--256] [--out FILE]` | Print one frame and exit. Handy for screenshots, CI, or your shell prompt.
`staticfx fetch [--tool fastfetch\|neofetch]` | Your system info over an effect.
`staticfx doctor` | Check your terminal and saved files, and render every effect once.

`play`, `render` and `fetch` share these options:

Option | Meaning
--- | ---
`-e`, `--effect EFFECT` | A key (`plasma`, `proc_042`, `my_sunrise`), a name (`"Matrix Rain"`), `proc42`, or `random`.
`-t`, `--theme THEME` | Start on a theme.
`--look NAME` | Start from a saved or built-in look.
`--speed X` | Animation speed (1.0 is normal).
`--crt`, `--glitch`, `--recolour` (and `--no-...`) | Filters.
`--ascii`, `--katakana` | Character set.
`--seed N` | Make random choices reproducible.
`--data-dir DIR` | Use another folder for settings and effects.

`play` also takes `--auto [SECS]`, `--duration SECS`, `--fps N`, `--256` and
`--no-save` (don't save settings on exit).

Run `staticfx COMMAND --help` for the details of any command. Flags from
StaticFX 1.x (`--list`, `--frames`, `--new-effect`, ...) still work.

## Where your things are saved

`~/.config/staticfx/` (or `$XDG_CONFIG_HOME/staticfx`, or `--data-dir`):

```
config.json      settings, favourites, recent effects, your key changes
looks.json       your saved looks
effects/*.sfx    effects you made or imported (format: docs/EFFECT_FORMAT.md)
```

All of them are written atomically, so a crash or a full disk can't leave a
half-written file. If you hand-edit one and make a mistake, StaticFX ignores
the bad value, tells you which one, and carries on.

## Troubleshooting

**Colours look wrong or washed out.** Your terminal probably doesn't support
24-bit colour. Set *Colours* to `256` in Settings, or run `staticfx --256`.

**Boxes and blocks show up as `?` or garbage.** Your terminal or font isn't
using UTF-8. Set *Characters* to `ascii`, or fix the locale (`echo $LANG`
should end in `UTF-8`).

**It's jerky.** Lower the frame rate in Settings or make the window smaller.
Generated effects lower their own detail automatically when a frame takes
too long.

**Something is off with a saved file.** `staticfx doctor` lists every file
that couldn't be read and why.

**Windows.** The interactive app needs a POSIX terminal: use WSL. `render`,
`list` and the other one-off commands work anywhere.
