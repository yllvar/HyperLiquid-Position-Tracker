# HyperLiquid Position Tracker, inspired by moondevonyt

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A comprehensive Python tool for real-time monitoring and analysis of positions on HyperLiquid DEX, with specialized features to identify positions approaching liquidation zones.

## ✨ Key Features

- **Real-time Monitoring**: Continuous position tracking via HyperLiquid's official SDK
- **Advanced Analytics**:
  - Top long/short positions identification
  - Coin-specific position breakdowns
  - Large position highlighting (>$2M)
- **Risk Metrics**:
  - Liquidation price calculations
  - Leverage analysis
  - Unrealized PnL tracking
- **Customizable Filters**:
  - Minimum position value threshold
  - Token-specific focus
  - Top N positions display

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip package manager

### Installation

```bash
git clone https://github.com/yllvar/HyperLiquid-Position-Tracker.git
cd HyperLiquid-Position-Tracker
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### Basic Usage

```bash
python see_all_positions.py
```

## ⚙️ Advanced Configuration

### Command Line Options

| Argument       | Description                          | Default |
|---------------|--------------------------------------|---------|
| `--min-value` | Minimum position value to display    | 25,000  |
| `--top-n`     | Number of positions to show         | 30      |
| `--coin`      | Filter by specific coin (BTC,ETH...) | All     |

Example:

```bash
python see_all_positions.py --min-value 50000 --top-n 15 --coin BTC
```

### Configuration File
Modify these constants in `see_all_positions.py`:

```python
MIN_POSITION_VALUE = 25000      # USD threshold
TOP_N_POSITIONS = 30            # Display limit
TOKENS_TO_ANALYZE = ['BTC', 'ETH', 'XRP', 'SOL']  # Coin filter
HIGHLIGHT_THRESHOLD = 2000000   # Large position alert level
```

## 📊 Output Sample

```
=== Top Long Positions ===
[$2.1M] BTC • 3.5x • Entry: $63,420
  Liq: $58,100 • PnL: +12.3%

[$850K] ETH • 5.2x • Entry: $3,420
  Liq: $3,120 • PnL: -4.2%

=== Top Short Positions ===
[...]
```

## 🛠 Technical Details

### Dependencies
- `hyperliquid-python-sdk`: Official HyperLiquid API interface
- `pandas`: Data processing and analysis
- `colorama`: Cross-platform colored terminal text
- `schedule`: Periodic task execution

### Error Handling
- API connection retries
- Data validation checks
- Graceful failure modes

## 🤝 Contributing

We welcome contributions! Please follow these steps:
1. Fork the repository
2. Create a feature branch 
3. Commit your changes
4. Push to the branch 
5. Open a Pull Request

## ⚠️ Important Disclaimer

**This software is provided for educational and informational purposes only.** Trading involves substantial risk of loss and is not suitable for every investor. Always:
- Conduct your own research
- Understand the risks involved
- Never trade with funds you cannot afford to lose

The maintainers are not responsible for any trading decisions made using this tool.


## 📜 License

MIT License - See [LICENSE](LICENSE) for full text.

---

🛠 Built with Python • 📈 For HyperLiquid traders • 🚀 By the DeFi community
