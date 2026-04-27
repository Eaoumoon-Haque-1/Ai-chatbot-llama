import os
import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Settings,
    SimpleDirectoryReader,
)
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openrouter import OpenRouter

# Load Environment Variables
load_dotenv()

DB_DIR = "storage/chroma"
DATA_DIR = "data"

# Available Models
AVAILABLE_MODELS = {
    "llama": "meta-llama/llama-3.1-8b-instruct",
    "gpt4o-mini": "openai/gpt-4o-mini",
}

DEFAULT_MODEL = os.getenv(
    "DEFAULT_MODEL",
    AVAILABLE_MODELS["llama"]
)

# Embedding Model
Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5",
    cache_folder="models"
)

# ChromaDB Setup
os.makedirs(DB_DIR, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=DB_DIR)

chroma_collection = chroma_client.get_or_create_collection(
    "chatbot_docs"
)

vector_store = ChromaVectorStore(
    chroma_collection=chroma_collection
)

storage_context = StorageContext.from_defaults(
    vector_store=vector_store
)

# Load Existing Index
index = VectorStoreIndex.from_vector_store(
    vector_store,
    storage_context=storage_context
)

# FastAPI App
app = FastAPI()

# Request Schema

class ChatRequest(BaseModel):
    message: str
    model: str = "llama"


# Query Engine
def get_query_engine(model_key: str):
    model_name = AVAILABLE_MODELS.get(
        model_key,
        DEFAULT_MODEL
    )

    llm = OpenRouter(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model=model_name,
    )

    return index.as_query_engine(
        llm=llm,
        similarity_top_k=15,
        response_mode="compact",
    )

# Chat Endpoint

@app.post("/chat")
def chat(req: ChatRequest):
    query_engine = get_query_engine(req.model)

    detailed_prompt = f"""
You are a professional AI document assistant.

Use the uploaded document context to answer the user.

Rules:
- Give detailed answers.
- Use headings when helpful.
- Use bullet points when useful.
- Explain clearly.
- Do not answer in only 1 or 2 lines unless necessary.
- If document lacks info, say so honestly.

User Question:
{req.message}
"""

    response = query_engine.query(detailed_prompt)

    return {
        "answer": str(response)
    }

# Upload Endpoint

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    allowed_extensions = [
        ".pdf",
        ".txt",
        ".md",
        ".png",
        ".jpg",
        ".jpeg"
    ]

    filename = file.filename.lower()

    if not any(filename.endswith(ext) for ext in allowed_extensions):
        return {
            "error": "Only PDF, TXT, MD, PNG, JPG, JPEG files are allowed."
        }

    os.makedirs(DATA_DIR, exist_ok=True)

    file_path = os.path.join(
        DATA_DIR,
        file.filename
    )

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Read Document
    documents = SimpleDirectoryReader(
        input_files=[file_path]
    ).load_data()

    # Add to Vector Store
    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context
    )

    return {
        "message": f"{file.filename} uploaded and indexed successfully."
    }

# Serve Frontend

app.mount(
    "/",
    StaticFiles(directory="static", html=True),
    name="static"
)