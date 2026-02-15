from fastapi import FastAPI
from app.api import endpoints
from app.core import config
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title=config.settings.PROJECT_NAME,
    description="RMBG-2.0 Background Removal Service",
    version="1.0.0"
)

app.include_router(endpoints.router)

@app.get("/")
async def root():
    return {
        "message": "RMBG-2.0 Service is Online",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
