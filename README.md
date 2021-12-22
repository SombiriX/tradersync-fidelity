## Description

A quick and dirty script to convert Fidelity history reports into something importable into Tradersync and possibly other trade journaling software. A reasonable attempt has been made to deal with Fidelity's idiosyncrasies but I admit this probably won't deal with every corner case. See caveats for details and feel free to create an issue, or better yet, a pull request for bugs or features.

## Usage

1. Download your history report from Fidelity as a .csv file
1. Place the downloaded file into the `raw_reports` directory
1. In your terminal run: `python parse_history.py`
1. `output.csv` with the parsed data will appear in the `processed_output` directory

## Caveats

1. Order execution times are not available in the source data