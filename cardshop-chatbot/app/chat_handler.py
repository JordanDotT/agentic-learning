import json
import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd
from pathlib import Path

import anthropic

from .models import ChatMessage, ChatResponse, Card, SuggestedAction, MessageRole
from .inventory import InventoryManager
from .guardrails import GuardrailsManager
from config.settings import settings

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation history and persistence"""
    
    def __init__(self, csv_path: str, max_history: int = 20):
        self.csv_path = Path(csv_path)
        self.max_history = max_history
        self._ensure_csv_exists()
    
    def _ensure_csv_exists(self):
        """Ensure conversations CSV file exists with proper headers"""
        if not self.csv_path.exists():
            df = pd.DataFrame(columns=['session_id', 'role', 'content', 'timestamp'])
            df.to_csv(self.csv_path, index=False)
    
    def save_message(self, session_id: str, role: MessageRole, content: str):
        """Save message to conversation history"""
        try:
            message_data = {
                'session_id': session_id,
                'role': role.value,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }
            
            # Append to CSV
            df = pd.DataFrame([message_data])
            df.to_csv(self.csv_path, mode='a', header=False, index=False)
            
        except Exception as e:
            logger.error(f"Error saving message to conversation history: {e}")
    
    def get_conversation_history(self, session_id: str) -> List[ChatMessage]:
        """Get conversation history for a session"""
        try:
            if not self.csv_path.exists():
                return []
            
            df = pd.read_csv(self.csv_path)
            session_messages = df[df['session_id'] == session_id].tail(self.max_history)
            
            messages = []
            for _, row in session_messages.iterrows():
                messages.append(ChatMessage(
                    role=MessageRole(row['role']),
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    session_id=session_id
                ))
            
            return messages
            
        except Exception as e:
            logger.error(f"Error loading conversation history: {e}")
            return []


class InventoryTool:
    """Tool for inventory operations that Claude can call"""
    
    def __init__(self, inventory_manager: InventoryManager):
        self.inventory = inventory_manager
    
    def search_cards(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search for cards by name"""
        try:
            cards = self.inventory.search_cards(query, max_results)
            return {
                "success": True,
                "results": [card.model_dump(mode='json') for card in cards],
                "count": len(cards)
            }
        except Exception as e:
            logger.error(f"Error searching cards: {e}")
            return {"success": False, "error": str(e)}
    
    def check_stock(self, card_name: str) -> Dict[str, Any]:
        """Check stock for a specific card"""
        try:
            result = self.inventory.check_stock(card_name)
            if result["found"] and "cards" in result:
                result["cards"] = [card.model_dump(mode='json') for card in result["cards"]]
            if "suggestions" in result:
                result["suggestions"] = [card.model_dump(mode='json') for card in result["suggestions"]]
            return result
        except Exception as e:
            logger.error(f"Error checking stock: {e}")
            return {"success": False, "error": str(e)}
    
    def get_card_details(self, card_id: int) -> Dict[str, Any]:
        """Get details for a specific card"""
        try:
            card = self.inventory.get_card_details(card_id)
            if card:
                return {"success": True, "card": card.model_dump(mode='json')}
            return {"success": False, "error": "Card not found"}
        except Exception as e:
            logger.error(f"Error getting card details: {e}")
            return {"success": False, "error": str(e)}
    
    def filter_by_price_range(self, min_price: float, max_price: float, max_results: int = 10) -> Dict[str, Any]:
        """Filter cards by price range"""
        try:
            cards = self.inventory.filter_by_price_range(min_price, max_price, max_results)
            return {
                "success": True,
                "results": [card.model_dump(mode='json') for card in cards],
                "count": len(cards)
            }
        except Exception as e:
            logger.error(f"Error filtering by price: {e}")
            return {"success": False, "error": str(e)}
    
    def get_inventory_stats(self) -> Dict[str, Any]:
        """Get inventory statistics"""
        try:
            return self.inventory.get_inventory_stats()
        except Exception as e:
            logger.error(f"Error getting inventory stats: {e}")
            return {"success": False, "error": str(e)}
    
    def browse_by_game(self, game_type: str, max_results: int = 3) -> Dict[str, Any]:
        """Browse cards by game type (Magic, Pokemon, Yu-Gi-Oh)"""
        try:
            # Simple keyword search for different games
            game_keywords = {
                "magic": "magic",
                "mtg": "magic", 
                "pokemon": "pokemon",
                "yugioh": "yu-gi-oh",
                "yu-gi-oh": "yu-gi-oh"
            }
            
            search_term = game_keywords.get(game_type.lower(), game_type)
            
            # Search by description or set name for game-specific cards
            if search_term == "magic":
                # For Magic, look for common MTG sets or terms
                magic_cards = []
                sets_to_check = ["Unlimited", "Alpha", "Core", "Modern", "Commander", "Tempest", "Ice Age"]
                for set_name in sets_to_check:
                    cards = self.inventory.filter_by_set(set_name, 10)
                    magic_cards.extend(cards)
                
                # Remove duplicates and sort by price descending
                seen_ids = set()
                unique_cards = []
                for card in magic_cards:
                    if card.card_id not in seen_ids:
                        unique_cards.append(card)
                        seen_ids.add(card.card_id)
                
                # Sort by price descending and take top results
                unique_cards.sort(key=lambda x: x.price_cad, reverse=True)
                top_cards = unique_cards[:max_results]
                
                return {
                    "success": True,
                    "results": [card.model_dump(mode='json') for card in top_cards],
                    "count": len(top_cards),
                    "game_type": "Magic: The Gathering",
                    "sorted_by": "price_desc"
                }
            
            elif search_term == "pokemon":
                # Search for Pokemon cards and sort by price
                pokemon_cards = self.inventory.filter_by_set("Base Set", 20)
                # Sort by price descending
                pokemon_cards.sort(key=lambda x: x.price_cad, reverse=True)
                top_pokemon = pokemon_cards[:max_results]
                
                return {
                    "success": True,
                    "results": [card.model_dump(mode='json') for card in top_pokemon],
                    "count": len(top_pokemon),
                    "game_type": "Pokemon",
                    "sorted_by": "price_desc"
                }
            
            elif search_term == "yu-gi-oh":
                # Search for Yu-Gi-Oh cards and sort by price
                yugioh_sets = ["Legend of Blue Eyes", "Metal Raiders", "Pharaoh's Servant", "Starter Deck"]
                yugioh_cards = []
                for set_name in yugioh_sets:
                    cards = self.inventory.filter_by_set(set_name, 8)
                    yugioh_cards.extend(cards)
                
                # Sort by price descending
                yugioh_cards.sort(key=lambda x: x.price_cad, reverse=True)
                top_yugioh = yugioh_cards[:max_results]
                
                return {
                    "success": True,
                    "results": [card.model_dump(mode='json') for card in top_yugioh],
                    "count": len(top_yugioh),
                    "game_type": "Yu-Gi-Oh",
                    "sorted_by": "price_desc"
                }
            
            else:
                # General search
                cards = self.inventory.search_cards(search_term, max_results)
                return {
                    "success": True,
                    "results": [card.model_dump(mode='json') for card in cards],
                    "count": len(cards),
                    "game_type": f"{game_type} cards"
                }
                
        except Exception as e:
            logger.error(f"Error browsing by game: {e}")
            return {"success": False, "error": str(e)}


class ClaudeChatHandler:
    """Main chat handler using Anthropic Claude"""
    
    SYSTEM_PROMPT = """You are a helpful and knowledgeable assistant for Derpdot Cards, a premium trading card shop. You specialize in Magic: The Gathering, Pokemon, Yu-Gi-Oh, and other trading card games.

Your role and guidelines:
1. ONLY discuss topics related to trading cards, card games, and our shop
2. ALWAYS verify inventory before making claims about card availability or pricing
3. Provide prices in Canadian dollars (CAD)
4. Maintain a professional but friendly tone
5. Never make promises about stock without checking our database first
6. When customers ask about cards, use the inventory tools to search and provide accurate information
7. If asked about non-card topics, politely redirect to card-related discussions
8. Include appropriate disclaimers about pricing and stock availability
9. Help customers find cards for their decks, collections, or competitive play
10. Provide card details, pricing, and condition information when available

You have access to the following inventory tools:
- search_cards: Search for cards by name
- check_stock: Check if specific cards are in stock
- get_card_details: Get detailed information about a specific card
- filter_by_price_range: Find cards within a price range
- get_inventory_stats: Get general inventory information

Always use these tools when customers ask about specific cards, availability, or pricing.

Remember: You're representing a Canadian trading card shop, so be helpful, accurate, and professional while maintaining enthusiasm for trading cards and games!"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.inventory_manager = InventoryManager(settings.csv_inventory_path)
        self.conversation_manager = ConversationManager(settings.csv_conversations_path, settings.max_conversation_history)
        self.guardrails = GuardrailsManager(settings.rate_limit_requests, settings.rate_limit_window)
        self.inventory_tool = InventoryTool(self.inventory_manager)
        
        # Define available tools for Claude
        self.tools = [
            {
                "name": "search_cards",
                "description": "Search for trading cards by name with fuzzy matching",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Card name to search for"},
                        "max_results": {"type": "integer", "description": "Maximum number of results (default 10)", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "check_stock",
                "description": "Check stock availability for a specific card name",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "card_name": {"type": "string", "description": "Exact or partial card name to check"}
                    },
                    "required": ["card_name"]
                }
            },
            {
                "name": "get_card_details",
                "description": "Get detailed information about a specific card by ID",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "card_id": {"type": "integer", "description": "Unique card ID"}
                    },
                    "required": ["card_id"]
                }
            },
            {
                "name": "filter_by_price_range",
                "description": "Find cards within a specific price range",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "min_price": {"type": "number", "description": "Minimum price in CAD"},
                        "max_price": {"type": "number", "description": "Maximum price in CAD"},
                        "max_results": {"type": "integer", "description": "Maximum number of results", "default": 10}
                    },
                    "required": ["min_price", "max_price"]
                }
            },
            {
                "name": "get_inventory_stats",
                "description": "Get general inventory statistics and information",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "browse_by_game",
                "description": "Browse and show cards by game type (Magic/MTG, Pokemon, Yu-Gi-Oh)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "game_type": {"type": "string", "description": "Type of card game: magic, pokemon, yugioh"},
                        "max_results": {"type": "integer", "description": "Maximum number of cards to show", "default": 3}
                    },
                    "required": ["game_type"]
                }
            }
        ]
    
    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool function"""
        try:
            if tool_name == "search_cards":
                return self.inventory_tool.search_cards(
                    query=tool_input["query"],
                    max_results=tool_input.get("max_results", 10)
                )
            elif tool_name == "check_stock":
                return self.inventory_tool.check_stock(tool_input["card_name"])
            elif tool_name == "get_card_details":
                return self.inventory_tool.get_card_details(tool_input["card_id"])
            elif tool_name == "filter_by_price_range":
                return self.inventory_tool.filter_by_price_range(
                    min_price=tool_input["min_price"],
                    max_price=tool_input["max_price"],
                    max_results=tool_input.get("max_results", 10)
                )
            elif tool_name == "get_inventory_stats":
                return self.inventory_tool.get_inventory_stats()
            elif tool_name == "browse_by_game":
                return self.inventory_tool.browse_by_game(
                    game_type=tool_input["game_type"],
                    max_results=tool_input.get("max_results", 3)
                )
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def _build_conversation_messages(self, session_id: str, new_message: str) -> List[Dict[str, str]]:
        """Build conversation messages for Claude API"""
        messages = []
        
        # Get conversation history
        history = self.conversation_manager.get_conversation_history(session_id)
        
        # Add historical messages (skip system messages)
        for msg in history:
            if msg.role != MessageRole.SYSTEM:
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        
        # Add new user message
        messages.append({
            "role": MessageRole.USER.value,
            "content": new_message
        })
        
        return messages
    
    def _extract_cards_from_tools(self, tool_results: List[Dict[str, Any]]) -> List[Card]:
        """Extract card objects from tool execution results"""
        cards = []
        
        for result in tool_results:
            if result.get("success"):
                # Handle different result formats
                if "results" in result:
                    for card_dict in result["results"]:
                        try:
                            cards.append(Card(**card_dict))
                        except Exception as e:
                            logger.warning(f"Error creating card from dict: {e}")
                elif "card" in result:
                    try:
                        cards.append(Card(**result["card"]))
                    except Exception as e:
                        logger.warning(f"Error creating card from dict: {e}")
                elif "cards" in result:
                    for card_dict in result["cards"]:
                        try:
                            cards.append(Card(**card_dict))
                        except Exception as e:
                            logger.warning(f"Error creating card from dict: {e}")
        
        return cards
    
    def _generate_suggested_actions(self, cards: List[Card], user_message: str) -> List[SuggestedAction]:
        """Generate suggested actions based on context"""
        actions = []
        
        # If cards were found, suggest viewing details
        if cards:
            if len(cards) == 1:
                actions.append(SuggestedAction(
                    action="View card details",
                    description=f"See full details for {cards[0].name}",
                    card_id=cards[0].card_id
                ))
            else:
                actions.append(SuggestedAction(
                    action="Browse similar cards",
                    description="Look at more cards like these"
                ))
        
        # General helpful actions
        if "price" in user_message.lower():
            actions.append(SuggestedAction(
                action="Search by price range",
                description="Find cards within your budget"
            ))
        
        if any(word in user_message.lower() for word in ["deck", "commander", "standard", "modern"]):
            actions.append(SuggestedAction(
                action="Browse by format",
                description="Find cards for your specific format"
            ))
        
        actions.append(SuggestedAction(
            action="Contact support",
            description="Speak with our trading card experts"
        ))
        
        return actions[:3]  # Limit to 3 suggestions
    
    async def process_message(self, message: str, session_id: Optional[str] = None, client_ip: str = "unknown") -> ChatResponse:
        """Process a user message and return a response"""
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Validate request
        is_valid, error_message = self.guardrails.validate_request(message, session_id, client_ip)
        if not is_valid:
            return ChatResponse(
                response=error_message,
                session_id=session_id,
                suggested_actions=[SuggestedAction(
                    action="Try again",
                    description="Rephrase your question about trading cards"
                )]
            )
        
        # Sanitize input
        clean_message = self.guardrails.sanitize_input(message)
        
        try:
            # Save user message
            self.conversation_manager.save_message(session_id, MessageRole.USER, clean_message)
            
            # Build conversation messages
            conversation_messages = self._build_conversation_messages(session_id, clean_message)
            
            # Call Claude API with tools
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                system=self.SYSTEM_PROMPT,
                messages=conversation_messages,
                tools=self.tools
            )
            
            assistant_response = ""
            tool_results = []
            
            # Process response content
            logger.info(f"Claude response content blocks: {len(response.content)}")
            for i, content_block in enumerate(response.content):
                logger.info(f"Content block {i}: type={content_block.type}")
                if content_block.type == "text":
                    assistant_response += content_block.text
                elif content_block.type == "tool_use":
                    # Execute the tool
                    logger.info(f"Executing tool: {content_block.name} with input: {content_block.input}")
                    tool_result = self._execute_tool(content_block.name, content_block.input)
                    logger.info(f"Tool result: {tool_result}")
                    tool_results.append(tool_result)
                    
                    # If tool use was successful, we might need to continue the conversation
                    if tool_result.get("success") or tool_result.get("found"):
                        # Create a follow-up message with tool results
                        follow_up_messages = conversation_messages + [
                            {
                                "role": "assistant",
                                "content": [
                                    {"type": "text", "text": assistant_response} if assistant_response else {"type": "text", "text": "Let me search our inventory..."},
                                    {"type": "tool_use", "id": content_block.id, "name": content_block.name, "input": content_block.input}
                                ]
                            },
                            {
                                "role": "user",
                                "content": [
                                    {"type": "tool_result", "tool_use_id": content_block.id, "content": json.dumps(tool_result)}
                                ]
                            }
                        ]
                        
                        # Get follow-up response from Claude
                        follow_up_response = self.client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=1000,
                            system=self.SYSTEM_PROMPT,
                            messages=follow_up_messages
                        )
                        
                        # Extract the follow-up text response
                        for follow_up_content in follow_up_response.content:
                            if follow_up_content.type == "text":
                                assistant_response += follow_up_content.text
            
            # Process response with guardrails
            processed_response, disclaimers = self.guardrails.process_response(clean_message, assistant_response)
            
            # Add disclaimers to response
            if disclaimers:
                processed_response += "\n\n" + "\n".join(f"*{disclaimer}*" for disclaimer in disclaimers)
            
            # Save assistant response
            self.conversation_manager.save_message(session_id, MessageRole.ASSISTANT, processed_response)
            
            # Extract cards from tool results
            cards = self._extract_cards_from_tools(tool_results)
            
            # Generate suggested actions
            suggested_actions = self._generate_suggested_actions(cards, clean_message)
            
            return ChatResponse(
                response=processed_response,
                cards=cards,
                suggested_actions=suggested_actions,
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            
            # Fallback response
            fallback_response = "I apologize, but I'm experiencing technical difficulties. Please try again in a moment, or contact our support team for assistance with your trading card needs."
            
            return ChatResponse(
                response=fallback_response,
                session_id=session_id,
                suggested_actions=[
                    SuggestedAction(
                        action="Try again",
                        description="Retry your question"
                    ),
                    SuggestedAction(
                        action="Contact support",
                        description="Get help from our team"
                    )
                ]
            )