"""
面试官模式 API —— 主动提问 + 碎片拼图的背题流程。

接口：
    GET  /interview/topics   - 主题列表（含题数）
    GET  /interview/quiz     - 抽题（随机 / 指定 qids 错题重练）
    POST /interview/opening  - 开场白（SSE）
    POST /interview/review   - 逐题点评（SSE）
    POST /interview/report   - 场次报告（SSE）

设计：场次状态全部在前端，端点无状态；点评/报告只接收 qid 与
用户产出（作答文本、拼图数值），题目与标准答案一律由服务端从题库
自查——不信任客户端回传的标准内容，同时防 prompt 注入与篡改。
"""
import json
import random

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from apps.api.schemas import (
    TopicListResponse, TopicItem, QuizResponse, QuizQuestion,
    OpeningRequest, ReviewRequest, ReportRequest,
)
from apps.core.services import interviewer_service, question_bank

router = APIRouter()

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _sse(generator):
    """把逐 token 生成器包装成 SSE 流（帧格式与 /qa/stream 完全一致）"""
    def generate():
        try:
            for chunk in generator:
                yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    return StreamingResponse(
        generate(), media_type="text/event-stream", headers=_SSE_HEADERS)


@router.get("/topics", response_model=TopicListResponse, summary="题库主题列表")
def list_topics():
    return TopicListResponse(
        topics=[TopicItem(**t) for t in question_bank.topics()])


@router.get("/quiz", response_model=QuizResponse, summary="抽题（随机或错题重练）")
def get_quiz(topic: str = "", count: int = 5, qids: str = ""):
    """qids 优先（逗号分隔，错题重练）；否则按主题随机抽 count 题"""
    if qids:
        items = []
        for qid in (q.strip() for q in qids.split(",") if q.strip()):
            item = question_bank.get(qid)
            if item is None:
                raise HTTPException(status_code=404, detail=f"题目不存在: {qid}")
            items.append(item)
        return QuizResponse(questions=[QuizQuestion(**i) for i in items])

    items = question_bank.questions(topic)
    if not items:
        raise HTTPException(status_code=404, detail=f"主题不存在或没有题目: {topic}")
    if not 1 <= count <= len(items):
        raise HTTPException(status_code=400, detail=f"count 需在 1~{len(items)} 之间")
    return QuizResponse(
        questions=[QuizQuestion(**i) for i in random.sample(items, count)])


@router.post("/opening", summary="面试开场白（SSE）")
def opening(request: OpeningRequest):
    mode_desc = ("先自由作答再拼图对答案" if request.mode == "practice"
                 else "直接碎片拼图速记")
    return _sse(interviewer_service.stream("opening", {
        "topic": request.topic,
        "count": request.count,
        "mode_desc": mode_desc,
    }))


@router.post("/review", summary="逐题点评（SSE）")
def review(request: ReviewRequest):
    item = question_bank.get(request.qid)
    if item is None:
        raise HTTPException(status_code=404, detail=f"题目不存在: {request.qid}")

    puzzle = request.puzzle
    if puzzle.correct > puzzle.total:
        raise HTTPException(status_code=400, detail="correct 不能大于 total")
    if puzzle.gave_up:
        puzzle_desc = "候选人选择放弃并直接查看了标准答案"
    else:
        pct = round(puzzle.correct / puzzle.total * 100)
        puzzle_desc = f"碎片排序 {puzzle.correct}/{puzzle.total} 片位置正确（{pct}%）"

    user_answer = (request.user_answer or "").strip() or "（本题跳过了自由作答）"

    return _sse(interviewer_service.stream("review", {
        "question": item["question"],
        "points": "\n".join(f"- {s['text']}" for s in item["sentences"]),
        "puzzle_desc": puzzle_desc,
        "user_answer": user_answer,
    }))


@router.post("/report", summary="场次报告（SSE）")
def report(request: ReportRequest):
    if not request.results:
        raise HTTPException(status_code=400, detail="results 不能为空")

    lines = []
    total = 0.0
    for r in request.results:
        item = question_bank.get(r.qid)
        if item is None:
            raise HTTPException(status_code=404, detail=f"题目不存在: {r.qid}")
        if r.skipped:
            desc = "跳过（不计分）"
        elif r.gave_up:
            desc = "放弃看答案（0 分）"
        else:
            desc = f"{int(round(r.score * 100))} 分"
        total += r.score
        lines.append(f"- {item['question']}：{desc}")

    avg = total / len(request.results)
    mode_desc = ("练习模式（先答后拼）" if request.mode == "practice"
                 else "速记模式（直接拼图）")
    return _sse(interviewer_service.stream("report", {
        "topic": request.topic,
        "mode_desc": mode_desc,
        "score_desc": f"平均 {int(round(avg * 100))} 分（满分 100）",
        "items": "\n".join(lines),
    }))
