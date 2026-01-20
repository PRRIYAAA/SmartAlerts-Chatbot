# SmartAlerts Chatbot

A FastAPI-based chatbot that helps businesses create creative deal titles using Google's Gemini AI. It guides users through selecting a business category, subcategory, and generates AI-powered deal suggestions with pricing and discounts.

## Features

- Interactive chatbot flow for deal creation
- AI-generated creative deal titles using Gemini 2.5 Flash
- Support for multiple business categories (Food, Clothing, FMCG, Accessories)
- RESTful API with structured responses
- FastAPI framework for high performance

## Prerequisites

- Python 3.8+
- Google Gemini API key (get from [Google AI Studio](https://makersuite.google.com/app/apikey))

## Installation

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd SmartAlerts-Chatbot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Running the Application

Start the server with:
```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`

- API Documentation: `http://127.0.0.1:8000/docs` (Swagger UI)
- Health Check: `http://127.0.0.1:8000/`

## API Usage

### POST /chat

Interact with the chatbot. Send JSON requests to progress through the deal creation flow.

#### Request Body
```json
{
  "message": "string (optional)",
  "stage": "string",
  "categoryId": "integer (optional)",
  "subcategory": "string (optional)"
}
```

#### Stages
1. **start**: Provide `categoryId` to begin. Returns subcategories.
2. **select_subcategory**: Provide `subcategory`. Returns help options.
3. **business_help**: Generates AI deal titles.
4. **title_selection**: Select or request more titles.
5. **price_selection**: Choose a price.
6. **discount_selection**: Choose a discount.
7. **confirm_submit**: Confirm and save the deal.

#### Example Request
```bash
curl -X POST "http://127.0.0.1:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"stage": "start", "categoryId": 1}'
```

#### Response
```json
{
  "reply": "Select your Food business type:",
  "options": ["Bakery", "Cafe", "Restaurant", ...],
  "next_stage": "select_subcategory"
}
```

## Project Structure

```
SmartAlerts-Chatbot/
├── main.py              # Main FastAPI application
├── requirements.txt     # Python dependencies
├── .gitignore          # Git ignore rules
├── .env                # Environment variables (not committed)
└── README.md           # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.