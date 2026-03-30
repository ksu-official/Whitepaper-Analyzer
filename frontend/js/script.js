pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js'

// File input label update
const fileInput = document.getElementById('file-input')
const fileLabel = document.getElementById('file-label')

fileInput.addEventListener('change', function() {
    if (fileInput.files[0]) {
        fileLabel.innerHTML = `<svg width="18" height="18" viewBox="0 0 18 18" style="vertical-align:middle; margin-right:8px;">
  <polyline points="3,9 7,13 15,5" fill="none" stroke="#515578" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>` + fileInput.files[0].name
        fileLabel.classList.add('has-file')
    }
})


// Error handlers
function showError(message) {
    const box = document.getElementById('errorBox')
    box.textContent = message
    box.classList.remove('hidden')
}

function hideError() {
    const box = document.getElementById('errorBox')
    box.classList.add('hidden')
}


// Analyze button handler
document.getElementById('analyze-btn').addEventListener('click', async function() {
    const url = document.getElementById('url-input').value.trim()
    const file = fileInput.files[0]

    if (!url && !file) {
        showError('Please paste a URL or upload a PDF!')
        return
    } else {
        hideError()
    }

    if (file) {
        await sendToBackend(file, null)
    } else {
        await sendToBackend(null, url)
    }
})


// Send data to backend
async function sendToBackend(file, url) {
    showLoading()

    try {
        const formData = new FormData()
        if (file) {
            formData.append('pdf', file)
        } else {
            formData.append('url', url)
        }

        const response = await fetch('https://api.ksuverse.online:8443/analyze', {
            method: 'POST',
            body: formData
        })

        const data = await response.json()
        renderDashboard(data)

    } catch (error) {
        alert('Error connecting to backend. Is Flask running?')
        console.error(error)
    }
}


// Show loading placeholders
function showLoading() {
    const results = document.getElementById('results')
    results.style.display = 'block'
    document.getElementById('r-supply').textContent = '...'
    document.getElementById('r-pages').textContent = '...'
    document.getElementById('r-vesting').textContent = '...'
    document.getElementById('r-risk').textContent = '...'
}


// Render full dashboard
function renderDashboard(data) {
    const results = document.getElementById('results')
    results.style.display = 'block'

    document.getElementById('r-supply').textContent = data.total_supply || 'N/A'
    document.getElementById('r-pages').textContent = data.pages

    const vestingEl = document.getElementById('r-vesting')
if (data.vesting && data.vesting !== 'mentioned') {
    vestingEl.textContent = '🔒 ' + data.vesting
    vestingEl.style.color = 'var(--accent5)'
} else if (data.vesting === 'mentioned') {
    vestingEl.textContent = '📋 Mentioned'
    vestingEl.style.color = '#ffc800'
} else {
    vestingEl.textContent = '⚡ Not found'
    vestingEl.style.color = 'var(--accent2)'
}

    const riskScore = calculateRisk(data)
    const riskEl = document.getElementById('r-risk')
    riskEl.textContent = riskScore + '/10'
    riskEl.style.color = riskScore > 6 ? 'var(--accent2)' : riskScore > 3 ? '#ffc800' : 'var(--accent5)'

    renderChart(data.allocation)
    renderFlags(data)

    if (data.summary) {
        document.getElementById('r-summary').textContent = data.summary
    }
}


// Calculate risk score
function calculateRisk(data) {
    let score = 0

    if (!data.vesting) score += 3

    if (data.allocation) {
        const team = data.allocation['Team'] || data.allocation['team'] || 0
        const investors = data.allocation['Investors'] || data.allocation['investors'] || 0
        const community = data.allocation['Community'] || data.allocation['community'] || 0

        if (team > 25) score += 2
        if (investors > community) score += 2
        if (investors > 20) score += 1
    }

    return Math.min(score, 10)
}


// Render allocation chart
let chartInstance = null

function renderChart(allocation) {
    if (!allocation || Object.keys(allocation).length === 0) {
        document.getElementById('chart-allocation').style.display = 'none'
        return
    }

    if (chartInstance) {
        chartInstance.destroy()
    }

    const labels = Object.keys(allocation)
    const values = Object.values(allocation)

    const colors = [
        '#00ff9d', '#ff2d6b', '#7b5ea7', '#00cfff',
        '#ffc800', '#ff6b35', '#4ecdc4', '#a8e6cf'
    ]

    const ctx = document.getElementById('chart-allocation').getContext('2d')

    chartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderColor: '#080810',
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#e0e0ff',
                        font: { family: 'Share Tech Mono', size: 11 },
                        padding: 16
                    }
                }
            }
        }
    })
}


// Render risk flags
function renderFlags(data) {
    const container = document.getElementById('r-flags')
    container.innerHTML = ''

    const flags = []

    if (!data.vesting) {
    flags.push({ type: 'yellow', text: '⚡ No vesting found — tokens unlock at TGE' })
} else if (data.vesting === 'mentioned') {
    flags.push({ type: 'yellow', text: '📋 Vesting mentioned but period not specified' })
} else {
    flags.push({ type: 'green', text: '🔒 Vesting: ' + data.vesting + ' — check unlock schedule before aping' })
}

    if (data.allocation) {
        const team = data.allocation['Team'] || data.allocation['team'] || 0
        const investors = data.allocation['Investors'] || data.allocation['investors'] || 0
        const community = data.allocation['Community'] || data.allocation['community'] || 0

        if (team > 25) {
            flags.push({ type: 'red', text: '⚠ Team allocation > 25% — high concentration risk' })
        } else if (team > 0) {
            flags.push({ type: 'green', text: '✅ Team allocation looks reasonable' })
        }

        if (investors > community && community > 0) {
            flags.push({ type: 'yellow', text: '⚡ Investors > Community — watch unlock schedule' })
        }
    }

    if (flags.length === 0) {
        flags.push({ type: 'yellow', text: '⚡ No allocation data found in this document' })
    }

    flags.forEach((flag, i) => {
        const el = document.createElement('div')
        el.className = 'flag ' + flag.type
        el.textContent = flag.text
        el.style.animationDelay = (i * 0.1) + 's'
        container.appendChild(el)
    })
}
