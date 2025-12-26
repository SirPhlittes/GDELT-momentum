"""
GDELT v4.0 Validation Utilities
================================
Input validation functions for the GDELT framework.

Author: Philip Hendrik Littau
Version: 4.0.0
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Tuple, List, Optional


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_date_range(
    start_date: datetime,
    end_date: datetime,
    max_days: int = 365,
) -> Tuple[datetime, datetime]:
    """
    Validate a date range for GDELT queries.
    
    Args:
        start_date: The start of the date range.
        end_date: The end of the date range.
        max_days: Maximum allowed days in range (default: 365).
        
    Returns:
        Tuple of validated (start_date, end_date).
        
    Raises:
        ValidationError: If the date range is invalid.
    """
    if start_date > end_date:
        raise ValidationError(
            f"start_date ({start_date}) must be before or equal to end_date ({end_date})"
        )
    
    days_diff = (end_date - start_date).days
    if days_diff > max_days:
        raise ValidationError(
            f"Date range of {days_diff} days exceeds maximum of {max_days} days"
        )
    
    # Ensure dates are not in the future
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if end_date > today:
        end_date = today - timedelta(days=1)
        if start_date > end_date:
            start_date = end_date
    
    return start_date, end_date


def validate_sample_percent(sample_percent: Optional[int]) -> Optional[int]:
    """
    Validate the sampling percentage.
    
    Args:
        sample_percent: The sampling percentage (1-100) or None.
        
    Returns:
        Validated sample_percent.
        
    Raises:
        ValidationError: If sample_percent is out of range.
    """
    if sample_percent is None:
        return None
    
    if not isinstance(sample_percent, int):
        try:
            sample_percent = int(sample_percent)
        except (ValueError, TypeError):
            raise ValidationError(
                f"sample_percent must be an integer, got {type(sample_percent).__name__}"
            )
    
    if not 1 <= sample_percent <= 100:
        raise ValidationError(
            f"sample_percent must be between 1 and 100, got {sample_percent}"
        )
    
    return sample_percent


def validate_boolean_expression(expression: str) -> str:
    """
    Validate a Boolean query expression.
    
    Args:
        expression: The Boolean expression to validate.
        
    Returns:
        Validated and normalized expression.
        
    Raises:
        ValidationError: If the expression is invalid.
    """
    if not expression or not expression.strip():
        raise ValidationError("Boolean expression cannot be empty")
    
    expression = expression.strip()
    
    # Check for balanced parentheses
    paren_count = 0
    for char in expression:
        if char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1
        if paren_count < 0:
            raise ValidationError("Unbalanced parentheses in expression")
    
    if paren_count != 0:
        raise ValidationError("Unbalanced parentheses in expression")
    
    # Check for empty parentheses
    if "()" in expression:
        raise ValidationError("Empty parentheses in expression")
    
    return expression


def validate_experiment_label(label: str) -> str:
    """
    Validate an experiment label.
    
    Args:
        label: The experiment label to validate.
        
    Returns:
        Validated label.
        
    Raises:
        ValidationError: If the label is invalid.
    """
    if not label or not label.strip():
        raise ValidationError("Experiment label cannot be empty")
    
    label = label.strip()
    
    # Check for maximum length
    if len(label) > 100:
        raise ValidationError(
            f"Experiment label too long ({len(label)} chars), maximum is 100"
        )
    
    return label


def validate_iso3_country_code(code: str) -> str:
    """
    Validate an ISO-3 country code.
    
    Args:
        code: The country code to validate.
        
    Returns:
        Uppercase validated code.
        
    Raises:
        ValidationError: If the code is invalid.
    """
    if not code:
        raise ValidationError("Country code cannot be empty")
    
    code = code.strip().upper()
    
    if len(code) != 3:
        raise ValidationError(
            f"ISO-3 country code must be 3 characters, got {len(code)}"
        )
    
    if not code.isalpha():
        raise ValidationError(
            f"ISO-3 country code must be alphabetic, got '{code}'"
        )
    
    return code


