# Rag_based_pdf_bot
RAG-Based PDF AI Assistant

An intelligent Retrieval-Augmented Generation (RAG) based PDF chatbot that allows users to upload PDF documents and ask context-aware questions through an interactive chat interface. The system combines semantic search, vector embeddings, and Large Language Models (LLMs) to provide accurate answers directly from uploaded documents.

Features
Upload and process PDF documents
Ask natural language questions based on PDF content
Context-aware answers using Retrieval-Augmented Generation (RAG)
Semantic search using HuggingFace embeddings
Fast vector similarity search using FAISS
Persistent multi-chat support using MySQL
Separate vector storage for each chat session
Interactive frontend with modern glassmorphism-inspired UI
FastAPI backend with REST API architecture
Chat history persistence and retrieval

Project Workflow
1. PDF Upload

The user uploads a PDF document through the frontend interface.

2. Text Extraction

The backend extracts readable text from the PDF using PyMuPDF (fitz).

3. Text Chunking

Large text is split into smaller chunks using LangChain's RecursiveCharacterTextSplitter to improve retrieval efficiency.

4. Embedding Generation

Each chunk is converted into vector embeddings using HuggingFace's MiniLM embedding model.

5. Vector Storage

The embeddings are stored locally using FAISS for efficient similarity search.

6. Question Answering

When the user asks a question:

The question is converted into an embedding
Relevant chunks are retrieved from FAISS
Retrieved context is sent to Groq’s LLaMA 3.1 model
The model generates a context-aware response
7. Chat Persistence

All chats and messages are stored in MySQL for session continuity.
