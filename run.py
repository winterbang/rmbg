import uvicorn

if __name__ == "__main__":
    print("Starting RMBG-2.0 Service...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
