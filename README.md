# Codex Sandbox

This repository contains example code for downloading public filings from the U.S. SEC EDGAR system and running OpenAI models on those documents.

## Requirements

- Python 3.8+
- `requests`
- `openai`
- `beautifulsoup4`
- `pandas`
- `openpyxl`

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Usage

The script `src/fetch_and_analyze.py` demonstrates how to download the two most recent 10-K or 10-Q filings for Apple (CIK `0000320193`) and summarize them using OpenAI's API.

Set your OpenAI API key in the environment:

```bash
export OPENAI_API_KEY=your-key-here
```

Run the script:

```bash
python src/fetch_and_analyze.py
```

Downloaded filings are stored in the `downloads/` directory. The script prints a short summary for each filing.

An Excel file named `financials.xlsx` will also be created in `downloads/` containing
income statement and balance sheet data with the most recent periods on the right.

**Note:** Network access is required to fetch filings from `sec.gov` and to call the OpenAI API. Make sure to respect the SEC's [terms of use](https://www.sec.gov/privacy) when downloading filings.
