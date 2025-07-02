# ⛵ Sailwind Market Watcher
![Market Finder GUI](MarketFinder.png)

A real-time market and trade route analyzer for the open-world sailing game **Sailwind**.

This tool connects to your running game, reads market data directly from memory, and helps you plan the most profitable trade routes between ports — all via an interactive graphical interface.

---

🚀 **How to Use**
1. Launch Sailwind
2. Once in-game, run main.py using Python
3. Click "Scan For Markets" in the GUI
4. Enter your player values:
    - Currency exchange rate
    - Cargo limits (mass/volume)
    - Available money
    - Minimum profit
5. Select your start and destination island groups
6. Browse the trade table for top opportunities!

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
💡 **Development**
This project is written in Python using:
- tkinter for the GUI
- pymem for memory access
- psutil for process handling
- Pillow for image icons

---
🧠 **How It Works**
This app reads Sailwind’s memory using pymem, scanning for a known pattern of market objects. 
It interprets product supplies and calculates dynamic prices using the game’s internal pricing formula.
It does not modify game memory or change game behavior.

💱 **Currency Conversion**
The game uses different currencies in different regions (Lions, Dragons, Crowns, etc).
To calculate trades properly:
1. Visit a Currency Exchange port in the game
2. Use the posted exchange rate to convert to Lions
3. Enter that value into the app’s Conversion Rate field

💡 Estimated values shown in the app:
    Lions ≈ 34.0
    Dragons ≈ 330
    Crowns ≈ 82.0
Use the actual in-game rate when possible for best results.

# Changelog

## [v1.1.0] - 2025-07-02
### Added
- Support for 2 new islands in latest Sailwind version
- 3 new tradeable items

### Fixed
- Fixed Emeralch Arch trades not showing because of a misname
- Removed Unneeded Library PSutil

## [v1.0.0] - 2025-06-29
### Added
- Initial release of Sailwind Market Watcher
- Trade route table and player settings input

## 🧰 Requirements

- Windows OS
- Python 3.9+
- The game [**Sailwind** on Steam](https://store.steampowered.com/app/1284190/Sailwind)
- Python dependencies:
  - `pymem`
  - `pillow`

Install dependencies with:

```bash
pip install -r requirements.txt
