# COVID-19 Data Dashboard

A beginner-friendly interactive Streamlit app for exploring a COVID-19 workbook. Its six sections appear as tabs beneath the dashboard title: Overview, Data Analysis, Country Details, World Map, Upload & Preview, and Data & About. Large KPI values are compactly formatted, with the exact count available by hovering over a card. Analysis includes daily changes, recovery and case-fatality rates, country/region comparisons, and CSV export.

## Run it on Windows

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/). During setup, enable **Add Python to PATH**.
2. Put `app.py`, `requirements.txt`, and (if available) `COVID19_Filtered.xlsx` in the same folder. The workbook is included in this project folder.
3. Open that folder in File Explorer. Click the address bar, type `powershell`, and press Enter.
4. Install the app packages:

   ```powershell
   py -m pip install -r requirements.txt
   ```

5. Start the dashboard:

   ```powershell
   py -m streamlit run app.py
   ```

6. Streamlit will open the dashboard in your browser. If it does not, copy the `Local URL` shown in PowerShell (usually `http://localhost:8501`) into your browser.
7. To explore a different dataset, upload a CSV or Excel workbook in the left sidebar. Excel workbooks can contain multiple sheets; the app prefers a sheet named `full_grouped` and lets you choose another sheet.

To stop the app, return to PowerShell and press **Ctrl+C**.

## Data handling

The app recognizes common variations of `Date`, `Country/Region`, `WHO Region`, `Confirmed`, `Deaths`, `Recovered`, `Active`, and daily measure columns. Date, country, confirmed, deaths, and recovered are required. Missing WHO Region is labeled `Unknown`; if Active is absent, it is calculated as Confirmed minus Deaths minus Recovered. Rows with zero values remain in the data.

Confirmed, deaths, recovered, and active are cumulative snapshots. KPI cards and comparisons aggregate records only on the latest date in the current filters, rather than across the full date history. If daily measures are missing, the app derives date-to-date differences by country. Negative daily values are retained because they may reflect source corrections.

## Visitor uploads

Visitors can upload their own CSV or Excel file and use the dashboard sections to explore it. The preview starts at the newest available date and ranks countries by confirmed cases, while retaining legitimate zeros. An upload is temporary to that visitor's app session; it does not replace or alter the shared workbook and is not written to a database.
