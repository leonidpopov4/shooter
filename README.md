# Shooter

A small first-person Python arena shooter I built for fun.

You fight a bot in a simple 3D-ish arena, swap weapons, and mess with different settings in the code.

---

## Status

✅ **Project status: Finished**

The game is basically **complete**.  
From here on, I only plan small updates:

- bug fixes
- tiny tweaks / balance changes
- maybe some visual polish

No huge new systems or rewrites are planned.

---

## Features

- First-person arena shooter built with Python
- 1v1 **duel** vs a bot (first to 5 kills)
- Bot AI that moves and shoots back
- Multiple weapons with different behavior (`weapons.py`)
- Simple OpenGL-style arena rendering (`render.py`)
- All the important knobs in one place (`settings.py`)

---

## Controls

_Default controls (can be changed in the code):_

- **Move** – `W A S D`
- **Jump** – `SPACE`
- **Sprint** – `Shift` (if enabled)
- **Shoot** – Left mouse button
- **Look around** – Mouse
- **Switch weapon** – Number keys (e.g. `1`, `2`)
- **Reload** – `R`
- **Quit / exit game** – `ESC`

---

## How to Run

You’ll need **Python 3.x** and a desktop OS (Windows/Linux/macOS) with working graphics drivers.

1. Install dependencies:

   ```bash
   pip install pygame PyOpenGL PyOpenGL_accelerate
