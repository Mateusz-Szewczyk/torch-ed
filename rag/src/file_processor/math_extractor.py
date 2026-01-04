"""
Math Equation Extractor for PDF Documents.

Detects and extracts mathematical equations from text content.
Supports LaTeX notation, Unicode math symbols, and common equation patterns.

IMPORTANT: This extractor is CONSERVATIVE - it only extracts well-formed
mathematical expressions, NOT individual symbols or pseudocode/algorithm text.
"""

import re
import logging
from typing import List, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MathEquation:
    """Represents an extracted mathematical equation."""
    text: str  # Original text containing the equation
    latex: str  # LaTeX representation
    equation_type: str  # 'inline', 'block', 'formula'
    start_pos: int  # Start position in original text
    end_pos: int  # End position in original text
    confidence: float = 1.0


@dataclass
class MathExtractionResult:
    """Result of math extraction from a text segment."""
    has_math: bool
    equations: List[MathEquation] = field(default_factory=list)
    processed_text: str = ""  # Text with math markers for frontend
    math_blocks: List[Dict] = field(default_factory=list)  # Serializable format


# Patterns that indicate algorithm/pseudocode (should NOT be treated as math)
ALGORITHM_PATTERNS = [
    r'(?i)\bAlgorithm\s+\d+',
    r'(?i)\bRequire:',
    r'(?i)\bEnsure:',
    r'(?i)\bInput:',
    r'(?i)\bOutput:',
    r'(?i)\bfor\s+.*\s+do\b',
    r'(?i)\bwhile\s+.*\s+do\b',
    r'(?i)\bif\s+.*\s+then\b',
    r'(?i)\bend\s+(if|for|while|function)\b',
    r'(?i)\breturn\b',
    r'(?i)\bfunction\b',
    r'(?i)\bprocedure\b',
    r'⊲',  # Algorithm comment marker
    r'←',  # Assignment operator in algorithms
]


