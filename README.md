WHITEPAPER ANALYZER
AI-powered tool for analyzing crypto whitepapers — upload a PDF or paste a URL, get tokenomics & risk analysis in seconds.
Live: vault3.xyz/analyzer
Features
* 🔍 Extracts total supply, allocation, vesting period
* ⚠️ Risk score 0–10 based on tokenomics signals
* 📊 Visual doughnut chart for token distribution
* 🚩 Green / yellow / red flag system
* 🤖 9-section AI summary via Groq LLaMA 3.3 70B
* 📸 OCR fallback for scanned PDFs via vision model
* 🔗 Supports PDF upload and URL input
Stack
LayerTech FrontendHTML, CSS, JS — Netlify BackendPython, Flask, PyMuPDF AIGroq API — llama-3.3-70b-versatile OCRGroq Vision — llama-4-scout-17b Proxynginx + Let's Encrypt HostingUbuntu VPS
Project Structure

```
/
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   └── particles.js
│
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   └── .env   ← local only, never commit
│
├── v3.PNG
├── .gitignore
└── README.md

```

Local Development
Frontend — open `index.html` in browser.
Backend:

```bash
pip install -r requirements.txt
python app.py

```

Create `/backend/.env`:

```
GROQ_API_KEY=your_key_here

```

Built by
@ksu-official — Web3 believer 👠  Part of vault3 ecosystem.
