"""
match_maker.py — minimal signalling server
Stores the offer, hands it to whoever joins, stores the answer back.
No matchmaking, no queues, just one room at a time.

Run:
    python match_maker.py
"""

from aiohttp import web

room = {}  # holds {"offer": ..., "answer": ...}


async def post_offer(req):
    room["offer"] = await req.json()
    room.pop("answer", None)  # reset answer for new session
    return web.json_response({"ok": True})


async def get_offer(req):
    if "offer" not in room:
        return web.json_response({"error": "no offer yet"}, status=404)
    return web.json_response(room["offer"])


async def post_answer(req):
    room["answer"] = await req.json()
    return web.json_response({"ok": True})


async def get_answer(req):
    if "answer" not in room:
        return web.json_response({"error": "no answer yet"}, status=404)
    return web.json_response(room["answer"])


app = web.Application()
app.router.add_post("/offer", post_offer)
app.router.add_get("/offer", get_offer)
app.router.add_post("/answer", post_answer)
app.router.add_get("/answer", get_answer)

if __name__ == "__main__":
    print("Signalling server running on http://localhost:8080")
    web.run_app(app, port=8080)
