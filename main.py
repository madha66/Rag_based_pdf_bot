# =========================
# main.py
# =========================

import os
from pathlib import Path

import fitz
import mysql.connector

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA

load_dotenv()

# =========================
# MYSQL
# =========================

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Kdmy#$2005",
    database="pdf_ai"
)

cursor = conn.cursor(dictionary=True)

# =========================
# FASTAPI
# =========================

app = FastAPI(title="PDF AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent

VECTORSTORE_DIR = BASE_DIR / "vectorstores"

VECTORSTORE_DIR.mkdir(exist_ok=True)

# =========================
# GLOBALS
# =========================

current_vectorstore = None
current_chain = None
current_chat_id = None
current_pdf_name = None

# =========================
# REQUEST MODEL
# =========================

class QuestionRequest(BaseModel):
    question: str

# =========================
# EMBEDDINGS
# =========================

embedder = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

# =========================
# PDF FUNCTIONS
# =========================

def extract_text_from_pdf(pdf_bytes: bytes):

    doc = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    return "".join(
        page.get_text()
        for page in doc
    )

def split_text(text):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )

    return splitter.split_text(text)

def build_vectorstore(chunks):

    return FAISS.from_texts(
        chunks,
        embedding=embedder
    )

def save_vectorstore(vstore, chat_id):

    path = VECTORSTORE_DIR / f"chat_{chat_id}"

    vstore.save_local(str(path))

def load_vectorstore(chat_id):

    path = VECTORSTORE_DIR / f"chat_{chat_id}"

    if not path.exists():
        return None

    return FAISS.load_local(
        str(path),
        embedder,
        allow_dangerous_deserialization=True
    )

def get_llm():

    groq_api_key = os.environ.get("GROQ_API_KEY")

    if not groq_api_key:
        raise ValueError("GROQ_API_KEY missing")

    return ChatGroq(
        model_name="llama-3.1-8b-instant",
        temperature=0.3,
        max_tokens=300
    )

def get_answer(vstore, query, llm):

    retriever = vstore.as_retriever(
        search_kwargs={"k": 3}
    )

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff"
    )

    result = qa.invoke({
        "query": query
    })

    return result["result"]

# =========================
# STATIC FILES
# =========================

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")

@app.get("/style.css")
def css():
    return FileResponse(BASE_DIR / "style.css")

@app.get("/app.js")
def js():
    return FileResponse(BASE_DIR / "app.js")

# =========================
# CREATE CHAT
# =========================

@app.post("/api/new-chat")
def new_chat():

    global current_chat_id

    cursor.execute(
        """
        INSERT INTO chats(title)
        VALUES(%s)
        """,
        ("New Chat",)
    )

    conn.commit()

    current_chat_id = cursor.lastrowid

    return {
        "chat_id": current_chat_id
    }

# =========================
# PROCESS PDF
# =========================

@app.post("/api/process")
async def process_pdf(file: UploadFile = File(...)):

    global current_vectorstore
    global current_chain
    global current_chat_id
    global current_pdf_name

    if current_chat_id is None:

        raise HTTPException(
            status_code=400,
            detail="Create chat first"
        )

    if not file.filename.lower().endswith(".pdf"):

        raise HTTPException(
            status_code=400,
            detail="Only PDFs allowed"
        )

    pdf_bytes = await file.read()

    text = extract_text_from_pdf(pdf_bytes)

    if not text.strip():

        raise HTTPException(
            status_code=400,
            detail="No readable text"
        )

    chunks = split_text(text)

    current_vectorstore = build_vectorstore(chunks)

    save_vectorstore(
        current_vectorstore,
        current_chat_id
    )

    current_chain = get_llm()

    current_pdf_name = file.filename

    cursor.execute(
        """
        UPDATE chats
        SET title=%s
        WHERE id=%s
        """,
        (
            current_pdf_name,
            current_chat_id
        )
    )

    conn.commit()

    return {
        "success": True,
        "pdf_name": current_pdf_name,
        "chunks": len(chunks)
    }

# =========================
# LOAD CHAT VECTORSTORE
# =========================

@app.get("/api/load-chat/{chat_id}")
def load_chat(chat_id: int):

    global current_chat_id
    global current_vectorstore
    global current_chain

    current_chat_id = chat_id

    current_vectorstore = load_vectorstore(chat_id)

    if current_vectorstore:
        current_chain = get_llm()

    cursor.execute(
        """
        SELECT *
        FROM chats
        WHERE id=%s
        """,
        (chat_id,)
    )

    chat = cursor.fetchone()

    return {
        "success": True,
        "chat": chat,
        "has_vectorstore": current_vectorstore is not None
    }

# =========================
# ASK QUESTION
# =========================

@app.post("/api/ask")
async def ask_question(payload: QuestionRequest):

    global current_chat_id
    global current_vectorstore
    global current_chain

    if current_chat_id is None:

        raise HTTPException(
            status_code=400,
            detail="No active chat"
        )

    if current_vectorstore is None:

        current_vectorstore = load_vectorstore(
            current_chat_id
        )

    if current_chain is None:
        current_chain = get_llm()

    if current_vectorstore is None:

        raise HTTPException(
            status_code=400,
            detail="Please upload PDF"
        )

    # SAVE USER MESSAGE

    cursor.execute(
        """
        INSERT INTO messages(chat_id, role, content)
        VALUES(%s, %s, %s)
        """,
        (
            current_chat_id,
            "user",
            payload.question
        )
    )

    conn.commit()

    answer = get_answer(
        current_vectorstore,
        payload.question,
        current_chain
    )

    if not answer.strip():

        answer = "Sorry, I could not find the answer."

    # SAVE BOT MESSAGE

    cursor.execute(
        """
        INSERT INTO messages(chat_id, role, content)
        VALUES(%s, %s, %s)
        """,
        (
            current_chat_id,
            "bot",
            answer
        )
    )

    conn.commit()

    return {
        "answer": answer
    }

# =========================
# GET CHATS
# =========================

@app.get("/api/chats")
def get_chats():

    cursor.execute(
        """
        SELECT *
        FROM chats
        ORDER BY created_at DESC
        """
    )

    return cursor.fetchall()

# =========================
# GET CHAT MESSAGES
# =========================

@app.get("/api/chat/{chat_id}")
def get_chat(chat_id: int):

    cursor.execute(
        """
        SELECT *
        FROM messages
        WHERE chat_id=%s
        ORDER BY created_at
        """,
        (chat_id,)
    )

    return cursor.fetchall()

# =========================
# DELETE CHAT
# =========================

@app.delete("/api/chat/{chat_id}")
def delete_chat(chat_id: int):

    global current_chat_id

    cursor.execute(
        """
        DELETE FROM chats
        WHERE id=%s
        """,
        (chat_id,)
    )

    conn.commit()

    vector_path = VECTORSTORE_DIR / f"chat_{chat_id}"

    if vector_path.exists():

        for file in vector_path.iterdir():
            file.unlink()

        vector_path.rmdir()

    if current_chat_id == chat_id:
        current_chat_id = None

    return {
        "success": True
    }

# =========================
# HEALTH
# =========================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }