# Shooter

Shooter is a small 3D-ish first-person arena shooter written in **Python** using **Pygame** + **PyOpenGL**.

You fight a bot in a floating “tray” arena, swap between different weapons (AK47, Sniper, Shotgun, etc.), and experiment with bot difficulty and settings.

---

## 🔥 Project Status

🧪 **Project status: Beta**

The core **Duel** mode is playable, but the game is still in **beta**:

- Things may change or break
- Balancing is still being tweaked
- Visuals / feel might be updated

There used to be an experimental Free For All (FFA) mode, but it was too glitchy and has been **removed for now**.  
FFA may come back in the future when it’s stable.

---

## 🕹️ Features

- **First-person shooter** built in pure Python
- **Duel mode** – 1v1 vs a single bot (first to a certain number of kills)
- Multiple weapons, each with their own stats:
  - `Pistol`
  - `minigun`
  - `AK47`
  - `Spray Gun`
  - `Sniper`
  - `Shotgun`
- Bot AI profiles (different “personalities”), for example:
  - `AK47 Bot`
  - `Sniper Bot`
  - `Shotgun Bot`
  - `sweat` (more aggressive / sweaty profile)
- Simple 3D “tray” arena with obstacles and blocks
- Customizable **movement, FOV, arena size, sensitivity, etc.** via config files
- Health bars, hit feedback, muzzle flashes, shell casings, and a basic HUD

---

## 🎮 Controls

Default controls (you can change them in the code):

### In the menu

- `UP / DOWN` – Change bot profile
- `LEFT / RIGHT` – Change primary weapon
- `Q / E` – Change map
- `ENTER` – Start match
- `ESC` – Quit the game

*(If your build shows any extra menu options, they may be experimental.)*

### In game

- **Move** – `W A S D`
- **Jump** – `SPACE`
- **Sprint** – `Left Shift`
- **Look / Aim** – Move the mouse
- **Fire** – Left Mouse Button (LMB)
- **Aim down sights** – Right Mouse Button (RMB) (improves accuracy)
- **Reload** – `R`
- **Switch weapon**
  - `1` – Primary weapon (AK47, Sniper, etc.)
  - `2` – Pistol (secondary)
- **Quit / return to menu** – `ESC`

---

## 🧩 Game Mode: Duel

- 1 player vs 1 bot
- You choose:
  - Bot type
  - Primary weapon
  - Map (layouts defined in `geometry.py`)
- First to a certain number of kills (e.g. 5) wins the duel
- HUD shows:
  - Your HP
  - Bot HP
  - Ammo info

---

## 🛠️ Requirements

You’ll need:

- **Python 3.x**
- A desktop OS (Windows, Linux, or macOS) with working OpenGL drivers

Python packages:

- `pygame`
- `PyOpenGL`
- `PyOpenGL_accelerate` (optional but recommended)

---

## 🚀 Installation & Running

1. **Clone or download** this repository:

   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   cd YOUR_REPO_NAME
