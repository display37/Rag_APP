import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.chat import router as chat_router
from api.upload import router as upload_router

from api.chat_management import router as chat_mgmt_router



from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    from db.mysql import engine
    from db.models import Base
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_mgmt_router)
app.include_router(chat_router)
app.include_router(upload_router)


@app.get("/")
def home():
    return {"message": "RAG API running 🚀"}