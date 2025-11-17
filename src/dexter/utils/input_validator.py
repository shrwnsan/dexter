"""
Input Validation Framework for Dexter Financial Research Agent

Prevents prompt injection attacks, resource exhaustion, and malicious input
through comprehensive input validation, sanitization, and length limits.
"""

import re
import logging
from typing import Optional, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class InputValidationResult(Enum):
    """Input validation result types"""
    VALID = "valid"
    INVALID_LENGTH = "invalid_length"
    INVALID_CHARACTERS = "invalid_characters"
    SUSPICIOUS_CONTENT = "suspicious_content"
    PROMPT_INJECTION = "prompt_injection"
    RESOURCE_EXHAUSTION = "resource_exhaustion"

class InputValidator:
    """Comprehensive input validation for financial research queries"""

    def __init__(self):
        # Define safe characters for financial queries
        self.safe_char_pattern = re.compile(r'^[a-zA-Z0-9\s\.,\?\!@#\$%\^&\*\(\)_\-\+=\{\}\[\]:;"\'<>/|\\`\~\n\r\t]+$')

        # Financial-specific allowlist patterns
        self.financial_patterns = [
            r'\b[A-Z]{1,5}\b',  # Stock symbols (1-5 letters)
            r'\$\d+(?:\.\d+)?',  # Dollar amounts
            r'\d{4}-\d{2}-\d{2}',  # Dates
            r'\b(?:stock|price|market|revenue|earnings|profit|loss|growth|analysis|research|report|financial)\b',
            r'\b(?:NASDAQ|NYSE|SP500|DOW|S&P)\b',
            r'\b(?:CEO|CFO|CTO|company|corporation|business)\b'
        ]

        # Prompt injection detection patterns
        self.injection_patterns = [
            r'(?i)(ignore|forget|disregard).*(previous|above|earlier).*(instruction|prompt|text)',
            r'(?i)(system|developer|admin).*(mode|access|override)',
            r'(?i)(execute|run|eval|interpret).*(code|script|command)',
            r'(?i)(new|different|change).*(role|persona|character)',
            r'(?i)(as|acting|pretend).*(ai|assistant|chatgpt|claude)',
            r'(?i)(tell|show|reveal).*(secret|hidden|internal)',
            r'(?i)(bypass|circumvent|avoid).*(security|filter|restriction)',
            r'\{\{.*?\}\}',  # Template injection
            r'<\|.*?\|>',   # Special token injection
            r'```[\s\S]*?```',  # Code block injection
        ]

        # Length limits
        self.max_query_length = 1000
        self.max_line_length = 200

        logger.info("Input validator initialized with comprehensive protection")

    def validate_length(self, query: str) -> Tuple[bool, Optional[str]]:
        """Validate query length"""
        if len(query) > self.max_query_length:
            return False, f"Query too long (max {self.max_query_length} characters)"

        # Check for extremely long lines (potential resource exhaustion)
        lines = query.split('\n')
        for i, line in enumerate(lines):
            if len(line) > self.max_line_length:
                return False, f"Line {i+1} too long (max {self.max_line_length} characters)"

        return True, None

    def validate_characters(self, query: str) -> Tuple[bool, Optional[str]]:
        """Validate allowed characters"""
        if not self.safe_char_pattern.match(query):
            # Find problematic characters
            problematic_chars = []
            for char in query:
                if not self.safe_char_pattern.match(char):
                    problematic_chars.append(char)

            unique_chars = set(problematic_chars)
            return False, f"Invalid characters detected: {list(unique_chars)[:5]}"

        return True, None

    def detect_prompt_injection(self, query: str) -> Tuple[bool, Optional[str]]:
        """Detect potential prompt injection attempts"""
        query_lower = query.lower()

        for pattern in self.injection_patterns:
            if re.search(pattern, query):
                return False, f"Potential prompt injection detected: pattern '{pattern}'"

        # Check for repetition attacks
        words = query_lower.split()
        if len(set(words)) < len(words) * 0.3:  # Less than 30% unique words
            return False, "Suspicious repetition detected"

        # Check for excessive special characters
        special_char_count = sum(1 for c in query if not c.isalnum() and not c.isspace())
        total_chars = len(query.replace(' ', ''))
        if total_chars > 0 and special_char_count / total_chars > 0.3:
            return False, "Excessive special characters detected"

        return True, None

    def validate_financial_content(self, query: str) -> Tuple[bool, Optional[str]]:
        """Validate content appears to be financial research related"""
        query_lower = query.lower()

        # Check if query contains financial terminology
        has_financial_content = any(re.search(pattern, query_lower, re.IGNORECASE) for pattern in self.financial_patterns)

        # Allow very short simple queries (e.g., "AAPL", "Tesla")
        if len(query.strip()) < 10:
            has_financial_content = True

        if not has_financial_content:
            logger.warning(f"Query may not be financial research related: '{query[:50]}...'")
            # Don't reject, but log for monitoring

        return True, None

    def validate_query(self, query: str) -> Tuple[InputValidationResult, Optional[str]]:
        """
        Comprehensive input validation

        Args:
            query: User input query to validate

        Returns:
            Tuple of (validation_result, error_message)
        """
        if not query or not query.strip():
            return InputValidationResult.VALID, None

        # Strip leading/trailing whitespace for validation
        clean_query = query.strip()

        # Length validation
        is_valid, error = self.validate_length(clean_query)
        if not is_valid:
            return InputValidationResult.INVALID_LENGTH, error

        # Character validation
        is_valid, error = self.validate_characters(clean_query)
        if not is_valid:
            return InputValidationResult.INVALID_CHARACTERS, error

        # Prompt injection detection
        is_valid, error = self.detect_prompt_injection(clean_query)
        if not is_valid:
            return InputValidationResult.PROMPT_INJECTION, error

        # Financial content validation
        is_valid, error = self.validate_financial_content(clean_query)
        if not is_valid:
            return InputValidationResult.SUSPICIOUS_CONTENT, error

        logger.info(f"Query validation passed: {len(clean_query)} characters")
        return InputValidationResult.VALID, None

    def sanitize_input(self, query: str) -> str:
        """
        Sanitize input by removing or replacing problematic content

        Args:
            query: Raw user input

        Returns:
            Sanitized input
        """
        if not query:
            return ""

        # Remove potential template injection
        sanitized = re.sub(r'\{\{.*?\}\}', '', query, flags=re.DOTALL)
        sanitized = re.sub(r'<\|.*?\|>', '', sanitized, flags=re.DOTALL)

        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()

        # Limit length
        if len(sanitized) > self.max_query_length:
            sanitized = sanitized[:self.max_query_length] + "..."
            logger.warning("Input truncated due to length limit")

        return sanitized

# Global validator instance
_input_validator = InputValidator()

def get_input_validator() -> InputValidator:
    """Get the global input validator instance"""
    return _input_validator

def validate_user_input(query: str) -> Tuple[bool, Optional[str]]:
    """
    Convenience function for input validation

    Args:
        query: User input query

    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = get_input_validator()
    result, error = validator.validate_query(query)

    if result == InputValidationResult.VALID:
        return True, None
    else:
        return False, error

def get_safe_user_input(unsafe_query: str) -> Tuple[str, Optional[str]]:
    """
    Get validated and sanitized user input

    Args:
        unsafe_query: Raw user input

    Returns:
        Tuple of (safe_query, error_message)
    """
    # First validate the input
    is_valid, error = validate_user_input(unsafe_query)
    if not is_valid:
        return "", error

    # Then sanitize it
    validator = get_input_validator()
    safe_query = validator.sanitize_input(unsafe_query)

    return safe_query, None