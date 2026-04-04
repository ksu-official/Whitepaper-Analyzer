pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

// File label update
const fileInput = document.getElementById('file-input');
const fileLabel = document.getElementById('file-label');

fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) {
        fileLabel.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 18 18" style="vertical-align:middle; margin-right:8px;">
                <polyline points="3,9 7,13 15,5" fill="none" stroke="#515578" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        ` + fileInput.files[0].name;

        fileLabel.classList.add('has-file');
    }
});

// Error helpers
function showError(message) {
    const box = document.getElementById('errorBox');
    box.textContent = message;
    box.classList.remove('hidden');
}

function hideError() {
    document.getElementById('errorBox').classList.add('hidden');
}

// Analyze button
document.getElementById('analyze-btn').addEventListener('click', async () => {
    const url = document.getElementById('url-input').value.trim();
    const file = fileInput.files[0];

    if (!url && !file) {
        showError('Please paste a URL or upload a PDF!');
        return;
    }

    hideError();

    if (file) {
        await sendToBackend(file, null);
    } else {
        await sendToBackend(null, url);
    }
});

// Backend request
async function sendToBackend(file, url) {
    showLoading();

    try {
        const formData = new FormData();
        if (file) formData.append('pdf', file);
        else formData.append('url', url);

        const response = await fetch('https://api.ksuverse.online:8443/analyze', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        renderDashboard(data);

    } catch (error) {
        alert('Error connecting to backend.');
        console.error(error);
    }
}

// Loading state
function showLoading() {
    const results = document.getElementById('results');
    results.style.display = 'block';

    document.getElementById('r-supply').textContent = '...';
    document.getElementById('r-pages').textContent = '...';
    document.getElementById('r-vesting').textContent = '...';
    document.getElementById('r-risk').textContent = '...';
}

// Dashboard renderer
function renderDashboard(data) {
    document.getElementById('results').style.display = 'block';

    document.getElementById('r-supply').textContent = data.total_supply || 'N/A';
    document.getElementById('r-pages').textContent = data.pages;

    const vestingEl = document.getElementById('r-vesting');

    if (data.vesting && data.vesting !== 'mentioned') {
        vestingEl.textContent = '🔒 ' + data.vesting;
        vestingEl.style.color = 'var(--accent5)';
    } else if (data.vesting === 'mentioned') {
        vestingEl.textContent = '📋 Mentioned';
        vestingEl.style.color = '#ffc800';
    } else {
        vestingEl.textContent = '⚡ Not found';
        vestingEl.style.color = 'var(--accent2)';
    }

    const riskScore = calculateRisk(data);
    const riskEl = document.getElementById('r-risk');
    riskEl.textContent = riskScore + '/10';
    riskEl.style.color =
        riskScore > 6 ? 'var(--accent2)' :
        riskScore > 3 ? '#ffc800' :
        'var(--accent5)';

    renderChart(data.allocation);
    renderFlags(data);

    if (data.summary) {
        document.getElementById('r-summary').textContent = data.summary;
    }
}

// Risk score
function calculateRisk(data) {
    let score = 0;

    if (!data.vesting) score += 3;

    if (data.allocation) {
        const team = data.allocation['Team'] || data.allocation['team'] || 0;
        const investors = data.allocation['Investors'] || data.allocation['investors'] || 0;
        const community = data.allocation['Community'] || data.allocation['community'] || 0;

        if (team > 25) score += 2;
        if (investors > community) score += 2;
        if (investors > 20) score += 1;
    }

    return Math.min(score, 10);
}

// Chart
let chartInstance = null;

function renderChart(allocation) {
    const canvas = document.getElementById('chart-allocation');

    if (!allocation || Object.keys(allocation).length === 0) {
        canvas.style.display = 'none';
        return;
    }

    if (chartInstance) chartInstance.destroy();

    const labels = Object.keys(allocation);
    const values = Object.values(allocation);

    const colors = [
        '#e1edec',
        '#7c5a66',
        '#a5a4b5',
        '#979d99',
        '#f1f2f4'
    ];

    const ctx = canvas.getContext('2d');

    chartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 0,
                borderColor: 'transparent',
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            cutout: '75%',
            spacing: 2,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#444466',
                        font: { family: 'Noto Sans', size: 14, weight: '600' },
                        padding: 16
                    }
                }
            }
        }
    });
}

// Flags
function renderFlags(data) {
    const container = document.getElementById('r-flags');
    container.innerHTML = '';

    const flags = [];

    if (!data.vesting) {
        flags.push({ type: 'yellow', text: '⚡ No vesting found — tokens unlock at TGE' });
    } else if (data.vesting === 'mentioned') {
        flags.push({ type: 'yellow', text: '📋 Vesting mentioned but period not specified' });
    } else {
        flags.push({ type: 'green', text: '🔒 Vesting: ' + data.vesting });
    }

    if (data.allocation) {
        const team = data.allocation['Team'] || data.allocation['team'] || 0;
        const investors = data.allocation['Investors'] || data.allocation['investors'] || 0;
        const community = data.allocation['Community'] || data.allocation['community'] || 0;

        if (team > 25) {
            flags.push({ type: 'red', text: '⚠ Team allocation > 25% — high concentration risk' });
        } else if (team > 0) {
            flags.push({ type: 'green', text: '✅ Team allocation looks reasonable' });
        }

        if (investors > community && community > 0) {
            flags.push({ type: 'yellow', text: '⚡ Investors > Community — watch unlock schedule' });
        }
    }

    if (flags.length === 0) {
        flags.push({ type: 'yellow', text: '⚡ No allocation data found in this document' });
    }

    flags.forEach((flag, i) => {
        const el = document.createElement('div');
        el.className = 'flag ' + flag.type;
        el.textContent = flag.text;
        el.style.animationDelay = (i * 0.1) + 's';
        container.appendChild(el);
    });
}
