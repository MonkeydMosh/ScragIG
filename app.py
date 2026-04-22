"""
app.py
------
Backend FastAPI para el scraper de Instagram.
Expone endpoints REST + SSE (Server-Sent Events) para streaming en tiempo real.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import asyncio
from pathlib import Path
from instagram import IGClient, AuthError, RateLimitError

app = FastAPI(title="IG Scraper", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── helpers ─────────────────────────────────────────────────────────────────

def make_client(session_id: str, csrf_token: str) -> IGClient:
    if not session_id or not csrf_token:
        raise HTTPException(400, "Faltan cookies: session_id y csrf_token son requeridos")
    return IGClient(session_id, csrf_token)


def sse_event(kind: str, payload) -> str:
    return f"data: {json.dumps({'type': kind, 'data': payload})}\n\n"


# ─── models ──────────────────────────────────────────────────────────────────

class CookieParams(BaseModel):
    session_id: str
    csrf_token: str


# ─── root ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    html = Path("templates/index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


# ─── profile ─────────────────────────────────────────────────────────────────

@app.get("/api/profile")
async def get_profile(
    username:   str = Query(...),
    session_id: str = Query(...),
    csrf_token: str = Query(...),
):
    client = make_client(session_id, csrf_token)
    try:
        uid = client.resolve_username(username)
        if not uid:
            raise HTTPException(404, f"Usuario @{username} no encontrado")
        profile = client.get_profile(uid)
        return {"ok": True, "profile": profile}
    except AuthError as e:
        raise HTTPException(401, str(e))
    except RateLimitError as e:
        raise HTTPException(429, str(e))


# ─── following / followers (SSE) ─────────────────────────────────────────────

@app.get("/api/stream/following")
async def stream_following(
    user_id:    str = Query(...),
    session_id: str = Query(...),
    csrf_token: str = Query(...),
    limit:      int = Query(50),
):
    async def generate():
        client = make_client(session_id, csrf_token)
        try:
            count = 0
            for user in client.iter_following(user_id, limit=limit):
                yield sse_event("item", user)
                count += 1
                await asyncio.sleep(0)          # cede el event loop
            yield sse_event("done", {"total": count})
        except AuthError as e:
            yield sse_event("error", {"message": str(e)})
        except RateLimitError as e:
            yield sse_event("error", {"message": str(e)})
        except Exception as e:
            yield sse_event("error", {"message": str(e)})

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/stream/followers")
async def stream_followers(
    user_id:    str = Query(...),
    session_id: str = Query(...),
    csrf_token: str = Query(...),
    limit:      int = Query(50),
):
    async def generate():
        client = make_client(session_id, csrf_token)
        try:
            count = 0
            for user in client.iter_followers(user_id, limit=limit):
                yield sse_event("item", user)
                count += 1
                await asyncio.sleep(0)
            yield sse_event("done", {"total": count})
        except AuthError as e:
            yield sse_event("error", {"message": str(e)})
        except RateLimitError as e:
            yield sse_event("error", {"message": str(e)})
        except Exception as e:
            yield sse_event("error", {"message": str(e)})

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ─── posts (SSE) ─────────────────────────────────────────────────────────────

@app.get("/api/stream/posts")
async def stream_posts(
    user_id:    str = Query(...),
    session_id: str = Query(...),
    csrf_token: str = Query(...),
    limit:      int = Query(12),
):
    async def generate():
        client = make_client(session_id, csrf_token)
        try:
            count = 0
            for post in client.iter_posts(user_id, limit=limit):
                yield sse_event("item", post)
                count += 1
                await asyncio.sleep(0)
            yield sse_event("done", {"total": count})
        except AuthError as e:
            yield sse_event("error", {"message": str(e)})
        except RateLimitError as e:
            yield sse_event("error", {"message": str(e)})
        except Exception as e:
            yield sse_event("error", {"message": str(e)})

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ─── comments (SSE) ──────────────────────────────────────────────────────────

@app.get("/api/stream/comments")
async def stream_comments(
    media_id:   str = Query(...),
    session_id: str = Query(...),
    csrf_token: str = Query(...),
    limit:      int = Query(50),
):
    async def generate():
        client = make_client(session_id, csrf_token)
        try:
            count = 0
            for comment in client.iter_comments(media_id, limit=limit):
                yield sse_event("item", comment)
                count += 1
                await asyncio.sleep(0)
            yield sse_event("done", {"total": count})
        except AuthError as e:
            yield sse_event("error", {"message": str(e)})
        except RateLimitError as e:
            yield sse_event("error", {"message": str(e)})
        except Exception as e:
            yield sse_event("error", {"message": str(e)})

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ─── likers ──────────────────────────────────────────────────────────────────

@app.get("/api/likers")
async def get_likers(
    media_id:   str = Query(...),
    session_id: str = Query(...),
    csrf_token: str = Query(...),
):
    client = make_client(session_id, csrf_token)
    try:
        likers = list(client.iter_likers(media_id))
        return {"ok": True, "likers": likers, "total": len(likers)}
    except AuthError as e:
        raise HTTPException(401, str(e))
    except RateLimitError as e:
        raise HTTPException(429, str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
