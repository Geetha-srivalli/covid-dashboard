# COVID-19 Data Dashboard

A beginner-friendly interactive Streamlit prototype for exploring a COVID-19 workbook. It includes latest-date KPI cards, date/country/WHO region filters, three time-series charts, a top 10 country comparison, WHO region comparison, and a data table.

## Run it on Windows

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/). During setup, enable **Add Python to PATH**.
2. Put `app.py`, `requirements.txt`, and `COVID19_Filtered.xlsx` in the same folder. (The workbook was not included with this deliverable; you can instead upload it in the app.)
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
7. If the workbook is not beside `app.py`, use **Upload COVID-19 Excel workbook** in the left sidebar. The app automatically selects a sheet named `full_grouped` when available; you can change the sheet in the sidebar.

To stop the app, return to PowerShell and press **Ctrl+C**.

## Data handling

The app recognizes common variations of `Date`, `Country/Region`, `WHO Region`, `Confirmed`, `Deaths`, `Recovered`, and `Active`. Date and country plus at least one usable metric are required. Missing WHO Region is labeled `Unknown`; if Active is absent, it is calculated as Confirmed minus Deaths minus Recovered. Rows with zero values remain in the data.

Confirmed, deaths, recovered, and active in this dataset are cumulative snapshots. KPI cards and comparison charts therefore aggregate records only on the latest date in the current filters, rather than summing across the full date history. Time-series charts sum each day's selected country records.
