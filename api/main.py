from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, stories, review, pipeline

app = FastAPI(
    title="The Lost Archives API",
    version="2.0",
    description="Pipeline automatizado de geração de vídeos de história para YouTube.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(stories.router)
app.include_router(review.router)
app.include_router(pipeline.router)
