# Maple Cards Chatbot

A sophisticated trading card shop chatbot powered by FastAPI and Anthropic Claude, designed for Canadian trading card retailers.

## Features

- **Intelligent Chat Interface**: Claude 3 Sonnet-powered conversations about trading cards
- **Inventory Management**: CSV-based inventory system with fuzzy search capabilities
- **Multi-Game Support**: Magic: The Gathering, Pokemon, Yu-Gi-Oh, and more
- **Safety Guardrails**: Input validation, rate limiting, and content filtering
- **RESTful API**: Comprehensive endpoints for chat, search, and inventory management
- **Canadian Focus**: Prices in CAD with professional shop experience

## Project Structure

```
cardshop-chatbot/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── chat_handler.py      # Anthropic Claude integration
│   ├── inventory.py         # CSV inventory management
│   ├── models.py            # Pydantic data models
│   └── guardrails.py        # Input validation and safety
├── data/
│   ├── inventory.csv        # Sample card inventory data
│   └── conversations.csv    # Chat history storage
├── config/
│   └── settings.py          # Configuration and environment variables
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── README.md               # This file
```

## Quick Start

### 1. Prerequisites

- Python 3.8+
- Anthropic API key

### 2. Installation

```bash
# Clone or download the project
cd cardshop-chatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings
nano .env
```

Required environment variables:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CSV_INVENTORY_PATH=data/inventory.csv
CSV_CONVERSATIONS_PATH=data/conversations.csv
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
LOG_LEVEL=INFO
```

### 4. Run the Application

```bash
# Start the development server
uvicorn app.main:app --reload

# Or run directly
python -m app.main
```

The API will be available at `http://localhost:8000`

### 5. Test the API

Visit `http://localhost:8000/docs` for interactive API documentation.

## API Endpoints

### Chat Endpoints

**POST /chat**
Send a message to the chatbot.

```json
{
  "message": "Do you have Lightning Bolt in stock?",
  "session_id": "optional-session-id"
}
```

Response:
```json
{
  "response": "I found several Lightning Bolt cards in our inventory...",
  "cards": [...],
  "suggested_actions": [...],
  "session_id": "session-id",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Inventory Endpoints

**GET /inventory/search**
Search for cards with optional filters.

Query parameters:
- `query`: Card name to search for
- `set_name`: Filter by set name
- `min_price`, `max_price`: Price range in CAD
- `condition`: Card condition filter
- `rarity`: Rarity filter
- `in_stock_only`: Only show cards in stock (default: true)
- `max_results`: Maximum results (default: 10)

**GET /inventory/card/{card_id}**
Get detailed information about a specific card.

**GET /inventory/stats**
Get inventory statistics and overview.

**POST /inventory/reload**
Reload inventory from CSV file (admin function).

### Utility Endpoints

**GET /health**
Health check endpoint.

**GET /**
API information and available endpoints.

## Sample Conversations

The chatbot can handle various types of queries:

1. **Stock Inquiries**
   - "Do you have Lightning Bolt in stock?"
   - "What's available from Innistrad set?"

2. **Price Queries**
   - "How much is Black Lotus?"
   - "Show me cards under $10"

3. **Deck Building**
   - "I need blue creatures for my Commander deck"
   - "What artifacts work well in Modern?"

4. **General Questions**
   - "What's the condition of your expensive cards?"
   - "Do you have any Pokemon cards?"

## Configuration Options

### Settings (config/settings.py)

- `anthropic_api_key`: Your Anthropic API key
- `csv_inventory_path`: Path to inventory CSV file
- `csv_conversations_path`: Path to conversation history CSV
- `cors_origins`: Allowed CORS origins for web frontends
- `log_level`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `max_search_results`: Default maximum search results
- `max_conversation_history`: Maximum messages to keep in memory
- `rate_limit_requests`: Requests per window for rate limiting
- `rate_limit_window`: Rate limiting window in seconds

### Inventory CSV Format

The inventory CSV should have these columns:

```csv
card_id,name,set_name,rarity,condition,price_cad,quantity,image_url,description
1,Lightning Bolt,Unlimited Edition,Common,Near Mint,2.50,12,https://example.com/image.jpg,Deal 3 damage to any target
```

Required columns:
- `card_id`: Unique integer identifier
- `name`: Card name
- `set_name`: Set or expansion name
- `rarity`: Common, Uncommon, Rare, Mythic Rare, etc.
- `condition`: Mint, Near Mint, Lightly Played, etc.
- `price_cad`: Price in Canadian dollars
- `quantity`: Number in stock

Optional columns:
- `image_url`: URL to card image
- `description`: Card description or rules text

## Safety Features

### Input Validation
- Message length limits
- Session ID validation
- Character filtering for security

### Content Filtering
- Prompt injection detection
- Off-topic redirection
- Trading card focus enforcement

### Rate Limiting
- Per-IP request limits
- Configurable time windows
- Graceful degradation

### Business Rules
- Inventory verification requirements
- Price disclaimer enforcement
- Professional disclaimer language

## Development

### Adding New Card Games

1. Update the sample data in `data/inventory.csv`
2. Modify the system prompt in `chat_handler.py` if needed
3. Add game-specific keywords to `guardrails.py`

### Extending Inventory Management

The `InventoryManager` class can be extended to support:
- Database backends (PostgreSQL, MySQL)
- Real-time inventory updates
- Advanced filtering and sorting
- Bulk operations

### Custom Guardrails

Modify `guardrails.py` to add:
- Custom validation rules
- Business-specific content filters
- Enhanced rate limiting strategies

## Deployment

### Production Considerations

1. **Environment Variables**: Use proper secret management
2. **Database**: Consider migrating from CSV to a proper database
3. **Caching**: Add Redis for conversation and inventory caching
4. **Monitoring**: Implement proper logging and monitoring
5. **Security**: Add HTTPS, authentication, and proper CORS settings

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Health Checks

The `/health` endpoint provides application health status:
- `healthy`: All components operational
- `degraded`: Some components have issues
- `unhealthy`: Critical components failing

## Troubleshooting

### Common Issues

**"Anthropic API key not found"**
- Ensure your `.env` file contains a valid `ANTHROPIC_API_KEY`
- Verify the API key is active and has sufficient credits

**"Inventory file not found"**
- Check that `data/inventory.csv` exists
- Verify the path in your environment variables

**"Rate limit exceeded"**
- Wait for the rate limit window to reset
- Adjust rate limiting settings in configuration

**"Chat responses seem off-topic"**
- Review the system prompt in `chat_handler.py`
- Check guardrails configuration in `guardrails.py`

### Logs

Logs are written to stdout with configurable verbosity. Check logs for:
- API request/response details
- Inventory loading status
- Claude API interactions
- Error messages and stack traces

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is provided as-is for educational and commercial use. Please ensure compliance with Anthropic's API terms of service.

## Support

For technical issues:
1. Check the logs for error details
2. Verify your configuration and API keys
3. Review the troubleshooting section
4. Open an issue with detailed information

For business inquiries about customization or deployment, please contact the development team.