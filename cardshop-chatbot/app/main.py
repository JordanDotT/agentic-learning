import logging
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional, List

from .models import (
    ChatRequest, ChatResponse, HealthResponse, 
    InventorySearchRequest, Card, SearchFilter
)
from .chat_handler import ClaudeChatHandler
from .inventory import InventoryManager
from .guardrails import GuardrailsManager
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
chat_handler: Optional[ClaudeChatHandler] = None
inventory_manager: Optional[InventoryManager] = None
guardrails_manager: Optional[GuardrailsManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global chat_handler, inventory_manager, guardrails_manager
    
    # Startup
    logger.info("Starting Derpdot Cards Chatbot API...")
    
    try:
        # Initialize managers
        inventory_manager = InventoryManager(settings.csv_inventory_path)
        guardrails_manager = GuardrailsManager(
            settings.rate_limit_requests, 
            settings.rate_limit_window
        )
        chat_handler = ClaudeChatHandler()
        
        logger.info("All components initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Derpdot Cards Chatbot API...")


# Create FastAPI app
app = FastAPI(
    title="Derpdot Cards Chatbot API",
    description="A trading card shop chatbot powered by Anthropic Claude",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )


@app.get("/")
async def root():
    """Serve the chat interface"""
    return FileResponse("static/index.html")

@app.get("/api", response_model=dict)
async def api_info():
    """API information endpoint"""
    return {
        "message": "Welcome to Derpdot Cards Chatbot API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "chat": "/chat",
            "health": "/health",
            "inventory_search": "/inventory/search",
            "card_details": "/inventory/card/{card_id}"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Test inventory manager
        if inventory_manager:
            stats = inventory_manager.get_inventory_stats()
            inventory_healthy = stats.get("unique_cards", 0) > 0
        else:
            inventory_healthy = False
        
        # Test guardrails
        guardrails_healthy = guardrails_manager is not None
        
        # Test chat handler
        chat_handler_healthy = chat_handler is not None
        
        if inventory_healthy and guardrails_healthy and chat_handler_healthy:
            status = "healthy"
        else:
            status = "degraded"
        
        return HealthResponse(status=status)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(status="unhealthy")


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    chat_request: ChatRequest,
    request: Request
):
    """Main chat endpoint"""
    if not chat_handler:
        raise HTTPException(status_code=503, detail="Chat service unavailable")
    
    try:
        client_ip = get_client_ip(request)
        
        response = await chat_handler.process_message(
            message=chat_request.message,
            session_id=chat_request.session_id,
            client_ip=client_ip
        )
        
        # Add rate limiting headers
        if guardrails_manager:
            remaining = guardrails_manager.get_remaining_requests(client_ip)
            response_dict = response.model_dump(mode='json')
            
            # Return response with rate limit info in headers
            json_response = JSONResponse(content=response_dict)
            json_response.headers["X-RateLimit-Remaining"] = str(remaining)
            json_response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
            json_response.headers["X-RateLimit-Window"] = str(settings.rate_limit_window)
            
            return json_response
        
        return response
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process message. Please try again."
        )


@app.get("/inventory/search", response_model=List[Card])
async def search_inventory(
    query: Optional[str] = None,
    set_name: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    condition: Optional[str] = None,
    rarity: Optional[str] = None,
    in_stock_only: bool = True,
    max_results: int = 10
):
    """Search inventory endpoint"""
    if not inventory_manager:
        raise HTTPException(status_code=503, detail="Inventory service unavailable")
    
    try:
        if query:
            # Simple name search
            cards = inventory_manager.search_cards(query, max_results)
        else:
            # Advanced search with filters
            filters = SearchFilter(
                set_name=set_name,
                min_price=min_price,
                max_price=max_price,
                condition=condition,
                rarity=rarity,
                in_stock_only=in_stock_only
            )
            cards = inventory_manager.advanced_search(filters, max_results)
        
        return cards
        
    except Exception as e:
        logger.error(f"Error searching inventory: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to search inventory. Please try again."
        )


@app.get("/inventory/card/{card_id}", response_model=Card)
async def get_card_details(card_id: int):
    """Get card details endpoint"""
    if not inventory_manager:
        raise HTTPException(status_code=503, detail="Inventory service unavailable")
    
    try:
        card = inventory_manager.get_card_details(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        return card
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting card details: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get card details. Please try again."
        )


@app.get("/inventory/stats", response_model=dict)
async def get_inventory_stats():
    """Get inventory statistics"""
    if not inventory_manager:
        raise HTTPException(status_code=503, detail="Inventory service unavailable")
    
    try:
        return inventory_manager.get_inventory_stats()
        
    except Exception as e:
        logger.error(f"Error getting inventory stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get inventory statistics."
        )


@app.post("/inventory/reload", response_model=dict)
async def reload_inventory():
    """Reload inventory from CSV (admin endpoint)"""
    if not inventory_manager:
        raise HTTPException(status_code=503, detail="Inventory service unavailable")
    
    try:
        success = inventory_manager.reload_inventory()
        if success:
            return {"message": "Inventory reloaded successfully"}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to reload inventory"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reloading inventory: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to reload inventory."
        )


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )