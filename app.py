import os

print("1. Starting app.py...")

import chromadb
print("2. chromadb imported.")

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

print("3. FastAPI imports done.")

from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Settings,
    SimpleDirectoryReader,
)
print("4. LlamaIndex core imported.")

from llama_index.vector_stores.chroma import ChromaVectorStore
print("5. ChromaVectorStore imported.")

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
print("6. HuggingFaceEmbedding imported.")

from llama_index.llms.openrouter import OpenRouter
print("7. OpenRouter imported.")

load_dotenv()
print("8. .env loaded.")

DB_DIR = "storage/chroma"
DATA_DIR = "data"

AVAILABLE_MODELS = {
    "llama": "meta-llama/llama-3.1-8b-instruct",
    "gpt4o-mini": "openai/gpt-4o-mini",
}

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", AVAILABLE_MODELS["llama"])

print("9. Loading embedding model...")
Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5",
    cache_folder="models"
)
print("10. Embedding model loaded.")

print("11. Connecting ChromaDB...")
chroma_client = chromadb.PersistentClient(path=DB_DIR)
chroma_collection = chroma_client.get_or_create_collection("chatbot_docs")
print("12. ChromaDB connected.")

vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

print("13. Loading vector index...")
index = VectorStoreIndex.from_vector_store(
    vector_store,
    storage_context=storage_context
)
print("14. Vector index loaded.")

app = FastAPI()
print("15. FastAPI app created.")


class ChatRequest(BaseModel):
    message: str
    model: str = "llama"


def get_query_engine(model_key: str):
    model_name = AVAILABLE_MODELS.get(model_key, DEFAULT_MODEL)

    llm = OpenRouter(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model=model_name,
    )

    return index.as_query_engine(
        llm=llm,
        similarity_top_k=12,
        response_mode="tree_summarize",
    )


@app.post("/chat")
def chat(req: ChatRequest):
    query_engine = get_query_engine(req.model)
    response = query_engine.query(req.message)
    return {"answer": str(response)}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    allowed = [".pdf", ".txt", ".md", ".png", ".jpg", ".jpeg"]
    filename = file.filename

    if not any(filename.lower().endswith(ext) for ext in allowed):
        return {"error": "Only PDF, TXT, MD, PNG, JPG, JPEG files are allowed."}

    os.makedirs(DATA_DIR, exist_ok=True)

    file_path = os.path.join(DATA_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    documents = SimpleDirectoryReader(input_files=[file_path]).load_data()

    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context
    )

    return {"message": f"{filename} uploaded and indexed successfully."}


app.mount("/", StaticFiles(directory="static", html=True), name="static")

print("16. app.py fully loaded.")