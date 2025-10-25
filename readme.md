# Career Assistant

An AI-powered career guidance system using FastAPI, LangChain, and Google's Gemini model.

## Features

- Career path recommendations based on user profile
- Resume parsing and analysis (PDF, DOCX, TXT, Images)
- Job search integration with LinkedIn
- Real-time chat interface for career guidance
- Document processing with OCR support

## Prerequisites

- Python 3.9-3.11
- Tesseract OCR binary installed
- Google API key for Gemini
- LinkedIn API credentials (optional)

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd CarrerAssistant
```

2. Create and activate virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r backend/requirements.txt
```



4. Create `.env` file:
```plaintext
GOOGLE_API_KEY=your_api_key_here
LINKEDIN_EMAIL=your_linkedin_email  
LINKEDIN_PASS=your_linkedin_password  
SERPER_API_KEY=your_serper_api
FIRECRAWL_API_KEY=your_firecrawl_api
```

## Project Structure

```
CarrerAssistant/
├── backend/
│   ├── routes/
│   │   ├── users.py
│   │   └── agents.py
│   ├── database.py
│   ├── model.py
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   └── chat.html
|   |__ main.html
└── README.md
```

## Usage

1. Start the FastAPI server:
```bash
cd backend
uvicorn main:app --reload
```

2. Open frontend/chat.html in your browser

3. API endpoints available at:
- http://127.0.0.1:8000/docs (Swagger UI)
- http://127.0.0.1:8000/redoc (ReDoc)

## API Endpoints

- POST `/user/signup` - Create new user account
- POST `/user/login` - User authentication
- POST `/user/chat` - AI chat interface

## Technologies Used

- FastAPI
- SQLAlchemy
- LangChain
- Google Gemini
- PyMuPDF
- python-docx
- pytesseract
- LinkedIn API

## License

MIT License

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open pull request