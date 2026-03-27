# gotchi

`gotchi` is a terminal virtual pet aimed at pubnix-style communities (e.g. Runv.Club). Each Unix user has a single persistent pet. Simulation is real-time without a resident daemon: state is recomputed every time the command runs, based on elapsed time since the last saved update.

The default visual identity follows a terminal crow: watchful, a little mischievous, and witty enough to feel alive without being childish.

![gotchi terminal UI](img/pet.jpeg)

## Installation

Requires Python 3.9+.

```bash
python3 -m pip install .
```

This installs the command:

```bash
gotchi
```

For local development:

```bash
python3 -m pip install -e .
python3 -m unittest discover -s tests
```

## Usage

```bash
gotchi
gotchi init --name Nyx --species crow
gotchi status
gotchi feed
gotchi play
gotchi sleep
gotchi clean
gotchi rename Pixel
gotchi doctor
gotchi help
```

With no arguments, `gotchi` opens the main text screen with ASCII art, status bars, a mood line, contextual hints, and an action menu.

## Persistence and configuration

- Preferred SQLite database: `$XDG_DATA_HOME/runv-pet/gotchi.db`
- Automatic database fallback: user home directory or `.gotchi-data/` in the current workspace when needed
- Optional config (preferred): `$XDG_CONFIG_HOME/runv-pet/gotchi.json`
- Automatic config fallback: other user paths when the primary XDG location is unavailable

To generate an initial tuning file:

```bash
gotchi init --write-config
```

The config file lets you adjust rates such as hunger per hour, energy loss, and illness threshold using JSON from the standard library only.

## Architecture

The project is split into small modules:

- `src/gotchi_app/cli.py` — command parsing and orchestration
- `src/gotchi_app/simulator.py` — business rules, time progression, and actions
- `src/gotchi_app/storage.py` — per-user SQLite persistence
- `src/gotchi_app/ui.py` — text and ASCII rendering
- `src/gotchi_app/config.py` — XDG paths and optional tuning
- `src/gotchi_app/models.py` — immutable pet model
- `src/gotchi_app/runv_mode.py` — passive environment health for special display modes

This keeps I/O separate from simulation and makes it easier to test core logic without the terminal.

## Simulation model

MVP rules:

- `hunger` increases over time
- `energy` decreases over time
- `hygiene` decreases over time
- during sleep, energy rises and degradation changes
- `mood` is recomputed from overall comfort and health
- `health` worsens when hunger, energy, or hygiene fall into a bad range
- the pet becomes ill when health drops below the configured threshold
- the pet dies when health reaches zero from prolonged neglect

All stats are clamped between `0` and `100`.

Bands shown in status (string keys used in the app):

- `excelente`
- `bem`
- `atencao`
- `critico`

## Tests

Tests cover:

- degradation over time
- feeding
- sleep
- cleaning
- illness
- death
- persistence round-trip
- config resilience
- special server-mode rendering

Run:

```bash
python3 -m unittest discover -s tests
```

## Assumptions

- the Unix user is identified with `getpass.getuser()`
- there is only one pet per user
- `gotchi init` only creates a pet when none exists or none is alive
- the `doctor` command improves health but does not revive dead pets
- the MVP UI is rich text on stdout, without `curses`, to keep the scope robust
- if the default XDG path cannot be used, the app falls back automatically so it keeps working
