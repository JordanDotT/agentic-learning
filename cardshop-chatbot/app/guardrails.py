import re
import time
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class InputValidator:
    """Input validation and sanitization"""
    
    MAX_MESSAGE_LENGTH = 1000
    MAX_SESSION_ID_LENGTH = 100
    
    # Patterns for potential prompt injection attempts
    INJECTION_PATTERNS = [
        r"ignore\s+previous\s+instructions",
        r"forget\s+everything",
        r"you\s+are\s+now",
        r"new\s+instructions",
        r"system\s*:\s*",
        r"assistant\s*:\s*",
        r"user\s*:\s*",
        r"<\s*system\s*>",
        r"<\s*assistant\s*>",
        r"<\s*user\s*>",
    ]
    
    # Patterns for inappropriate content
    INAPPROPRIATE_PATTERNS = [
        r"hack\s+into",
        r"break\s+into",
        r"steal\s+credit",
        r"fraud",
        r"scam",
        r"illegal",
    ]
    
    def __init__(self):
        self.injection_regex = re.compile("|".join(self.INJECTION_PATTERNS), re.IGNORECASE)
        self.inappropriate_regex = re.compile("|".join(self.INAPPROPRIATE_PATTERNS), re.IGNORECASE)
    
    def validate_message(self, message: str) -> Tuple[bool, Optional[str]]:
        """Validate user message for safety and appropriateness"""
        if not message or not isinstance(message, str):
            return False, "Message cannot be empty"
        
        # Length check
        if len(message) > self.MAX_MESSAGE_LENGTH:
            return False, f"Message too long. Maximum {self.MAX_MESSAGE_LENGTH} characters allowed"
        
        # Check for prompt injection attempts
        if self.injection_regex.search(message):
            logger.warning(f"Potential prompt injection attempt detected: {message[:100]}")
            return False, "Your message contains inappropriate instructions. Please rephrase your question about trading cards"
        
        # Check for inappropriate content
        if self.inappropriate_regex.search(message):
            logger.warning(f"Inappropriate content detected: {message[:100]}")
            return False, "Please keep your questions related to trading cards and our shop"
        
        return True, None
    
    def validate_session_id(self, session_id: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Validate session ID format"""
        if session_id is None:
            return True, None
        
        if not isinstance(session_id, str):
            return False, "Session ID must be a string"
        
        if len(session_id) > self.MAX_SESSION_ID_LENGTH:
            return False, f"Session ID too long. Maximum {self.MAX_SESSION_ID_LENGTH} characters allowed"
        
        # Only allow alphanumeric characters, hyphens, and underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
            return False, "Session ID contains invalid characters"
        
        return True, None
    
    def sanitize_message(self, message: str) -> str:
        """Sanitize message for safe processing"""
        # Remove any potential HTML/XML tags
        message = re.sub(r'<[^>]*>', '', message)
        
        # Remove excessive whitespace
        message = ' '.join(message.split())
        
        # Trim to max length
        if len(message) > self.MAX_MESSAGE_LENGTH:
            message = message[:self.MAX_MESSAGE_LENGTH]
        
        return message.strip()


class RateLimiter:
    """Rate limiting for API requests"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """Check if request is allowed for given identifier"""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        while self.requests[identifier] and self.requests[identifier][0] < window_start:
            self.requests[identifier].popleft()
        
        # Check if limit exceeded
        if len(self.requests[identifier]) >= self.max_requests:
            # Calculate when next request will be allowed
            oldest_request = self.requests[identifier][0]
            next_allowed = oldest_request + self.window_seconds
            wait_time = int(next_allowed - now)
            return False, wait_time
        
        # Record this request
        self.requests[identifier].append(now)
        return True, None
    
    def get_remaining_requests(self, identifier: str) -> int:
        """Get remaining requests for identifier"""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        while self.requests[identifier] and self.requests[identifier][0] < window_start:
            self.requests[identifier].popleft()
        
        return max(0, self.max_requests - len(self.requests[identifier]))


class ContentFilter:
    """Content filtering for responses"""
    
    # Topics that should be redirected to trading cards
    OFF_TOPIC_PATTERNS = [
        r"weather",
        r"politics",
        r"sports",
        r"cooking",
        r"travel",
        r"programming",
        r"cryptocurrency",
        r"stocks",
        r"real\s+estate",
    ]
    
    # Trading card related keywords
    CARD_KEYWORDS = [
        "card", "cards", "deck", "magic", "pokemon", "yugioh", "yu-gi-oh",
        "mtg", "tcg", "ccg", "booster", "pack", "rare", "common", "uncommon",
        "legendary", "mythic", "foil", "holographic", "set", "collection",
        "trade", "trading", "buy", "sell", "price", "value", "condition",
        "mint", "played", "damaged", "inventory", "stock"
    ]
    
    def __init__(self):
        self.off_topic_regex = re.compile("|".join(self.OFF_TOPIC_PATTERNS), re.IGNORECASE)
    
    def is_card_related(self, message: str) -> bool:
        """Check if message is related to trading cards"""
        message_lower = message.lower()
        
        # Check for card-related keywords
        for keyword in self.CARD_KEYWORDS:
            if keyword in message_lower:
                return True
        
        # If no card keywords found, it might be off-topic
        return False
    
    def should_redirect(self, message: str) -> Tuple[bool, Optional[str]]:
        """Check if message should be redirected to card topics"""
        if self.off_topic_regex.search(message):
            return True, "I'm here to help you with trading cards and our shop inventory. What cards are you looking for?"
        
        if not self.is_card_related(message) and len(message.split()) > 3:
            return True, "I specialize in trading cards! Are you looking for specific cards, or would you like to browse our inventory?"
        
        return False, None


class BusinessRulesEnforcer:
    """Enforce business rules and policies"""
    
    DISCLAIMER_TRIGGERS = [
        "price", "cost", "expensive", "cheap", "value", "worth",
        "buy", "purchase", "order", "payment", "card"
    ]
    
    STOCK_TRIGGERS = [
        "available", "in stock", "have", "quantity", "how many"
    ]
    
    def __init__(self):
        self.price_disclaimer = "Prices are subject to change and may vary based on card condition. Please verify current pricing before making a purchase."
        self.stock_disclaimer = "Stock levels are updated regularly but may change. Please contact us to confirm availability before visiting."
        self.purchase_disclaimer = "I can help you find cards, but purchases must be completed in-store or through our official website with proper payment processing."
    
    def get_required_disclaimers(self, message: str, response: str) -> List[str]:
        """Get required disclaimers based on message and response content"""
        disclaimers = []
        combined_text = (message + " " + response).lower()
        
        # Price-related disclaimer
        if any(trigger in combined_text for trigger in self.DISCLAIMER_TRIGGERS):
            if "price" in combined_text or "$" in response:
                disclaimers.append(self.price_disclaimer)
        
        # Stock-related disclaimer
        if any(trigger in combined_text for trigger in self.STOCK_TRIGGERS):
            if "stock" in combined_text or "available" in combined_text:
                disclaimers.append(self.stock_disclaimer)
        
        # Purchase-related disclaimer
        if any(word in combined_text for word in ["buy", "purchase", "order", "cart"]):
            disclaimers.append(self.purchase_disclaimer)
        
        return disclaimers
    
    def enforce_inventory_verification(self, response: str) -> str:
        """Ensure inventory claims are properly qualified"""
        # Add qualifiers to definitive stock statements
        qualified_response = response
        
        # Pattern for definitive availability statements
        availability_patterns = [
            (r"we have (\d+)", r"our current inventory shows \1"),
            (r"in stock", "currently in stock"),
            (r"available", "appears to be available"),
        ]
        
        for pattern, replacement in availability_patterns:
            qualified_response = re.sub(pattern, replacement, qualified_response, flags=re.IGNORECASE)
        
        return qualified_response


class GuardrailsManager:
    """Main guardrails manager coordinating all safety measures"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.validator = InputValidator()
        self.rate_limiter = RateLimiter(max_requests, window_seconds)
        self.content_filter = ContentFilter()
        self.business_rules = BusinessRulesEnforcer()
    
    def validate_request(self, message: str, session_id: Optional[str], client_ip: str) -> Tuple[bool, Optional[str]]:
        """Comprehensive request validation"""
        
        # Rate limiting check
        allowed, wait_time = self.rate_limiter.is_allowed(client_ip)
        if not allowed:
            return False, f"Rate limit exceeded. Please wait {wait_time} seconds before making another request."
        
        # Input validation
        valid_message, message_error = self.validator.validate_message(message)
        if not valid_message:
            return False, message_error
        
        valid_session, session_error = self.validator.validate_session_id(session_id)
        if not valid_session:
            return False, session_error
        
        # Content filtering
        should_redirect, redirect_message = self.content_filter.should_redirect(message)
        if should_redirect:
            return False, redirect_message
        
        return True, None
    
    def sanitize_input(self, message: str) -> str:
        """Sanitize user input"""
        return self.validator.sanitize_message(message)
    
    def process_response(self, message: str, response: str) -> Tuple[str, List[str]]:
        """Process response with business rules and disclaimers"""
        # Apply business rules
        processed_response = self.business_rules.enforce_inventory_verification(response)
        
        # Get required disclaimers
        disclaimers = self.business_rules.get_required_disclaimers(message, processed_response)
        
        return processed_response, disclaimers
    
    def get_remaining_requests(self, client_ip: str) -> int:
        """Get remaining requests for client"""
        return self.rate_limiter.get_remaining_requests(client_ip)