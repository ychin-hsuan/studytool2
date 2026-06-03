import os
import json
import base64
import asyncio
from pathlib import Path

import fitz  # PyMuPDF
import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="PDF Quiz Solver")

SYSTEM_PROMPT = """你是一位專業的解題老師。
使用者會提供一份包含多道題目的考卷（可能是文字或手寫圖片）。請：
1. 找出所有題目（包括選擇題、填充題、問答題、計算題等）
2. 依序為每道題目提供詳細的正確解答與解題說明
3. 格式使用：【第X題】題目內容 → 解答：...（附解析）
4. 若題目有選項，請明確指出正確選項並說明原因
5. 使用繁體中文回答
6. 解析要清楚易懂，適合學生理解"""


def resolve_api_key(request: Request) -> str:
    """Header X-API-Key takes priority over env var."""
    return request.headers.get("X-API-Key", "").strip() or os.getenv("ANTHROPIC_API_KEY", "")


def extract_text_from_pdf(pdf_bytes: bytes) -> tuple[str, int]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n\n".join(pages), page_count


def pdf_to_images(pdf_bytes: bytes) -> list[str]:
    """Render each PDF page at 2× scale → PNG → base64."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    mat = fitz.Matrix(2, 2)  # 144 DPI — good for handwriting
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        images.append(base64.b64encode(pix.tobytes()).decode())
    doc.close()
    return images


async def stream_answers(pdf_text: str = "", images: list[str] | None = None, api_key: str = ""):
    if not api_key:
        yield f"data: {json.dumps({'error': '請先在右上角 ⚙ 設定 API Key，或設定 ANTHROPIC_API_KEY 環境變數'})}\n\n"
        return

    client = anthropic.Anthropic(api_key=api_key)

    if images:
        content: list = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img}}
            for img in images
        ]
        content.append({
            "type": "text",
            "text": "以上是考卷圖片（可能含有手寫內容、圖表或數學式），請找出所有題目並依序提供正確解答。",
        })
    else:
        content = f"以下是 PDF 考卷的內容，請幫我解答所有題目：\n\n{pdf_text}"

    try:
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        ) as stream:
            for text in stream.text_stream:
                payload = json.dumps({"text": text}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0)

        yield f"data: {json.dumps({'done': True})}\n\n"

    except anthropic.AuthenticationError:
        yield f"data: {json.dumps({'error': 'API Key 無效，請在 ⚙ 設定中確認'})}\n\n"
    except anthropic.RateLimitError:
        yield f"data: {json.dumps({'error': '已超過 API 使用限制，請稍後再試'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': f'發生錯誤：{str(e)}'})}\n\n"


async def stream_chat(context: str, follow_up: str, api_key: str = ""):
    if not api_key:
        yield f"data: {json.dumps({'error': '請先在右上角 ⚙ 設定 API Key'})}\n\n"
        return

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = """你是一位耐心的老師，正在幫學生理解一道題目的解答。
請根據提供的題目與解答，用清楚易懂的方式回應學生的問題。
使用繁體中文，說明要精簡有力，適時舉例輔助理解。"""

    user_message = f"題目與解答如下：\n\n{context}\n\n---\n\n學生追問：{follow_up}"

    try:
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                payload = json.dumps({"text": text}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0)

        yield f"data: {json.dumps({'done': True})}\n\n"

    except anthropic.AuthenticationError:
        yield f"data: {json.dumps({'error': 'API Key 無效，請在 ⚙ 設定中確認'})}\n\n"
    except anthropic.RateLimitError:
        yield f"data: {json.dumps({'error': '已超過 API 使用限制，請稍後再試'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': f'發生錯誤：{str(e)}'})}\n\n"


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = Path(__file__).parent / "templates" / "index.html"
    return html_path.read_text(encoding="utf-8")


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只接受 PDF 檔案")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="檔案大小不能超過 20MB")

    try:
        text, page_count = extract_text_from_pdf(content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"無法解析 PDF：{str(e)}")

    # Scanned / image-based PDF: fewer than 30 chars/page → use Vision OCR
    if len(text.strip()) / max(page_count, 1) < 30:
        try:
            images = pdf_to_images(content)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"無法轉換 PDF 頁面為圖片：{str(e)}")
        return {"images": images, "pages": page_count, "mode": "ocr"}

    return {"text": text, "pages": page_count, "mode": "text"}


class SolveRequest(BaseModel):
    text: str = ""
    images: list[str] = []


class ChatRequest(BaseModel):
    context: str
    follow_up: str


@app.post("/chat")
async def chat(req: ChatRequest, request: Request):
    if not req.follow_up.strip():
        raise HTTPException(status_code=400, detail="問題不可為空")
    return StreamingResponse(
        stream_chat(req.context, req.follow_up, api_key=resolve_api_key(request)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/solve")
async def solve(req: SolveRequest, request: Request):
    if not req.text.strip() and not req.images:
        raise HTTPException(status_code=400, detail="題目內容不可為空")
    return StreamingResponse(
        stream_answers(req.text, req.images or None, api_key=resolve_api_key(request)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
