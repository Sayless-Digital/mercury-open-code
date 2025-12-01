"""
Modern Design System - Reference for creating amazing UI/UX.
Provides templates, patterns, and best practices for modern, clean design.
"""

from typing import Dict, List, Any


class ModernDesignSystem:
    """
    Modern design system with best practices, patterns, and templates.
    
    Ensures every UI component follows:
    - Modern visual design (gradients, shadows, animations)
    - Clean, minimal aesthetic
    - Responsive design
    - Accessibility
    - Professional polish
    """
    
    # Modern color palettes
    COLOR_PALETTES = {
        "modern_blue": {
            "primary": "#3b82f6",
            "secondary": "#1e40af",
            "accent": "#60a5fa",
            "background": "#f8fafc",
            "text": "#1e293b",
            "text_light": "#64748b"
        },
        "modern_purple": {
            "primary": "#8b5cf6",
            "secondary": "#6d28d9",
            "accent": "#a78bfa",
            "background": "#faf5ff",
            "text": "#1e1b4b",
            "text_light": "#6b7280"
        },
        "modern_green": {
            "primary": "#10b981",
            "secondary": "#059669",
            "accent": "#34d399",
            "background": "#f0fdf4",
            "text": "#064e3b",
            "text_light": "#6b7280"
        }
    }
    
    # Modern typography
    TYPOGRAPHY = {
        "font_stack": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
        "heading_font": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        "monospace": "'Fira Code', 'Courier New', monospace",
        "sizes": {
            "xs": "0.75rem",
            "sm": "0.875rem",
            "base": "1rem",
            "lg": "1.125rem",
            "xl": "1.25rem",
            "2xl": "1.5rem",
            "3xl": "1.875rem",
            "4xl": "2.25rem",
            "5xl": "3rem"
        }
    }
    
    # Modern spacing system
    SPACING = {
        "xs": "0.25rem",   # 4px
        "sm": "0.5rem",    # 8px
        "md": "1rem",      # 16px
        "lg": "1.5rem",    # 24px
        "xl": "2rem",      # 32px
        "2xl": "3rem",     # 48px
        "3xl": "4rem",     # 64px
    }
    
    # Modern CSS patterns
    CSS_PATTERNS = {
        "gradient_background": """
background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
background-attachment: fixed;
""",
        "glass_morphism": """
background: rgba(255, 255, 255, 0.1);
backdrop-filter: blur(10px);
border: 1px solid rgba(255, 255, 255, 0.2);
border-radius: 16px;
""",
        "modern_shadow": """
box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 
            0 2px 4px -1px rgba(0, 0, 0, 0.06);
""",
        "hover_lift": """
transition: transform 0.2s ease, box-shadow 0.2s ease;
""",
        "hover_lift_active": """
transform: translateY(-2px);
box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 
            0 4px 6px -2px rgba(0, 0, 0, 0.05);
""",
        "smooth_transition": """
transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
""",
        "modern_button": """
display: inline-flex;
align-items: center;
justify-content: center;
padding: 0.75rem 1.5rem;
font-weight: 600;
border-radius: 0.5rem;
background: linear-gradient(135deg, var(--primary), var(--secondary));
color: white;
border: none;
cursor: pointer;
transition: all 0.3s ease;
box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
""",
        "modern_button_hover": """
transform: translateY(-2px);
box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
""",
        "hero_section": """
min-height: 100vh;
display: flex;
align-items: center;
justify-content: center;
background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
position: relative;
overflow: hidden;
""",
        "container": """
max-width: 1200px;
margin: 0 auto;
padding: 0 1.5rem;
width: 100%;
"""
    }
    
    # Landing page structure
    LANDING_PAGE_STRUCTURE = {
        "sections": [
            "hero",  # Hero section with headline
            "features",  # Key features
            "benefits",  # Benefits/why choose
            "testimonials",  # Social proof
            "cta",  # Call to action
            "footer"  # Footer
        ],
        "required_elements": [
            "navigation",
            "hero_headline",
            "hero_subheadline",
            "cta_button",
            "feature_cards",
            "responsive_design"
        ]
    }
    
    @classmethod
    def get_modern_css_template(cls) -> str:
        """Get modern CSS template with all best practices."""
        return """
/* Modern Design System - CSS Variables */
:root {
    --primary: #3b82f6;
    --secondary: #1e40af;
    --accent: #60a5fa;
    --background: #f8fafc;
    --text: #1e293b;
    --text-light: #64748b;
    --border-radius: 0.5rem;
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Modern Reset & Base Styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: var(--text);
    background: var(--background);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* Modern Typography */
h1, h2, h3, h4, h5, h6 {
    font-weight: 700;
    line-height: 1.2;
    color: var(--text);
}

/* Modern Buttons */
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.75rem 1.5rem;
    font-weight: 600;
    border-radius: var(--border-radius);
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    color: white;
    border: none;
    cursor: pointer;
    transition: var(--transition);
    box-shadow: var(--shadow-md);
}

.btn:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
}

/* Modern Cards */
.card {
    background: white;
    border-radius: var(--border-radius);
    padding: 1.5rem;
    box-shadow: var(--shadow-md);
    transition: var(--transition);
}

.card:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
}

/* Responsive Design */
@media (max-width: 768px) {
    .container {
        padding: 0 1rem;
    }
}
"""
    
    @classmethod
    def get_landing_page_html_template(cls) -> str:
        """Get modern landing page HTML template."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Modern Landing Page</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar">
        <div class="container">
            <div class="nav-content">
                <div class="logo">Logo</div>
                <ul class="nav-links">
                    <li><a href="#features">Features</a></li>
                    <li><a href="#benefits">Benefits</a></li>
                    <li><a href="#testimonials">Testimonials</a></li>
                    <li><a href="#cta" class="btn">Get Started</a></li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero">
        <div class="container">
            <div class="hero-content">
                <h1 class="hero-title">Amazing Product That Solves Your Problem</h1>
                <p class="hero-subtitle">The modern solution you've been waiting for</p>
                <div class="hero-cta">
                    <a href="#cta" class="btn btn-primary">Get Started</a>
                    <a href="#features" class="btn btn-secondary">Learn More</a>
                </div>
            </div>
        </div>
    </section>

    <!-- Features Section -->
    <section id="features" class="features">
        <div class="container">
            <h2 class="section-title">Key Features</h2>
            <div class="features-grid">
                <div class="feature-card card">
                    <div class="feature-icon">✨</div>
                    <h3>Feature One</h3>
                    <p>Description of amazing feature</p>
                </div>
                <div class="feature-card card">
                    <div class="feature-icon">🚀</div>
                    <h3>Feature Two</h3>
                    <p>Description of amazing feature</p>
                </div>
                <div class="feature-card card">
                    <div class="feature-icon">💎</div>
                    <h3>Feature Three</h3>
                    <p>Description of amazing feature</p>
                </div>
            </div>
        </div>
    </section>

    <!-- CTA Section -->
    <section id="cta" class="cta">
        <div class="container">
            <h2>Ready to Get Started?</h2>
            <p>Join thousands of satisfied customers</p>
            <a href="#" class="btn btn-primary">Start Now</a>
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <div class="container">
            <p>&copy; 2024 Company Name. All rights reserved.</p>
        </div>
    </footer>
</body>
</html>
"""
    
    @classmethod
    def get_design_guidelines(cls) -> Dict[str, Any]:
        """Get comprehensive design guidelines."""
        return {
            "principles": [
                "Modern visual design with gradients, shadows, and animations",
                "Clean, minimal aesthetic with plenty of white space",
                "Responsive design that works on all devices",
                "Accessible with semantic HTML and ARIA labels",
                "Professional polish with consistent spacing and typography",
                "Smooth transitions and micro-interactions",
                "Modern color palette (not plain white/black)",
                "Typography hierarchy with clear visual structure"
            ],
            "must_have": [
                "CSS gradients or modern backgrounds",
                "Box shadows or text shadows for depth",
                "Smooth transitions or animations",
                "Responsive design with media queries",
                "Modern layout (Flexbox or CSS Grid)",
                "CSS custom properties (variables)",
                "Consistent spacing system",
                "Typography scale"
            ],
            "avoid": [
                "Plain white backgrounds with black text",
                "Basic Arial or Times fonts",
                "Harsh black borders",
                "No spacing or cramped layouts",
                "No responsive design",
                "No visual hierarchy"
            ]
        }











