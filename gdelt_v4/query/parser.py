"""
GDELT v4.0 Boolean Query Parser
================================
Unified Boolean expression parser that converts user queries to SQL conditions.

Supports:
- AND: All terms must match (multiple REGEXP_CONTAINS conditions)
- OR: Any term can match (single REGEXP_CONTAINS with alternation)
- NOT: Term must not match (NOT REGEXP_CONTAINS)
- Parentheses: Grouping of expressions
- Quoted phrases: Exact phrase matching

Author: Philip Hendrik Littau
Version: 4.0.0
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set
from enum import Enum

from gdelt_v4.utils.logging import get_logger
from gdelt_v4.utils.validators import validate_boolean_expression


logger = get_logger(__name__)


class TokenType(Enum):
    """Token types for Boolean expression parsing."""
    TERM = "TERM"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    QUOTE = "QUOTE"


@dataclass
class Token:
    """A single token in a Boolean expression."""
    type: TokenType
    value: str


@dataclass
class ParsedQuery:
    """
    Result of parsing a Boolean expression.
    
    Attributes:
        required_groups: Groups of terms where all must match (AND logic).
                        Each group is a list of OR-alternatives.
        excluded_terms: Terms that must not match (NOT logic).
        original: The original query string.
    """
    required_groups: List[List[str]] = field(default_factory=list)
    excluded_terms: List[str] = field(default_factory=list)
    original: str = ""
    
    def is_empty(self) -> bool:
        """Check if the parsed query is empty."""
        return not self.required_groups and not self.excluded_terms


class BooleanParser:
    """
    Parses Boolean expressions into structured query components.
    
    This parser fixes the AND operator issue from previous implementations
    by correctly separating AND conditions into multiple SQL WHERE clauses.
    
    Grammar:
        expression ::= and_expression
        and_expression ::= or_expression (AND or_expression)*
        or_expression ::= not_expression (OR not_expression)*
        not_expression ::= NOT? term
        term ::= WORD | QUOTED_STRING | '(' expression ')'
    
    Example:
        >>> parser = BooleanParser()
        >>> result = parser.parse("(CHINA OR RUSSIA) AND SANCTIONS NOT SPORT")
        >>> print(result.required_groups)
        [['CHINA', 'RUSSIA'], ['SANCTIONS']]
        >>> print(result.excluded_terms)
        ['SPORT']
    """
    
    # Regex patterns
    TOKEN_PATTERNS = [
        (r'\s+', None),  # Whitespace (skip)
        (r'\bAND\b', TokenType.AND),
        (r'\bOR\b', TokenType.OR),
        (r'\bNOT\b', TokenType.NOT),
        (r'\(', TokenType.LPAREN),
        (r'\)', TokenType.RPAREN),
        (r'"([^"]*)"', TokenType.QUOTE),  # Quoted string
        (r"'([^']*)'", TokenType.QUOTE),  # Single-quoted string
        (r'[^\s()"\']+', TokenType.TERM),  # Unquoted term
    ]
    
    def __init__(self):
        """Initialize the parser."""
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), token_type)
            for pattern, token_type in self.TOKEN_PATTERNS
        ]
    
    def parse(self, expression: str) -> ParsedQuery:
        """
        Parse a Boolean expression.
        
        Args:
            expression: The Boolean expression to parse.
            
        Returns:
            ParsedQuery with structured query components.
            
        Raises:
            ValueError: If the expression is invalid.
        """
        expression = validate_boolean_expression(expression)
        
        logger.debug(f"Parsing expression: {expression}")
        
        tokens = self._tokenize(expression)
        
        if not tokens:
            return ParsedQuery(original=expression)
        
        result = self._parse_expression(tokens)
        result.original = expression
        
        logger.debug(
            f"Parsed result: {len(result.required_groups)} required groups, "
            f"{len(result.excluded_terms)} excluded terms"
        )
        
        return result
    
    def _tokenize(self, expression: str) -> List[Token]:
        """
        Tokenize the expression into a list of tokens.
        
        Args:
            expression: The expression to tokenize.
            
        Returns:
            List of Token objects.
        """
        tokens = []
        pos = 0
        
        while pos < len(expression):
            match = None
            for pattern, token_type in self._compiled_patterns:
                match = pattern.match(expression, pos)
                if match:
                    if token_type is not None:  # Skip whitespace
                        value = match.group(1) if match.lastindex else match.group()
                        tokens.append(Token(token_type, value))
                    pos = match.end()
                    break
            
            if not match:
                raise ValueError(f"Unexpected character at position {pos}: {expression[pos]}")
        
        return tokens
    
    def _parse_expression(self, tokens: List[Token]) -> ParsedQuery:
        """
        Parse tokens into a ParsedQuery structure.
        
        This implements a simplified recursive descent parser.
        """
        result = ParsedQuery()
        current_group: List[str] = []
        negate_next = False
        pos = 0
        paren_depth = 0
        paren_start = -1
        
        while pos < len(tokens):
            token = tokens[pos]
            
            if token.type == TokenType.LPAREN:
                if paren_depth == 0:
                    paren_start = pos + 1
                paren_depth += 1
                pos += 1
                continue
            
            if token.type == TokenType.RPAREN:
                paren_depth -= 1
                if paren_depth == 0:
                    # Parse the parenthesized sub-expression
                    sub_tokens = tokens[paren_start:pos]
                    if sub_tokens:
                        sub_result = self._parse_expression(sub_tokens)
                        
                        if negate_next:
                            # Add all terms from sub-result as excluded
                            for group in sub_result.required_groups:
                                result.excluded_terms.extend(group)
                            negate_next = False
                        else:
                            # Merge sub-result
                            if sub_result.required_groups:
                                if len(sub_result.required_groups) == 1:
                                    # Single OR group from parens
                                    current_group.extend(sub_result.required_groups[0])
                                else:
                                    # Multiple AND groups
                                    if current_group:
                                        result.required_groups.append(current_group)
                                        current_group = []
                                    result.required_groups.extend(sub_result.required_groups)
                            result.excluded_terms.extend(sub_result.excluded_terms)
                pos += 1
                continue
            
            if paren_depth > 0:
                pos += 1
                continue
            
            if token.type == TokenType.NOT:
                negate_next = True
                pos += 1
                continue
            
            if token.type == TokenType.AND:
                # End current OR group, start new one
                if current_group:
                    result.required_groups.append(current_group)
                    current_group = []
                pos += 1
                continue
            
            if token.type == TokenType.OR:
                # Continue current OR group
                pos += 1
                continue
            
            if token.type in (TokenType.TERM, TokenType.QUOTE):
                if negate_next:
                    result.excluded_terms.append(token.value)
                    negate_next = False
                else:
                    current_group.append(token.value)
                pos += 1
                continue
            
            pos += 1
        
        # Add final group
        if current_group:
            result.required_groups.append(current_group)
        
        return result
    
    def to_sql_conditions(
        self,
        parsed: ParsedQuery,
        fields: List[str],
        case_insensitive: bool = True,
    ) -> str:
        """
        Convert a parsed query to SQL WHERE conditions.
        
        Args:
            parsed: The parsed query structure.
            fields: List of GDELT fields to search (e.g., ['V2Themes', 'AllNames']).
            case_insensitive: Whether to use case-insensitive matching.
            
        Returns:
            SQL WHERE clause string (without the WHERE keyword).
        """
        conditions = []
        prefix = "(?i)" if case_insensitive else ""
        
        # Required groups (AND between groups, OR within groups)
        for group in parsed.required_groups:
            if not group:
                continue
            
            # Build OR pattern for this group
            pattern = "|".join(re.escape(term) for term in group)
            
            # Match against any of the fields
            field_conditions = []
            for field in fields:
                field_conditions.append(
                    f"REGEXP_CONTAINS({field}, r'{prefix}({pattern})')"
                )
            
            if len(field_conditions) == 1:
                conditions.append(field_conditions[0])
            else:
                conditions.append(f"({' OR '.join(field_conditions)})")
        
        # Excluded terms (NOT)
        for term in parsed.excluded_terms:
            for field in fields:
                conditions.append(
                    f"NOT REGEXP_CONTAINS({field}, r'{prefix}{re.escape(term)}')"
                )
        
        if not conditions:
            return "TRUE"
        
        return " AND ".join(conditions)


def parse_boolean_query(expression: str) -> ParsedQuery:
    """
    Convenience function to parse a Boolean expression.
    
    Args:
        expression: The Boolean expression to parse.
        
    Returns:
        ParsedQuery with structured query components.
    """
    parser = BooleanParser()
    return parser.parse(expression)


