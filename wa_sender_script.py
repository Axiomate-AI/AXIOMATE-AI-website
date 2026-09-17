name: WA Scheduled Sender Workflow

on:
  schedule:
    # Runs hourly during IST working window (Mon-Sat, 9:30 AM to 6:30 PM IST)
    - cron: '0 4-13 * * 1-6'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  run-wa-script:
    runs-on: ubuntu-latest
    steps:
      - name: Check out Repository
        uses: actions/checkout@v4

      - name: Set up Python Environment
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytz requests pandas

      - name: Execute WhatsApp Sender Script
        env:
          GREEN_API_ID_INSTANCE: ${{ secrets.GREEN_API_ID_INSTANCE }}
          GREEN_API_TOKEN_INSTANCE: ${{ secrets.GREEN_API_TOKEN_INSTANCE }}
        run: |
          python wa_sender_script.py

      - name: Auto-Save Leads History to Repo
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add leads_history.json || true
          git commit -m "Auto-update sent leads history [skip ci]" || echo "No history changes to commit"
          git push || true
