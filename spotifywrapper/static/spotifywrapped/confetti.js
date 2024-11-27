
class Confetti {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext("2d");
        this.particles = [];
        this.colors = ["#ff00ff", "#00ffff", "#ffff00", "#ff00ff"];
        this.shapes = ["circle", "square", "triangle"];
        this.width = this.canvas.width = window.innerWidth;
        this.height = this.canvas.height = window.innerHeight;

        // Resize canvas on window resize
        window.addEventListener("resize", () => {
            this.width = this.canvas.width = window.innerWidth;
            this.height = this.canvas.height = window.innerHeight;
        });
    }

    // Generate particles
    createParticles() {
        for (let i = 0; i < 100; i++) {
            const shape = this.shapes[Math.floor(Math.random() * this.shapes.length)];
            this.particles.push({
                x: Math.random() * this.width,
                y: Math.random() * this.height - this.height,
                size: Math.random() * 10 + 5,
                color: this.colors[Math.floor(Math.random() * this.colors.length)],
                shape: shape,
                velocityX: Math.random() * 4 - 2,
                velocityY: Math.random() * 3 + 2,
                rotation: Math.random() * 360,
            });
        }
    }

    // Draw particles
    drawParticles() {
        this.ctx.clearRect(0, 0, this.width, this.height);
        this.particles.forEach((particle, index) => {
            this.ctx.fillStyle = particle.color;

            this.ctx.save();
            this.ctx.translate(particle.x, particle.y);
            this.ctx.rotate((particle.rotation * Math.PI) / 180);

            if (particle.shape === "circle") {
                this.ctx.beginPath();
                this.ctx.arc(0, 0, particle.size / 2, 0, Math.PI * 2);
                this.ctx.fill();
            } else if (particle.shape === "square") {
                this.ctx.fillRect(-particle.size / 2, -particle.size / 2, particle.size, particle.size);
            } else if (particle.shape === "triangle") {
                this.ctx.beginPath();
                this.ctx.moveTo(0, -particle.size / 2);
                this.ctx.lineTo(particle.size / 2, particle.size / 2);
                this.ctx.lineTo(-particle.size / 2, particle.size / 2);
                this.ctx.closePath();
                this.ctx.fill();
            }

            this.ctx.restore();

            // Update particle position
            particle.x += particle.velocityX;
            particle.y += particle.velocityY;
            particle.rotation += particle.velocityX * 2;

            // Remove particles out of bounds
            if (particle.y > this.height || particle.x < 0 || particle.x > this.width) {
                this.particles.splice(index, 1);
            }
        });
    }

    // Animation loop
    animate() {
        if (this.particles.length > 0) {
            this.drawParticles();
            requestAnimationFrame(() => this.animate());
        }
    }

    // Start confetti
    start() {
        this.createParticles();
        this.animate();
    }
}

// Trigger confetti on card click
function triggerConfetti() {
    const confetti = new Confetti("confetti");
    confetti.start();
}