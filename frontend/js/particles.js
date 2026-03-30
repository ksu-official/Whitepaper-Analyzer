const canvas = document.getElementById('particle-canvas')

// Mobile: hide canvas and show static title
if (window.innerWidth < 600) {
    canvas.style.display = 'none'
    const title = document.createElement('h1')
    title.textContent = 'WHITEPAPER ANALYZER'
    title.style.cssText = `
        font-family: 'Orbitron', monospace;
        font-size: 1.8rem;
        font-weight: 900;
        color: #000000;
        text-align: center;
        letter-spacing: 2px;
        margin: 0;
    `
    canvas.parentNode.insertBefore(title, canvas)

} else {
    // Desktop: particle animation
    const ctx = canvas.getContext('2d')
    let mouse = { x: null, y: null, radius: 80 }

    // Mouse tracking
    window.addEventListener('mousemove', e => {
        const rect = canvas.getBoundingClientRect()
        mouse.x = e.clientX - rect.left
        mouse.y = e.clientY - rect.top
    })

    window.addEventListener('mouseleave', () => {
        mouse.x = null
        mouse.y = null
    })

    // Particle class
    class Particle {
        constructor(x, y) {
            this.baseX = x
            this.baseY = y
            this.x = Math.random() * canvas.width
            this.y = Math.random() * canvas.height
            this.size = 1.5
            this.density = Math.random() * 20 + 5
            this.settled = false
        }

        draw() {
            const dx = this.x - this.baseX
            const dy = this.y - this.baseY
            const distance = Math.sqrt(dx * dx + dy * dy)
            ctx.fillStyle = distance < 1.5 ? '#000000' : '#685E5B'
            ctx.beginPath()
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
            ctx.closePath()
            ctx.fill()
        }

        update() {
            // Mouse repulsion
            if (mouse.x !== null) {
                const dx = mouse.x - this.x
                const dy = mouse.y - this.y
                const distance = Math.sqrt(dx * dx + dy * dy)
                if (distance < mouse.radius) {
                    const force = (mouse.radius - distance) / mouse.radius
                    this.x -= dx * force * 0.15
                    this.y -= dy * force * 0.15
                }
            }

            // Return to base position
            const dx = this.baseX - this.x
            const dy = this.baseY - this.y
            this.x += dx * 0.08
            this.y += dy * 0.08
        }
    }

    let particles = []
    let animationId = null

    // Initialize particles from text mask
    function initParticles() {
        particles = []
        ctx.clearRect(0, 0, canvas.width, canvas.height)

        const fontSize = Math.max(18, Math.min(52, canvas.width * 0.054))
        ctx.fillStyle = '#000000'
        ctx.font = `900 ${fontSize}px Orbitron, monospace`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'alphabetic'
        ctx.fillText('WHITEPAPER ANALYZER', canvas.width / 2, canvas.height / 2)

        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
        ctx.clearRect(0, 0, canvas.width, canvas.height)

        const step = Math.max(2, canvas.width / 370)

        for (let y = 0; y < canvas.height; y += step) {
            for (let x = 0; x < canvas.width; x += step) {
                const index = (Math.floor(y) * canvas.width + Math.floor(x)) * 4
                if (imageData.data[index + 3] > 128) {
                    particles.push(new Particle(x, y))
                }
            }
        }
    }

    // Resize canvas and rebuild particles
    function resizeCanvas() {
        canvas.width = Math.min(960, window.innerWidth - 40)
        canvas.height = 100
        initParticles()
    }

    // Animation loop
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height)
        particles.forEach(p => {
            p.update()
            p.draw()
        })
        animationId = requestAnimationFrame(animate)
    }

    // Start animation after fonts load
    document.fonts.ready.then(() => {
        resizeCanvas()
        animate()
        window.addEventListener('resize', resizeCanvas)
    })
}
