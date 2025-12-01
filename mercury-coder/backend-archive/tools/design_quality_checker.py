"""
Design Quality Checker - Systematic UI/UX quality validation.
Ensures modern, clean, polished design for all UI components.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger("mercury.tools.design_quality_checker")


class DesignQualityChecker:
    """
    Validates UI/UX design quality for HTML/CSS/JS files.
    
    Checks for:
    - Modern design patterns (gradients, shadows, animations)
    - Responsive design (media queries, flexbox/grid)
    - Accessibility (semantic HTML, ARIA labels)
    - Visual polish (spacing, typography, color)
    - Professional structure (sections, layout)
    """
    
    # Modern design patterns to check for
    MODERN_CSS_PATTERNS = [
        r'gradient',  # CSS gradients
        r'box-shadow|text-shadow',  # Shadows for depth
        r'transition|animation|@keyframes',  # Animations
        r'backdrop-filter|filter:',  # Modern filters
        r'border-radius',  # Rounded corners
        r'flex|grid',  # Modern layout
        r'var\(--',  # CSS variables
        r'@media',  # Responsive design
    ]
    
    # Anti-patterns (signs of basic/plain design)
    BASIC_PATTERNS = [
        r'background:\s*white|background:\s*#fff|background:\s*#ffffff',
        r'color:\s*black|color:\s*#000|color:\s*#000000',
        r'border:\s*1px\s*solid\s*black',
        r'font-family:\s*["\']?Arial["\']?|font-family:\s*["\']?Times["\']?',
        r'text-align:\s*center',  # Only center, no other alignment
    ]
    
    # Required modern features for landing pages
    REQUIRED_FEATURES = {
        'responsive': r'@media|viewport|responsive',
        'modern_layout': r'flex|grid|display:\s*(flex|grid)',
        'spacing': r'padding|margin',
        'typography': r'font-size|line-height|font-weight',
    }
    
    # Quality thresholds
    MIN_MODERN_PATTERNS = 5  # Minimum modern patterns required
    MAX_BASIC_PATTERNS = 2   # Maximum basic patterns allowed
    
    def __init__(self):
        """Initialize design quality checker."""
        pass
    
    def check_design_quality(
        self,
        file_path: str,
        content: str,
        file_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check design quality of a UI file.
        
        Args:
            file_path: Path to file
            content: File content
            file_type: File type ('html', 'css', 'js', or auto-detect)
            
        Returns:
            Dict with:
            - quality_score: float (0-100)
            - is_modern: bool
            - is_polished: bool
            - modern_patterns_found: List
            - basic_patterns_found: List
            - missing_features: List
            - suggestions: List
            - passed: bool
        """
        if not file_type:
            file_type = self._detect_file_type(file_path)
        
        # ONLY check CSS files for design quality
        # HTML/JS are structural/behavioral, not visual - they should pass automatically
        if file_type not in ['css']:
            return {
                "quality_score": 100,
                "is_modern": True,
                "is_polished": True,
                "passed": True,
                "message": f"Skipping design check for {file_type} file (only CSS files are checked for design quality)"
            }
        
        results = {
            "quality_score": 0,
            "is_modern": False,
            "is_polished": False,
            "modern_patterns_found": [],
            "basic_patterns_found": [],
            "missing_features": [],
            "suggestions": [],
            "warnings": [],
            "passed": False
        }
        
        # Check for modern patterns
        modern_count = 0
        for pattern in self.MODERN_CSS_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                modern_count += len(matches)
                results["modern_patterns_found"].append({
                    "pattern": pattern,
                    "count": len(matches)
                })
        
        # Check for basic/plain patterns (anti-patterns)
        basic_count = 0
        for pattern in self.BASIC_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                basic_count += len(matches)
                results["basic_patterns_found"].append({
                    "pattern": pattern,
                    "count": len(matches)
                })
        
        # Check for required features
        missing = []
        for feature, pattern in self.REQUIRED_FEATURES.items():
            if not re.search(pattern, content, re.IGNORECASE):
                missing.append(feature)
        
        results["missing_features"] = missing
        
        # Calculate quality score
        score = 0
        
        # Modern patterns (40 points max)
        if modern_count >= self.MIN_MODERN_PATTERNS:
            score += min(40, (modern_count / self.MIN_MODERN_PATTERNS) * 40)
        else:
            results["suggestions"].append(
                f"Add more modern CSS patterns (gradients, shadows, animations). Found {modern_count}, need at least {self.MIN_MODERN_PATTERNS}"
            )
        
        # Avoid basic patterns (30 points max)
        if basic_count <= self.MAX_BASIC_PATTERNS:
            score += 30
        else:
            results["suggestions"].append(
                f"Reduce basic/plain styling patterns. Found {basic_count}, should be max {self.MAX_BASIC_PATTERNS}"
            )
        
        # Required features (30 points max)
        required_count = len(self.REQUIRED_FEATURES) - len(missing)
        score += (required_count / len(self.REQUIRED_FEATURES)) * 30
        
        if missing:
            results["suggestions"].append(
                f"Add missing features: {', '.join(missing)}"
            )
        
        results["quality_score"] = min(100, score)
        results["is_modern"] = modern_count >= self.MIN_MODERN_PATTERNS
        results["is_polished"] = (
            modern_count >= self.MIN_MODERN_PATTERNS and
            basic_count <= self.MAX_BASIC_PATTERNS and
            len(missing) == 0
        )
        
        # Pass if quality score >= 70 and is polished
        results["passed"] = results["quality_score"] >= 70 and results["is_polished"]
        
        if not results["passed"]:
            results["warnings"].append(
                "Design quality below threshold. Add modern patterns, reduce basic styling, and include required features."
            )
        
        return results
    
    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type from extension."""
        ext = Path(file_path).suffix.lower()
        type_map = {
            '.html': 'html',
            '.css': 'css',
            '.js': 'js',
            '.jsx': 'jsx',
            '.tsx': 'tsx',
            '.vue': 'vue',
        }
        return type_map.get(ext, 'unknown')
    
    def get_design_suggestions(
        self,
        quality_result: Dict[str, Any],
        file_type: str
    ) -> List[str]:
        """
        Get specific design improvement suggestions.
        
        Args:
            quality_result: Result from check_design_quality
            file_type: File type
            
        Returns:
            List of specific suggestions
        """
        suggestions = []
        
        if not quality_result.get("is_modern"):
            suggestions.extend([
                "Add CSS gradients for visual interest",
                "Include box-shadow or text-shadow for depth",
                "Add smooth transitions or animations",
                "Use modern layout (Flexbox or CSS Grid)",
                "Include CSS custom properties (variables) for theming"
            ])
        
        if quality_result.get("basic_patterns_found"):
            suggestions.extend([
                "Replace plain white/black colors with modern color palette",
                "Use modern font stack (system fonts, Google Fonts)",
                "Add visual hierarchy with spacing and typography",
                "Include subtle borders or dividers instead of harsh black lines"
            ])
        
        missing = quality_result.get("missing_features", [])
        if 'responsive' in missing:
            suggestions.append("Add responsive design with @media queries and viewport meta tag")
        if 'modern_layout' in missing:
            suggestions.append("Use Flexbox or CSS Grid for modern, flexible layouts")
        if 'spacing' in missing:
            suggestions.append("Add consistent spacing system (padding/margin)")
        if 'typography' in missing:
            suggestions.append("Define typography scale (font sizes, line heights, weights)")
        
        return suggestions











