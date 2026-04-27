import asyncio
import json
import time

try:
    import websockets
except ImportError:
    websockets = None


def execute(self, input_data):
    ws_port = self.config.get("ws_port", 8765)
    timeout_seconds = self.config.get("timeout_seconds", 60)
    collect_types_str = self.config.get("collect_types", "page_info,network,console")
    max_messages = self.config.get("max_messages", 100)
    output_var = self.config.get("output_var", "collected_data")

    collect_types = [t.strip() for t in collect_types_str.split(",") if t.strip()]

    if websockets is None:
        return {
            **input_data,
            output_var: {
                "status": "error",
                "error": "websockets 库未安装，请先安装: pip install websockets"
            }
        }

    collected_data = []
    connection_info = {"ws_port": ws_port, "connected_clients": 0}

    async def run_server():
        nonlocal collected_data

        async def handler(websocket):
            connection_info["connected_clients"] += 1
            config_msg = json.dumps({
                "type": "config",
                "collect_types": collect_types,
                "max_messages": max_messages
            })
            try:
                await websocket.send(config_msg)
            except Exception:
                pass

            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        data = {"type": "raw", "payload": message}

                    if data.get("type") == "data":
                        collect_type = data.get("collect_type", "unknown")
                        if not collect_types or collect_type in collect_types:
                            collected_data.append(data)
                            if len(collected_data) >= max_messages:
                                break
                    elif data.get("type") == "ping":
                        try:
                            await websocket.send(json.dumps({"type": "pong"}))
                        except Exception:
                            pass
                    elif data.get("type") == "done":
                        break

                    if len(collected_data) >= max_messages:
                        break
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                connection_info["connected_clients"] -= 1

        try:
            async with websockets.serve(handler, "0.0.0.0", ws_port):
                deadline = time.time() + timeout_seconds
                while time.time() < deadline and len(collected_data) < max_messages:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        break
                    await asyncio.sleep(min(0.5, remaining))
        except OSError as e:
            connection_info["error"] = str(e)

    try:
        asyncio.run(run_server())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run_server())
        finally:
            loop.close()

    result = {
        "status": "completed",
        "total_collected": len(collected_data),
        "connection_info": connection_info,
        "collect_types": collect_types,
        "items": collected_data
    }

    return {**input_data, output_var: result}
