from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from datetime import datetime
import fitz
import re
import os
import base64
import logging
from dotenv import load_dotenv
from groq import Groq

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Environment & Groq client
load_dotenv()
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

app = Flask(__name__)
CORS(app)

# Limit upload size
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024  # 30MB


@app.after_request
def add_headers(response):
    # Allow embedding (frontend uses iframe in some cases)
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    return response


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(e):
    logger.warning('File too large rejected')
    return jsonify({'error': 'File too large. Maximum size is 30MB'}), 413


@app.errorhandler(500)
def server_error(e):
    logger.error(f'Server error: {str(e)}')
    return jsonify({'error': 'Internal server error'}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'version': '2.1',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


def validate_url(url):
    # Block local/internal URLs
    if not url.startswith(('http://', 'https://')):
        return False, 'URL must start with http:// or https://'
    if any(url.startswith(prefix) for prefix in [
        'http://localhost', 'http://127.', 'http://192.168.', 'http://10.'
    ]):
        return False, 'Local URLs are not allowed'
    return True, None


def extract_text_or_ocr(pdf_bytes):
    # Try direct text extraction; fallback to OCR if needed
    with fitz.open(stream=pdf_bytes, filetype='pdf') as doc:
        pages = len(doc)
        max_pages = min(20, pages)

        full_text = ''.join(doc[i].get_text() for i in range(max_pages))
        logger.info(f'Extracted {len(full_text)} chars from {pages} pages')

        if len(full_text.strip()) < 100:
            logger.info('Low text detected, switching to OCR')
            full_text = ocr_with_vision(doc, max_pages)

        return full_text, pages


def ocr_with_vision(doc, max_pages):
    # OCR for first few pages (usually enough for tokenomics)
    texts = []
    for i in range(min(3, max_pages)):
        pix = doc[i].get_pixmap(dpi=150)
        img_bytes = pix.tobytes('png')
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')

        try:
            response = client.chat.completions.create(
                model='meta-llama/llama-4-scout-17b-16e-instruct',
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'image_url',
                         'image_url': {'url': f'data:image/png;base64,{img_b64}'}},
                        {'type': 'text',
                         'text': 'Extract all text from this page. Return only the text.'}
                    ]
                }],
                timeout=30
            )
            texts.append(response.choices[0].message.content)
            logger.info(f'OCR success on page {i+1}')
        except Exception as e:
            logger.error(f'OCR error on page {i+1}: {str(e)}')
            texts.append(f'[OCR error on page {i+1}]')

    return '\n'.join(texts)


@app.route('/analyze', methods=['POST'])
def analyze():
    file = request.files.get('pdf')
    url = request.form.get('url')

    # File upload
    if file:
        logger.info(f'Analyzing PDF file: {file.filename}')
        pdf_bytes = file.read()
        if not pdf_bytes.startswith(b'%PDF'):
            return jsonify({'error': 'Invalid file format. Please upload a PDF'}), 400

    # URL input
    elif url:
        valid, error = validate_url(url)
        if not valid:
            logger.warning(f'Invalid URL rejected: {url}')
            return jsonify({'error': error}), 400

        try:
            import requests as req
            logger.info(f'Downloading PDF from URL: {url}')
            response = req.get(url, timeout=15)
            pdf_bytes = response.content

            if not pdf_bytes.startswith(b'%PDF'):
                return jsonify({'error': 'URL does not point to a valid PDF'}), 400

        except Exception as e:
            logger.error(f'URL download error: {str(e)}')
            return jsonify({'error': f'Could not download PDF: {str(e)}'}), 400

    else:
        return jsonify({'error': 'No file or URL provided'}), 400

    full_text, pages = extract_text_or_ocr(pdf_bytes)

    result = {
        'pages': pages,
        'total_supply': find_supply(full_text),
        'allocation': find_allocation(full_text),
        'vesting': find_vesting(full_text),
        'summary': get_ai_summary(full_text)
    }

    logger.info(f'Analysis complete: {pages} pages, supply={result["total_supply"]}')
    return jsonify(result)


def find_supply(text):
    patterns = [
        r'total supply[:\s]+([0-9,\.]+\s*[a-zA-Z]*)',
        r'maximum supply[:\s]+([0-9,\.]+\s*[a-zA-Z]*)',
        r'max supply[:\s]+([0-9,\.]+\s*[a-zA-Z]*)',
        r'circulating supply[:\s]+([0-9,\.]+\s*[a-zA-Z]*)',
        r'total[:\s]+([0-9,\.]+\s*[a-zA-Z]*\s*tokens?)',
        r'supply[:\s]+([0-9,\.]+\s*[a-zA-Z]*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def find_vesting(text):
    # Month-based vesting
    patterns = [
        r'(\d+)[- ]month(?:s)?\s*vesting',
        r'vesting[:\s]+(\d+)[- ]month',
        r'vesting\s+period[:\s]+(\d+)\s*month',
        r'locked?\s+for\s+(\d+)\s*month',
        r'(\d+)\s*month[s]?\s+lock',
        r'(\d+)\s*month[s]?\s+cliff',
        r'cliff[:\s]+(\d+)\s*month',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1) + ' months'

    # Year-based vesting → convert to months
    year_patterns = [
        r'(\d+)[- ]year[s]?\s*vesting',
        r'vesting[:\s]+(\d+)[- ]year',
        r'locked?\s+for\s+(\d+)\s*year',
    ]
    for pattern in year_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return str(int(match.group(1)) * 12) + ' months'

    if 'vesting' in text.lower():
        return 'mentioned'

    return None


def find_allocation(text):
    matches = re.findall(r'([A-Za-z\s]+):\s*(\d+\.?\d*)\s*%', text)
    return {k.strip(): float(v) for k, v in matches[:10]} if matches else {}


def get_ai_summary(text):
    try:
        excerpt = text[:6000]

        prompt = f"""You are a crypto research analyst. Analyze this whitepaper and provide a structured report:

1. Project overview
2. Technology stack
3. Token utility
4. Tokenomics (supply, distribution, vesting)
5. Target audience
6. Team & backers
7. Risks
8. Airdrop potential
9. Verdict (rate 1–10)

Whitepaper text:
{excerpt}"""

        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            timeout=20
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f'AI summary error: {str(e)}')
        return f"AI summary unavailable: {str(e)}"


if __name__ == '__main__':
    # For production: run behind gunicorn/uvicorn + reverse proxy
    app.run(host='0.0.0.0', debug=False, port=5000)
