# Sailwind Market Watcher

⛵ A real-time trade route analyzer for Sailwind. Connects directly to the running game, reads market memory, and helps you optimize for the most profitable routes.

---

## 🧭 Features

- 🔍 Scans all in-game markets (27 total)
- 📈 Calculates trade profit per item, per weight, and total
- ⚙️ Custom player settings (money, cargo weight, volume, currency)
- 🧠 Smart product pricing based on in-game supply
- 💡 Clean GUI with checkboxes, tooltips, and auto-updating trade table

---

## 💾 Requirements

- Windows
- Python 3.9+
- Game: [Sailwind on Steam](https://store.steampowered.com/app/1284190/Sailwind/)
- Python packages:  
  `pymem`, `psutil`, `pillow`, `tkinter`

To install dependencies:
```bash
pip install -r requirements.txt
