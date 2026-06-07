from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import receipts_ocr_router

app = FastAPI()

origins = [
    "http://localhost:4200"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins = ['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(receipts_ocr_router.router)
