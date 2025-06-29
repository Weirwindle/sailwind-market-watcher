# ⛵ Sailwind Market Watcher

A real-time market and trade route analyzer for the open-world sailing game **Sailwind**.

This tool connects to your running game, reads market data directly from memory, and helps you plan the most profitable trade routes between ports — all via an interactive graphical interface.

---

## 📌 Features

✅ **Live Memory Scan**  
Scans all 27 in-game markets for live product supply data and prices.

💰 **Profit-Driven Trade Routes**  
Automatically finds the most profitable trades based on:
- Total profit
- Profit per pound (weight)
- Profit per item

🎯 **Player-Conscious Filtering**  
Takes into account your current:
- Money
- Cargo mass & volume limits
- Minimum profit threshold

🌎 **Regional Trade Planning**  
Select specific **start** and **destination** island groups to tailor your strategy.

🖼️ **Interactive GUI**  
A modern, user-friendly interface with:
- Live-updating trade table
- Tooltips for helpful guidance
- Input fields for cargo & currency

---

### 🧭 Market Scan Example

![Market Finder GUI](MarketFinder.png)

## 🧰 Requirements

- Windows OS
- Python 3.9+
- The game [**Sailwind** on Steam](https://store.steampowered.com/app/1284190/Sailwind)
- Python dependencies:
  - `pymem`
  - `psutil`
  - `pillow`

Install dependencies with:

```bash
pip install -r requirements.txt
