from round import Round
from netpeer import NetPeer
from sys import argv
from asyncio import ensure_future, run


async def main(server, role):
    peer = NetPeer(server)

    @peer.on("_connect")
    def on_connect(_):
        print("Connected! Sending greeting...")
        peer.send("message", {"msg": "Hello, world!", "from": role})

    @peer.on("message")
    def on_message(data):
        print(f"Message from {data['from']}: {data['msg']}")

    @peer.on("_disconnect")
    def on_disconnect(_):
        print("Peer disconnected")

    if role == "host":
        print("Hosting... run: python main.py join")
        await peer.host()
    else:
        print("Joining...")
        await peer.join()

    await peer.wait()


if __name__ == "__main__":
    match_maker_server = "http://localhost:8080"
    role = argv[1] if len(argv) > 1 else "host"
    run(main(match_maker_server, role))
