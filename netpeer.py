"""
netpeer.py — minimal aiortc wrapper for multiplayer games
----------------------------------------------------------
Hides all WebRTC/signalling boilerplate behind a simple API:

    # Host
    peer = NetPeer(server="http://localhost:8080")
    await peer.host()

    # Joiner
    peer = NetPeer(server="http://localhost:8080")
    await peer.join()

    # Send & receive
    peer.send("move", {"x": 10, "y": 5})

    @peer.on("move")
    def handle_move(data):
        player.x = data["x"]

    await peer.wait()
"""

import asyncio
import json
import logging
from typing import Callable, Any

import aiohttp
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCIceServer,
)

logger = logging.getLogger("netpeer")


# ---------------------------------------------------------------------------
# ICE config — Google STUN for NAT traversal
# ---------------------------------------------------------------------------
DEFAULT_ICE = RTCConfiguration(
    iceServers=[
        RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
    ]
)


class NetPeer:
    """
    One connection to one remote peer.

    Usage
    -----
    peer = NetPeer(server="http://my-signal-server.com")

    await peer.host()   # or await peer.join()

    @peer.on("player_move")
    def on_move(data):
        ...

    peer.send("player_move", {"x": 1, "y": 2})

    await peer.wait()   # blocks until disconnected
    """

    def __init__(self, server: str, ice: RTCConfiguration = DEFAULT_ICE):
        self.server = server.rstrip("/")
        self._pc = RTCPeerConnection(configuration=ice)
        self._channel = None
        self._handlers: dict[str, list[Callable]] = {}
        self._connected = asyncio.Event()
        self._disconnected = asyncio.Event()
        self._queue: asyncio.Queue = asyncio.Queue()

        # Track connection drops
        @self._pc.on("connectionstatechange")
        async def _on_state():
            state = self._pc.connectionState
            logger.info(f"[netpeer] connection → {state}")
            if state == "connected":
                self._connected.set()
            if state in ("failed", "closed", "disconnected"):
                self._disconnected.set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def host(self, poll_interval: float = 1.0):
        """Create offer, post to signal server, wait for answer."""
        self._channel = self._pc.createDataChannel("game", ordered=False)
        self._setup_channel(self._channel)

        offer = await self._pc.createOffer()
        await self._pc.setLocalDescription(offer)
        await self._gather_ice()

        async with aiohttp.ClientSession() as http:
            await http.post(f"{self.server}/offer", json=self._local_sdp())
            logger.info("[netpeer] offer posted — waiting for joiner...")

            while True:
                async with http.get(f"{self.server}/answer") as r:
                    if r.status == 200:
                        answer = await r.json()
                        break
                await asyncio.sleep(poll_interval)

        await self._pc.setRemoteDescription(RTCSessionDescription(**answer))
        await asyncio.wait_for(self._connected.wait(), timeout=15)
        logger.info("[netpeer] connected as host ✅")

    async def join(self, poll_interval: float = 1.0):
        """Fetch offer from signal server, post answer back."""

        @self._pc.on("datachannel")
        def _on_channel(channel):
            self._channel = channel
            self._setup_channel(channel)

        async with aiohttp.ClientSession() as http:
            logger.info("[netpeer] waiting for host offer...")
            while True:
                async with http.get(f"{self.server}/offer") as r:
                    if r.status == 200:
                        offer = await r.json()
                        break
                await asyncio.sleep(poll_interval)

            await self._pc.setRemoteDescription(RTCSessionDescription(**offer))
            answer = await self._pc.createAnswer()
            await self._pc.setLocalDescription(answer)
            await self._gather_ice()

            await http.post(f"{self.server}/answer", json=self._local_sdp())

        await asyncio.wait_for(self._connected.wait(), timeout=15)
        logger.info("[netpeer] connected as joiner ✅")

    def send(self, msg_type: str, data: Any = None):
        """Send a typed message to the remote peer."""
        if self._channel is None or self._channel.readyState != "open":
            logger.warning(f"[netpeer] send({msg_type}) dropped — channel not open")
            return
        self._channel.send(json.dumps({"type": msg_type, "data": data}))

    def on(self, msg_type: str):
        """
        Decorator to register a handler for a message type.

            @peer.on("player_action")
            def handle(data):
                ...
        """

        def decorator(fn: Callable):
            self._handlers.setdefault(msg_type, []).append(fn)
            return fn

        return decorator

    async def wait(self):
        """Block until the connection closes."""
        await self._disconnected.wait()
        await self._pc.close()

    async def close(self):
        """Manually close the connection."""
        self._disconnected.set()
        await self._pc.close()

    @property
    def connected(self) -> bool:
        return self._connected.is_set() and not self._disconnected.is_set()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _setup_channel(self, channel):
        @channel.on("open")
        def _open():
            self._connected.set()
            self._dispatch("_connect", None)

        @channel.on("message")
        def _message(raw: str):
            try:
                msg = json.loads(raw)
                self._dispatch(msg.get("type", "_raw"), msg.get("data"))
            except json.JSONDecodeError:
                self._dispatch("_raw", raw)

        @channel.on("close")
        def _close():
            self._disconnected.set()
            self._dispatch("_disconnect", None)

    def _dispatch(self, msg_type: str, data: Any):
        for fn in self._handlers.get(msg_type, []):
            result = fn(data)
            if asyncio.iscoroutine(result):
                asyncio.ensure_future(result)

    async def _gather_ice(self, timeout: float = 2.0):
        """Wait for ICE candidates to gather."""
        await asyncio.sleep(timeout)

    def _local_sdp(self) -> dict:
        return {
            "sdp": self._pc.localDescription.sdp,
            "type": self._pc.localDescription.type,
        }
