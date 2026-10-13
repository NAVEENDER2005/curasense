from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ai.chat import answer_question
from app.analytics import compute_summary, flatten_for_chat
from app.dependencies import get_pool

router = APIRouter(prefix="/chat", tags=["chat"])


class AskRequest(BaseModel):
    question: str


@router.post("/ask")
async def ask(body: AskRequest, pool=Depends(get_pool)):
    summary = await compute_summary(pool)
    context = flatten_for_chat(summary)
    answer = answer_question(body.question, context)
    return {"answer": answer, "context_used": context}
