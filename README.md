# HyperLiquid Position Tracker

A Python-based tool for monitoring and analyzing positions on HyperLiquid DEX, with a focus on identifying positions near liquidation. This tool helps traders make informed decisions by providing real-time insights into market positions.

## Features

- Real-time position tracking using official HyperLiquid SDK
- Display of top long and short positions
- Filtering by minimum position value
- Coin-specific analysis
- Automatic updates every minute
- Highlighting of large positions (>$2M)
- Detailed position information including:
  - Entry prices
  - Liquidation levels
  - Leverage
  - Unrealized PnL
  - Position values

## Prerequisites

- Python 3.9+
- pip (Python package installer)

## Installation

1. Clone the repository:
```bash
git clone <your-repository-url>
cd hyperliquid-position-tracker
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the script with default settings:
```bash
python see_all_positions.py
```

### Command Line Arguments

- `--min-value`: Set minimum position value to track (default: $25,000)
- `--top-n`: Number of top positions to display (default: 30)
- `--coin`: Filter positions by specific coin (e.g., BTC, ETH, SOL)

Example with arguments:
```bash
python see_all_positions.py --min-value 50000 --top-n 20 --coin BTC
```

## Output Format

The tool displays two main sections:
1. Top Long Positions
2. Top Short Positions

Each position shows:
- Position Value ($)
- Entry Price
- Unrealized PnL (%)
- Leverage
- Liquidation Price

Positions above $2M are highlighted in magenta for easy identification.

## Configuration

Default constants in `see_all_positions.py`:
```python
MIN_POSITION_VALUE = 25000
TOP_N_POSITIONS = 30
TOKENS_TO_ANALYZE = ['BTC', 'ETH', 'XRP', 'SOL']
HIGHLIGHT_THRESHOLD = 2000000
```

## Dependencies

- hyperliquid-python-sdk
- pandas
- numpy
- colorama
- schedule
- termcolor

## Error Handling

The script includes comprehensive error handling for:
- API connection issues
- Data processing errors
- Invalid input parameters

Error messages are color-coded for better visibility.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for informational purposes only. Do not make trading decisions solely based on this information. Always perform your own research and risk assessment.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.

## Acknowledgments

- HyperLiquid team for providing the Python SDK
- Contributors and users of this tool

---
Made with ❤️ for the HyperLiquid community
