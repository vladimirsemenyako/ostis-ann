from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from code_search_agent import run_agent

app = FastAPI()


@app.post("/search")
async def search_model(request: str):
    try:
        result = run_agent(request)
        link = result.get("link", "")
        if not link:
            raise HTTPException(status_code=404, detail="Не удалось найти ссылку.")
        return {"link": link}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


