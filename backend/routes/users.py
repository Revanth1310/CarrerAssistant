# routes/users.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
import shutil, os
import json
import fitz  # for PDFs
import asyncio
import docx  # for .docx files
from PIL import Image  # for images
import pytesseract  # for OCR text extraction from images
from routes.agents import get_job_ids, fetch_all_jobs_async, get_pages_content
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentExecutor
from langchain.agents.agent_types import AgentType
from database import get_db
from model import User

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)




# --- Signup route (supports file upload + form fields) ---
@router.post("/signup")
async def signup(
    username: str = Form(...),
    password: str = Form(...),
    age: int = Form(...),
    current_study: str = Form(""),
    goal: str = Form(""),
    skills: str = Form(""),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # --- Save uploaded file ---
    file_path = None
    parsed_text = ""
    if file:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract text from uploaded document
        parsed_text = extract_text_from_file(file_path)

    # --- Create new user record ---
    new_user = User(
        username=username,
        password=password,
        age=age,
        current_study=current_study,
        goal=goal,
        skills=skills,
        document_path=file_path,
        parsed_text=parsed_text,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully", "user_id": new_user.id}



@router.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(User.username == username, User.password == password).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful", "user": db_user.username}
    



# --- Helper function: Parse Document text ---
def extract_text_from_file(file_path: str) -> str:
    """
    Extracts text from PDF, DOCX, TXT, PNG, JPG, JPEG files.
    """
    text = ""
    ext = os.path.splitext(file_path)[-1].lower()

    try:
        if ext == ".pdf":
            with fitz.open(file_path) as pdf:
                for page in pdf:
                    text += page.get_text()

        elif ext == ".docx":
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"

        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

        elif ext in [".jpg", ".jpeg", ".png"]:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)

        else:
            text = "Unsupported file type."

    except Exception as e:
        text = f"Error reading file: {str(e)}"

    return text.strip()





@router.post("/chat")
async def chat_with_agent(
    query: str = Form(...),
    username: str = Form(...), 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")


    if not query:
        return {"error": "No query provided"}

    # --- Initialize Gemini model ---
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.7
    )

    # --- Define helper tools ---
    def web_search_tool(query: str) -> str:
        try:
            result = get_pages_content(query)  # blocking; run inside agent thread below
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"Error fetching web content: {str(e)}"})

    def job_search_tool(job_title: str, location: str = "", limit: int = 5) -> str:
        try:
            job_ids = get_job_ids(job_title, location, limit=limit)
            if not job_ids:
                return json.dumps({"jobs": [], "note": "No job IDs found."})
            # fetch_all_jobs_async is async — safe to run with asyncio.run inside a background thread
            jobs = asyncio.run(fetch_all_jobs_async(job_ids))
            return json.dumps({"jobs": jobs}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

# ---------------------------
# No-op tool to avoid None warnings
# ---------------------------
    def noop_tool(_input: str) -> str:
        return "No additional tools required."

    prompt = f"""
You are a career guidance assistant. Use the following user document context to help answer career-related queries.
Context from user's documents:
{user.parsed_text}

User Query: {query}

Please consider the above context while providing career guidance and answering the query.
When you use the "Job Search" tool it will return JSON with job postings.
If you use the "Web Search" tool it will return JSON of pages scraped.
prrovide examples where relevant.provide links to resources where applicable.
at last, summarize your suggestions in bullet points or para in short
"""

    

        # --- Initialize the agent with tools ---
    tools = [
        Tool(name="Web Search", func=web_search_tool, description="Search the web for information on careers, skills, or companies."),
        Tool(name="Job Search", func=job_search_tool, description="Find recent job openings for specific roles."),
        Tool(name="NoOp", func=noop_tool, description="No operation: use when no more tools are needed.")
    ]   

    agent_executor = initialize_agent(
        tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True
    )

    # --- Run the query through the agent ---
    try:
        response = await asyncio.to_thread(agent_executor.run, prompt)
        return {"response": response}
    except Exception as e:
        return {"error": str(e)}    