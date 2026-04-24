from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routers import collect, data, automation, analytics

app = FastAPI(title="Lead Generation System")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DATABASE
Base.metadata.create_all(bind=engine)

# ROUTERS
app.include_router(collect.router)
app.include_router(data.router)
app.include_router(automation.router)
app.include_router(analytics.router)

# ROOT
@app.get("/")
def root():
    return {"status": "root working"}

# HEALTH
@app.get("/health")
def health():
    return {"status": "ok"}

# TEST
@app.get("/test")
def test():
    return {"message": "API is alive"}