# Lenovo ThinkPad Specs Scraper

Automated browser script that searches for AMD ThinkPads on Lenovo.com, filters and sorts results, then extracts detailed specifications of the best-selling product.

## Requirements

- Python 3.8+
- Playwright 1.48+

## Setup Instructions

1. Install dependencies:

```bash
   pip install -r requirements.txt
```

2. Install Playwright browsers:

```bash
   playwright install chromium
```

## Usage

Run the script:

```bash
python main.py
```

The program will:

1. Navigate to Lenovo.com
2. Search for "thinkpad"
3. Apply AMD processor filter
4. Sort by best selling
5. Extract and display specifications of the top result

## Output

The script prints formatted product information including:

- Product name and part number
- Price
- Detailed specifications (processor, memory, storage, etc.)

## Error Handling

- Automatically handles popup overlays
- Takes screenshots on failures (saved as `error_screenshot.png`)
- Includes proper wait times for dynamic content loading
