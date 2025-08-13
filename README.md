# pepco-automation

End-to-end flow:
1) **Streamlit extractor** (PDF → CSV)  
2) **Illustrator Worker** runs `PEPCO.jsx` with the CSV → final print PDF

## Quick start
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run scripts/pep_data_app.py

