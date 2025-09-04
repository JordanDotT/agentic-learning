from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class CardCondition(str, Enum):
    MINT = "Mint"
    NEAR_MINT = "Near Mint"
    LIGHTLY_PLAYED = "Lightly Played"
    MODERATELY_PLAYED = "Moderately Played"
    HEAVILY_PLAYED = "Heavily Played"
    DAMAGED = "Damaged"


class CardRarity(str, Enum):
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    MYTHIC = "Mythic Rare"
    LEGENDARY = "Legendary"
    SPECIAL = "Special"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: Optional[str] = None


class Card(BaseModel):
    card_id: int
    name: str
    set_name: str
    rarity: CardRarity
    condition: CardCondition
    price_cad: float
    quantity: int
    image_url: Optional[str] = None
    description: Optional[str] = None


class SearchFilter(BaseModel):
    name: Optional[str] = None
    set_name: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    condition: Optional[CardCondition] = None
    rarity: Optional[CardRarity] = None
    in_stock_only: bool = True


class SuggestedAction(BaseModel):
    action: str
    description: str
    card_id: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    cards: List[Card] = []
    suggested_actions: List[SuggestedAction] = []
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class InventorySearchRequest(BaseModel):
    query: Optional[str] = None
    filters: SearchFilter = Field(default_factory=SearchFilter)
    max_results: int = 10


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"