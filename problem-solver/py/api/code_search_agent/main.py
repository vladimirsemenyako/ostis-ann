from fastapi import FastAPI, HTTPException
from code_search_agent import run_agent



app = FastAPI()

@app.post("/search")
async def search_model(request: str = None):
    if not request:
        return {"best_link": ""}
    try:
        result = await run_agent(request)
        if not result:
            raise HTTPException(status_code=404, detail="Не удалось найти ссылку.")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))