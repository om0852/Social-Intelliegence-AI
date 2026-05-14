from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from core.orchestrator import run_social_intelligence_pipeline
import uvicorn
import logging
import asyncio
import sys

# Windows-specific: Force ProactorEventLoop for Playwright subprocess support
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Social Intelligence AI Engine")

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    logger.info(f"Startup: Using event loop: {loop.__class__.__name__}")

class ExtractRequest(BaseModel):
    url: str

@app.get("/")
def read_root():
    return {"message": "Social Intelligence AI API is online."}

@app.post("/extract")
async def extract_intelligence(request: ExtractRequest):
    """
    Triggers the 4-Phase Social Intelligence Pipeline for a non-login URL.
    """
    logger.info(f"Received extraction request for: {request.url}")
    result = await run_social_intelligence_pipeline(request.url)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown pipeline error"))
    
    return result

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True, loop="asyncio")
