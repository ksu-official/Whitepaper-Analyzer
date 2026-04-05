from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from datetime import datetime, timedelta
from collections import defaultdict
import fitz
import re
import os
import base64
import logging
from dotenv import load_dotenv
from groq import Groq
from prompts import FACTS_PROMPT, SUMMARY_PROMPT

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024

rate_limits = defaultdict(list)
RATE_LIMIT = 10
RATE_WINDOW = 3600
MAX_URL_SIZE = 30 * 1024 * 1024

def check_rate_limit(ip):
    now = datetime.now()
    window_start = now - timedelta(seconds=RATE_WINDOW)
    rate_limits[ip] = [t for t in rate_limits[ip] if t > window_start]
    if len(rate_limits[ip]) >= RATE_LIMIT:
        return False
    rate_limits[ip].append(now)
    return True

@app.after_request
def add_headers(response):
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
    return jsonify({'status': 'healthy', 'version': '3.4', 'timestamp': datetime.utcnow().isoformat()}), 200

def validate_url(url):
    if not url.startswith(('http://', 'https://')):
        return False, 'URL must start with http:// or https://'
    if any(url.startswith(p) for p in ['http://localhost', 'http://127.', 'http://192.168.', 'http://10.']):
        return False, 'Local URLs are not allowed'
    return True, None

def download_pdf_from_url(url):
    import requests as req
    try:
        head = req.head(url, timeout=10, allow_redirects=True)
        content_length = head.headers.get('Content-Length')
        if content_length and int(content_length) > MAX_URL_SIZE:
            return None, 'File too large. Maximum size is 30MB'
        response = req.get(url, timeout=15, stream=True)
        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            total += len(chunk)
            if total > MAX_URL_SIZE:
                return None, 'File too large. Maximum size is 30MB'
            chunks.append(chunk)
        return b''.join(chunks), None
    except Exception as e:
        return None, str(e)

def extract_text_or_ocr(pdf_bytes):
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
    texts = []
    for i in range(min(3, max_pages)):
        pix = doc[i].get_pixmap(dpi=150)
        img_b64 = base64.b64encode(pix.tobytes('png')).decode('utf-8')
        try:
            response = client.chat.completions.create(
                model='meta-llama/llama-4-scout-17b-16e-instruct',
                messages=[{'role': 'user', 'content': [
                    {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_b64}'}},
                    {'type': 'text', 'text': 'Extract all text from this whitepaper page. Return only the text, no comments.'}
                ]}],
                timeout=30
            )
            texts.append(response.choices[0].message.content)
            logger.info(f'OCR success on page {i+1}')
        except Exception as e:
            logger.error(f'OCR error on page {i+1}: {str(e)}')
            texts.append(f'[OCR error on page {i+1}]')
    return '\n'.join(texts)

def find_airdrop_info(text):
    keywords = ['airdrop', 'testnet rewards', 'community incentives',
                'retroactive', 'eligibility', 'claim', 'points program',
                'points system', 'early adopter', 'community rewards']
    quotes = []
    for keyword in keywords:
        for match in re.finditer(rf'([^.!?]*{keyword}[^.!?]*[.!?])', text, re.IGNORECASE):
            quote = match.group(1).strip()
            if quote and len(quote) < 200:
                quotes.append(quote)
    quotes = list(dict.fromkeys(quotes))[:3]
    return {'mentioned': len(quotes) > 0, 'quotes': quotes}

def find_supply(text):
    for pattern in [
        r'total supply[:\s]+([0-9,\.]+\s*[a-zA-Z]*)',
        r'maximum supply[:\s]+([0-9,\.]+\s*[a-zA-Z]*)',
        r'max supply[:\s]+([0-9,\.]+\s*[a-zA-Z]*)',
        r'circulating supply[:\s]+([0-9,\.]+\s*[a-zA-Z]*)',
        r'total[:\s]+([0-9,\.]+\s*[a-zA-Z]*\s*tokens?)',
        r'supply[:\s]+([0-9,\.]+\s*[a-zA-Z]*)',
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def find_vesting(text):
    for pattern in [
        r'(\d+)[- ]month(?:s)?\s*vesting', r'vesting[:\s]+(\d+)[- ]month',
        r'vesting\s+period[:\s]+(\d+)\s*month', r'locked?\s+for\s+(\d+)\s*month',
        r'(\d+)\s*month[s]?\s+lock', r'(\d+)\s*month[s]?\s+cliff', r'cliff[:\s]+(\d+)\s*month',
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1) + ' months'
    for pattern in [r'(\d+)[- ]year[s]?\s*vesting', r'vesting[:\s]+(\d+)[- ]year', r'locked?\s+for\s+(\d+)\s*year']:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return str(int(match.group(1)) * 12) + ' months'
    if 'vesting' in text.lower():
        return 'mentioned'
    return None

def find_allocation(text):
    matches = re.findall(r'([A-Za-z\s]+):\s*(\d+\.?\d*)\s*%', text)
    return {k.strip(): float(v) for k, v in matches[:10]} if matches else {}

def get_ai_summary(text, airdrop_info):
    try:
        excerpt = text[:8000]
        facts_response = client.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[{'role': 'user', 'content': FACTS_PROMPT.format(text=excerpt[:4000])}],
            timeout=15, max_tokens=400
        )
        facts = facts_response.choices[0].message.content
        logger.info('Facts extracted successfully')

        if airdrop_info['mentioned']:
            airdrop_context = "AIRDROP MENTIONED IN WHITEPAPER:\n" + "\n".join(airdrop_info['quotes'])
        else:
            airdrop_context = "AIRDROP: Not mentioned in whitepaper. User should check official channels."

        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': SUMMARY_PROMPT.format(facts=facts, airdrop_context=airdrop_context)}],
            timeout=25, max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f'AI summary error: {str(e)}')
        return f"AI summary unavailable: {str(e)}"

@app.route('/analyze', methods=['POST'])
def analyze():
    ip = request.remote_addr
    if not check_rate_limit(ip):
        logger.warning(f'Rate limit exceeded for {ip}')
        return jsonify({'error': f'Too many requests. Maximum {RATE_LIMIT} analyses per hour.'}), 429

    file = request.files.get('pdf')
    url = request.form.get('url')

    if file:
        logger.info(f'Analyzing PDF file: {file.filename}')
        pdf_bytes = file.read()
        if not pdf_bytes.startswith(b'%PDF'):
            return jsonify({'error': 'Invalid file format. Please upload a PDF'}), 400
    elif url:
        valid, error = validate_url(url)
        if not valid:
            logger.warning(f'Invalid URL rejected: {url}')
            return jsonify({'error': error}), 400
        logger.info(f'Downloading PDF from URL: {url}')
        pdf_bytes, error = download_pdf_from_url(url)
        if error:
            return jsonify({'error': error}), 400
        if not pdf_bytes.startswith(b'%PDF'):
            return jsonify({'error': 'URL does not point to a valid PDF'}), 400
    else:
        return jsonify({'error': 'No file or URL provided'}), 400

    full_text, pages = extract_text_or_ocr(pdf_bytes)
    airdrop_info = find_airdrop_info(full_text)

    result = {
        'pages': pages,
        'total_supply': find_supply(full_text),
        'allocation': find_allocation(full_text),
        'vesting': find_vesting(full_text),
        'airdrop_mentioned': airdrop_info['mentioned'],
        'airdrop_quotes': airdrop_info['quotes'],
        'summary': get_ai_summary(full_text, airdrop_info)
    }
    logger.info(f'Analysis complete: {pages} pages, supply={result["total_supply"]}, airdrop={airdrop_info["mentioned"]}')
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False, port=5000)