class MathExtractor:
    """
    Extracts and formats mathematical equations from text.

    Supports:
    - LaTeX inline ($...$, \\(...\\))
    - LaTeX display ($$...$$, \\[...\\], equation environments)
    - Unicode math symbols
    - Common mathematical patterns
    """

    # LaTeX patterns
    LATEX_INLINE_DOLLAR = r'\$([^$]+)\$'
    LATEX_INLINE_PAREN = r'\\\((.+?)\\\)'
    LATEX_DISPLAY_DOUBLE = r'\$\$(.+?)\$\$'
    LATEX_DISPLAY_BRACKET = r'\\\[(.+?)\\\]'
    LATEX_EQUATION_ENV = r'\\begin\{(equation|align|gather|multline)\*?\}(.+?)\\end\{\1\*?\}'

    # Unicode math symbols that indicate mathematical content
    MATH_SYMBOLS = {
        # Greek letters
        'α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ',
        'ν', 'ξ', 'ο', 'π', 'ρ', 'σ', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω',
        'Α', 'Β', 'Γ', 'Δ', 'Ε', 'Ζ', 'Η', 'Θ', 'Ι', 'Κ', 'Λ', 'Μ',
        'Ν', 'Ξ', 'Ο', 'Π', 'Ρ', 'Σ', 'Τ', 'Υ', 'Φ', 'Χ', 'Ψ', 'Ω',
        # Mathematical operators
        '∑', '∏', '∫', '∬', '∭', '∮', '∂', '∇', '√', '∛', '∜',
        '±', '∓', '×', '÷', '·', '∘', '⊗', '⊕', '⊖', '⊙',
        # Relations
        '≈', '≠', '≤', '≥', '≪', '≫', '∝', '∼', '≅', '≡', '≢',
        '⊂', '⊃', '⊆', '⊇', '∈', '∉', '∋', '∌',
        # Arrows
        '→', '←', '↔', '⇒', '⇐', '⇔', '↦', '⟶', '⟷',
        # Set notation
        '∅', '∪', '∩', '⊄', '⊅',
        # Logic
        '∀', '∃', '∄', '¬', '∧', '∨', '⊢', '⊨',
        # Miscellaneous
        '∞', '℘', 'ℵ', 'ℶ', 'ℕ', 'ℤ', 'ℚ', 'ℝ', 'ℂ',
        # Fractions and superscripts/subscripts
        '¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹', '⁰',
        '₀', '₁', '₂', '₃', '₄', '₅', '₆', '₇', '₈', '₉',
        'ⁿ', 'ⁱ', '½', '⅓', '¼', '⅕', '⅔', '¾', '⅖', '⅗',
    }

    # Patterns for common mathematical expressions (not in LaTeX)
    MATH_EXPRESSION_PATTERNS = [
        # Fractions like "a/b" where a and b are numbers or variables
        r'(?<![a-zA-Z])([a-zA-Z0-9]+)\s*/\s*([a-zA-Z0-9]+)(?![a-zA-Z])',
        # Exponents like "x^2", "x^n", "e^x"
        r'([a-zA-Z0-9]+)\s*\^\s*([a-zA-Z0-9{}\-\+]+)',
        # Subscripts like "x_i", "a_1"
        r'([a-zA-Z])\s*_\s*([a-zA-Z0-9{}\-\+]+)',
        # Functions with parentheses
        r'\b(sin|cos|tan|cot|sec|csc|log|ln|exp|lim|max|min|arg|det)\s*\(',
        # Summation/product notation
        r'∑|∏|Σ|Π',
        # Integral notation
        r'∫|∬|∭|∮',
        # Square root
        r'√\s*[(\[{]?[^)\]}]*[)\]}]?',
        # Limits
        r'lim\s*(_{[^}]+}|\s+as\s+)',
    ]

    # Symbol to LaTeX mapping
    SYMBOL_TO_LATEX = {
        'α': r'\alpha', 'β': r'\beta', 'γ': r'\gamma', 'δ': r'\delta',
        'ε': r'\epsilon', 'ζ': r'\zeta', 'η': r'\eta', 'θ': r'\theta',
        'ι': r'\iota', 'κ': r'\kappa', 'λ': r'\lambda', 'μ': r'\mu',
        'ν': r'\nu', 'ξ': r'\xi', 'π': r'\pi', 'ρ': r'\rho',
        'σ': r'\sigma', 'τ': r'\tau', 'υ': r'\upsilon', 'φ': r'\phi',
        'χ': r'\chi', 'ψ': r'\psi', 'ω': r'\omega',
        'Γ': r'\Gamma', 'Δ': r'\Delta', 'Θ': r'\Theta', 'Λ': r'\Lambda',
        'Ξ': r'\Xi', 'Π': r'\Pi', 'Σ': r'\Sigma', 'Υ': r'\Upsilon',
        'Φ': r'\Phi', 'Ψ': r'\Psi', 'Ω': r'\Omega',
        '∑': r'\sum', '∏': r'\prod', '∫': r'\int', '∬': r'\iint',
        '∭': r'\iiint', '∮': r'\oint', '∂': r'\partial', '∇': r'\nabla',
        '√': r'\sqrt', '±': r'\pm', '∓': r'\mp', '×': r'\times',
        '÷': r'\div', '·': r'\cdot', '∘': r'\circ',
        '≈': r'\approx', '≠': r'\neq', '≤': r'\leq', '≥': r'\geq',
        '≪': r'\ll', '≫': r'\gg', '∝': r'\propto', '∼': r'\sim',
        '≅': r'\cong', '≡': r'\equiv', '⊂': r'\subset', '⊃': r'\supset',
        '⊆': r'\subseteq', '⊇': r'\supseteq', '∈': r'\in', '∉': r'\notin',
        '→': r'\rightarrow', '←': r'\leftarrow', '↔': r'\leftrightarrow',
        '⇒': r'\Rightarrow', '⇐': r'\Leftarrow', '⇔': r'\Leftrightarrow',
        '∅': r'\emptyset', '∪': r'\cup', '∩': r'\cap',
        '∀': r'\forall', '∃': r'\exists', '¬': r'\neg',
        '∧': r'\land', '∨': r'\lor', '∞': r'\infty',
        'ℕ': r'\mathbb{N}', 'ℤ': r'\mathbb{Z}', 'ℚ': r'\mathbb{Q}',
        'ℝ': r'\mathbb{R}', 'ℂ': r'\mathbb{C}',
    }

    # Superscript/subscript mapping
    SUPERSCRIPT_MAP = {
        '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
        '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
        'ⁿ': 'n', 'ⁱ': 'i',
    }
    SUBSCRIPT_MAP = {
        '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4',
        '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9',
    }

    def __init__(self, min_math_density: float = 0.15):
        """
        Initialize the math extractor.

        Args:
            min_math_density: Minimum ratio of math symbols to text length
                             for a segment to be considered mathematical
                             (increased to 0.15 to be more conservative)
        """
        self.min_math_density = min_math_density
        self._compile_patterns()
        self.algorithm_patterns = [re.compile(p) for p in ALGORITHM_PATTERNS]

    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        self.latex_patterns = [
            (re.compile(self.LATEX_DISPLAY_DOUBLE, re.DOTALL), 'block'),
            (re.compile(self.LATEX_DISPLAY_BRACKET, re.DOTALL), 'block'),
            (re.compile(self.LATEX_EQUATION_ENV, re.DOTALL), 'block'),
            (re.compile(self.LATEX_INLINE_DOLLAR), 'inline'),
            (re.compile(self.LATEX_INLINE_PAREN), 'inline'),
        ]
        self.expression_patterns = [
            re.compile(p) for p in self.MATH_EXPRESSION_PATTERNS
        ]

    def _is_algorithm_text(self, text: str) -> bool:
        """
        Check if text appears to be algorithm/pseudocode.

        Algorithm text should NOT be processed for math extraction
        as it will break the formatting.
        """
        for pattern in self.algorithm_patterns:
            if pattern.search(text):
                return True

        # Check for numbered lines like "1:", "2:", etc. (algorithm steps)
        if re.search(r'^\d+:\s+', text, re.MULTILINE):
            return True

        # Check for high density of assignment arrows
        arrow_count = text.count('←') + text.count('⟵')
        if arrow_count >= 2:
            return True

        return False

    def has_math_content(self, text: str) -> bool:
        """
        Quick check if text contains mathematical content.

        CONSERVATIVE: Returns False for algorithm/pseudocode text.
        Only returns True for explicit LaTeX or significant math symbols.

        Args:
            text: Text to check

        Returns:
            True if text likely contains math content
        """
        if not text:
            return False

        # Skip algorithm/pseudocode text
        if self._is_algorithm_text(text):
            return False

        # Check for LaTeX delimiters (explicit math)
        latex_indicators = ['$', '\\(', '\\)', '\\[', '\\]', '\\begin{']
        if any(ind in text for ind in latex_indicators):
            return True

        # For Unicode symbols, be VERY conservative
        # Only return True for EXPLICIT mathematical expressions
        # (like standalone equations, not symbols in regular text)

        # Check for explicit equation patterns: variable = expression
        if re.search(r'[A-Za-z]\s*=\s*[^=]', text):
            # Must also have math symbols
            math_symbol_count = sum(1 for char in text if char in self.MATH_SYMBOLS)
            if math_symbol_count >= 1:
                return True

        return False

    def extract_equations(self, text: str) -> MathExtractionResult:
        """
        Extract all mathematical equations from text.

        CONSERVATIVE: Does NOT process algorithm/pseudocode text.
        Only extracts well-formed mathematical expressions.

        Args:
            text: Text to extract equations from

        Returns:
            MathExtractionResult with extracted equations
        """
        # CRITICAL: Skip algorithm/pseudocode text entirely
        # These contain math symbols but should not be parsed as math
        if self._is_algorithm_text(text):
            logger.debug("[MathExtractor] Skipping algorithm/pseudocode text")
            return MathExtractionResult(
                has_math=False,
                equations=[],
                processed_text=text,
                math_blocks=[]
            )

        equations = []
        processed_text = text

        # Extract LaTeX equations first (highest confidence)
        for pattern, eq_type in self.latex_patterns:
            for match in pattern.finditer(text):
                if eq_type == 'block' and '\\begin' in pattern.pattern:
                    # Environment pattern - groups are different
                    env_name = match.group(1)
                    content = match.group(2)
                    latex = f"\\begin{{{env_name}}}{content}\\end{{{env_name}}}"
                else:
                    content = match.group(1)
                    latex = content

                equations.append(MathEquation(
                    text=match.group(0),
                    latex=latex,
                    equation_type=eq_type,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=1.0
                ))

        # Extract Unicode math expressions
        unicode_equations = self._extract_unicode_math(text)
        equations.extend(unicode_equations)

        # Extract expression-based math (x^2, log(x), etc.)
        expression_equations = self._extract_expression_math(text)
        equations.extend(expression_equations)

        # Deduplicate equations by position
        equations = self._deduplicate_equations(equations)

        # Sort by position
        equations.sort(key=lambda e: e.start_pos)

        has_math = len(equations) > 0 or self.has_math_content(text)

        # Create math blocks for serialization
        math_blocks = []
        for eq in equations:
            math_blocks.append({
                'text': eq.text,
                'latex': eq.latex,
                'type': eq.equation_type,
                'start': eq.start_pos,
                'end': eq.end_pos,
                'confidence': eq.confidence,
            })

        if has_math:
            logger.debug(f"[MathExtractor] Found {len(equations)} equations in text (len={len(text)})")

        # Process text to add math markers
        processed_text = self._add_math_markers(text, equations)

        return MathExtractionResult(
            has_math=has_math,
            equations=equations,
            processed_text=processed_text,
            math_blocks=math_blocks
        )

    def _extract_unicode_math(self, text: str) -> List[MathEquation]:
        """
        Extract mathematical content using Unicode symbols.

        CONSERVATIVE: Only extracts COMPLETE mathematical expressions,
        not individual symbols scattered in regular text.
        """
        equations = []

        # Only extract well-formed mathematical expressions
        # Pattern for equation-like structures: variable = expression with math symbols
        # E.g., "E = mc²" or "a² + b² = c²"
        equation_pattern = re.compile(
            r'([A-Za-z][A-Za-z0-9₀-₉⁰-⁹]*)\s*[=≈≡≠<>≤≥]\s*([^,.\n]+(?:[+\-×÷·∓±][^,.\n]+)*)',
            re.UNICODE
        )

        for match in equation_pattern.finditer(text):
            expr = match.group(0)
            # Must contain at least one math operator or symbol
            math_count = sum(1 for c in expr if c in self.MATH_SYMBOLS or c in '=+-×÷')
            if math_count >= 1:
                latex = self._convert_to_latex(expr)
                equations.append(MathEquation(
                    text=expr,
                    latex=latex,
                    equation_type='inline',
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.7
                ))

        # Pattern for summation/integral expressions
        sum_int_pattern = re.compile(r'[∑∏∫∬∭∮][^\s,.\n]{2,}', re.UNICODE)
        for match in sum_int_pattern.finditer(text):
            expr = match.group(0)
            latex = self._convert_to_latex(expr)
            equations.append(MathEquation(
                text=expr,
                latex=latex,
                equation_type='inline',
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.85
            ))

        return equations

    def _extract_expression_math(self, text: str) -> List[MathEquation]:
        """Extract mathematical expressions based on regex patterns."""
        equations = []

        # Patterns for common math expressions
        expression_patterns = [
            # Exponents: x^2, e^x, 2^n
            (r'(?<![a-zA-Z])([a-zA-Z0-9]+)\^(\{[^}]+\}|[a-zA-Z0-9]+)', r'\1^{\2}', 0.85),
            # Subscripts: x_i, a_1
            (r'([a-zA-Z])_(\{[^}]+\}|[a-zA-Z0-9]+)', r'\1_{\2}', 0.85),
            # Functions: sin(x), log(x), exp(x)
            (r'\b(sin|cos|tan|cot|sec|csc|log|ln|exp|sqrt|min|max|arg|det)\s*\(([^)]+)\)', r'\\operatorname{\1}(\2)', 0.9),
            # Fractions written as a/b (but not file paths)
            (r'(?<![/\w])(\d+)/(\d+)(?![/\w])', r'\\frac{\1}{\2}', 0.75),
            # Simple equations: E = mc^2, a = b + c
            (r'([A-Z])\s*=\s*([a-zA-Z0-9\^\+\-\*/ ]+)', r'\1 = \2', 0.7),
        ]

        for pattern_str, latex_template, confidence in expression_patterns:
            pattern = re.compile(pattern_str)
            for match in pattern.finditer(text):
                expr_text = match.group(0)

                # Convert to LaTeX based on template
                if callable(latex_template):
                    latex = latex_template(match)
                else:
                    latex = match.expand(latex_template)

                # Clean up LaTeX
                latex = self._convert_to_latex(latex)

                equations.append(MathEquation(
                    text=expr_text,
                    latex=latex,
                    equation_type='inline',
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=confidence
                ))

        return equations


    def _convert_to_latex(self, expression: str) -> str:
        """Convert a mathematical expression to LaTeX format."""
        latex = expression

        # Replace Unicode symbols with LaTeX commands
        for symbol, latex_cmd in self.SYMBOL_TO_LATEX.items():
            latex = latex.replace(symbol, latex_cmd + ' ')

        # Handle superscripts
        result = []
        i = 0
        while i < len(latex):
            if latex[i] in self.SUPERSCRIPT_MAP:
                # Collect consecutive superscripts
                sup_chars = []
                while i < len(latex) and latex[i] in self.SUPERSCRIPT_MAP:
                    sup_chars.append(self.SUPERSCRIPT_MAP[latex[i]])
                    i += 1
                result.append('^{' + ''.join(sup_chars) + '}')
            elif latex[i] in self.SUBSCRIPT_MAP:
                # Collect consecutive subscripts
                sub_chars = []
                while i < len(latex) and latex[i] in self.SUBSCRIPT_MAP:
                    sub_chars.append(self.SUBSCRIPT_MAP[latex[i]])
                    i += 1
                result.append('_{' + ''.join(sub_chars) + '}')
            else:
                result.append(latex[i])
                i += 1

        return ''.join(result).strip()

    def _deduplicate_equations(self, equations: List[MathEquation]) -> List[MathEquation]:
        """Remove overlapping equations, keeping higher confidence ones."""
        if not equations:
            return []

        # Sort by start position, then by length (longer first)
        sorted_eqs = sorted(equations, key=lambda e: (e.start_pos, -(e.end_pos - e.start_pos)))

        result = []
        last_end = -1

        for eq in sorted_eqs:
            if eq.start_pos >= last_end:
                result.append(eq)
                last_end = eq.end_pos
            elif eq.confidence > 0.9:  # High confidence equation overrides
                # Check if it's significantly different
                if eq.end_pos > last_end + 5:
                    result.append(eq)
                    last_end = eq.end_pos

        return result

    def _add_math_markers(self, text: str, equations: List[MathEquation]) -> str:
        """
        Add markers to text for frontend rendering.

        Uses special markers that the frontend can recognize:
        - [MATH_INLINE]{latex}[/MATH_INLINE] for inline math
        - [MATH_BLOCK]{latex}[/MATH_BLOCK] for block/display math
        """
        if not equations:
            return text

        # Process in reverse order to preserve positions
        result = text
        for eq in reversed(equations):
            marker_type = 'MATH_BLOCK' if eq.equation_type == 'block' else 'MATH_INLINE'
            replacement = f'[{marker_type}]{eq.latex}[/{marker_type}]'
            result = result[:eq.start_pos] + replacement + result[eq.end_pos:]

        return result


def extract_math_from_text(text: str) -> Dict:
    """
    Convenience function to extract math from text.

    Args:
        text: Text to process

    Returns:
        Dictionary with extraction results
    """
    extractor = MathExtractor()
    result = extractor.extract_equations(text)

    return {
        'has_math': result.has_math,
        'math_blocks': result.math_blocks,
        'processed_text': result.processed_text,
    }


def check_math_content(text: str) -> bool:
    """
    Quick check if text contains math content.

    Args:
        text: Text to check

    Returns:
        True if text likely contains math
    """
    extractor = MathExtractor()
    return extractor.has_math_content(text)

