# KnowEdge Merger Android Bridge — WebSocket Relay
# Relay for Android telemetry and control to primary stack

import asyncio
import websockets
import json
import hashlib
import secrets
import os
import socket
import logging

# Security: Generated at startup
PIN = str(secrets.randbelow(900000) + 100000)
VERIFIED_CLIENTS = set()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("android-bridge")

def get_lan_ip():
    """Attempts to find the local network IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Port doesn't need to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

async def handle_client(websocket):
    """Handles verification and message relay."""
    try:
        # 1. Verification Phase
        auth_msg = await websocket.recv()
        data = json.loads(auth_msg)
        
        if data.get("pin") == PIN:
            VERIFIED_CLIENTS.add(websocket)
            logger.info(f"Verified client connected from {websocket.remote_address}")
            await websocket.send(json.dumps({"status": "verified", "message": "Connection established"}))
        else:
            logger.warning(f"Failed verification attempt from {websocket.remote_address}")
            await websocket.send(json.dumps({"status": "denied", "message": "Invalid PIN"}))
            await websocket.close()
            return

        # 2. Main Relay Loop
        async for message in websocket:
            # Here we relay to the local backend if needed
            # For this bridge, we treat messages as telemetry or control commands
            logger.info(f"Bridge received: {message}")
            
            # Broadcast telemetry to all verified connections if it matches a specific type
            if "telemetry" in message:
                await broadcast_telemetry(message)

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client {websocket.remote_address} disconnected")
    finally:
        VERIFIED_CLIENTS.discard(websocket)

async def broadcast_telemetry(data):
    """Broadcasts data to all connected verified clients."""
    if VERIFIED_CLIENTS:
        message = json.dumps({"type": "telemetry", "payload": data})
        await asyncio.wait([ws.send(message) for ws in VERIFIED_CLIENTS])

async def main():
    lan_ip = get_lan_ip()
    port = 3001
    
    print("\n" + "="*50)
    print("KnowEdge Merger Android Bridge — ONLINE")
    print(f"Network IP: {lan_ip}")
    print(f"Port:       {port}")
    print(f"Access PIN: {PIN}")
    print("="*50 + "\n")
    
    async with websockets.serve(handle_client, "0.0.0.0", port):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bridge shutting down...")
