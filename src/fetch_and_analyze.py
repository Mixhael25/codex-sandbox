import os
import requests
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

import pandas as pd


@dataclass
class Company:
    ticker: str
    cik: str
    investor_relations_urls: List[str] = field(default_factory=list)


class EdgarClient:
    """Simple client for downloading filings from SEC EDGAR."""

    BASE_SUBMISSION_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

    def __init__(self, user_agent: str):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
        })

    def get_company_filings(self, cik: str) -> Dict:
        """Retrieve submission data for a company."""
        url = self.BASE_SUBMISSION_URL.format(cik=cik)
        r = self.session.get(url)
        r.raise_for_status()
        return r.json()

    def download_filing(self, cik: str, accession: str, primary_doc: str, output_dir: str) -> str:
        """Download the primary document of a filing."""
        accession_no = accession.replace("-", "")
        base_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_no}"
        doc_url = f"{base_url}/{primary_doc}"
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, primary_doc)
        with self.session.get(doc_url, stream=True) as resp:
            resp.raise_for_status()
            with open(file_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        return file_path


def summarize_with_chatgpt(text: str, prompt: str, api_key: str) -> str:
    """Send the text to OpenAI's API using the given prompt."""
    import openai

    openai.api_key = api_key
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": text},
    ]
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
    return response["choices"][0]["message"]["content"]


def download_company_filings(company: Company, forms: Optional[List[str]] = None, count: int = 1,
                             output_dir: str = "downloads", user_agent: str = "ExampleBot") -> List[str]:
    """Download recent filings for the company."""
    forms = forms or ["10-K", "10-Q"]
    client = EdgarClient(user_agent=user_agent)
    data = client.get_company_filings(company.cik)
    recent = data.get("filings", {}).get("recent", {})
    downloaded_files = []
    for idx, form in enumerate(recent.get("form", [])):
        if form in forms:
            accession = recent["accessionNumber"][idx]
            primary_doc = recent["primaryDocument"][idx]
            file_path = client.download_filing(company.cik, accession, primary_doc, output_dir)
            downloaded_files.append(file_path)
            if len(downloaded_files) >= count:
                break
    return downloaded_files


def _find_statement_table(tables: List[pd.DataFrame], keywords: List[str]) -> Optional[pd.DataFrame]:
    """Return the first table containing any of the keywords."""
    for df in tables:
        try:
            first_col = df.iloc[:, 0].astype(str).str.lower()
        except Exception:
            continue
        for kw in keywords:
            if first_col.str.contains(kw).any():
                return df
    return None


def extract_financial_tables(file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Attempt to extract income statement and balance sheet tables from an HTML filing."""
    with open(file_path, "r", errors="ignore") as f:
        html = f.read()
    tables = pd.read_html(html)
    income = _find_statement_table(tables, ["net income", "total revenue"])
    balance = _find_statement_table(tables, ["total assets", "total liabilities"])
    return income, balance


def _sort_by_period(df: pd.DataFrame) -> pd.DataFrame:
    """Sort statement columns chronologically with the latest period on the right."""
    if df is None or df.empty:
        return df
    df = df.copy()
    base = df.columns[0]
    cols = df.columns[1:]
    try:
        dates = pd.to_datetime(cols, errors="coerce")
        order = dates.argsort()
        ordered = [cols[i] for i in order]
        df = pd.concat([df[[base]], df[ordered]], axis=1)
    except Exception:
        pass
    return df


def export_financials_to_excel(files: List[str], output_path: str = "downloads/financials.xlsx") -> None:
    """Combine financial statements from filings and export them to an Excel file."""
    income_frames = []
    balance_frames = []
    for path in files:
        income, balance = extract_financial_tables(path)
        if income is not None:
            income = _sort_by_period(income).set_index(income.columns[0])
            income_frames.append(income)
        if balance is not None:
            balance = _sort_by_period(balance).set_index(balance.columns[0])
            balance_frames.append(balance)
    if income_frames:
        income_df = pd.concat(income_frames, axis=1)
    else:
        income_df = pd.DataFrame()
    if balance_frames:
        balance_df = pd.concat(balance_frames, axis=1)
    else:
        balance_df = pd.DataFrame()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with pd.ExcelWriter(output_path) as writer:
        income_df.to_excel(writer, sheet_name="Income Statement")
        balance_df.to_excel(writer, sheet_name="Balance Sheet")
    print(f"Financials exported to {output_path}")


def main():
    example_company = Company(ticker="AAPL", cik="0000320193",
                              investor_relations_urls=["https://www.apple.com/newsroom/archive/"])
    api_key = os.getenv("OPENAI_API_KEY", "")
    files = download_company_filings(example_company, count=2, user_agent="MyResearchBot")
    for file in files:
        with open(file, "r", errors="ignore") as f:
            text = f.read()
        summary = summarize_with_chatgpt(text[:10000], "Summarize the following filing:", api_key)
        print(f"Summary for {file}:\n{summary}\n")
    export_financials_to_excel(files)


if __name__ == "__main__":
    main()
