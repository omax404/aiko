
import asyncio
from flask import Flask, request, jsonify
import threading
import logging

logger = logging.getLogger("ReturnHook")

class AikoCallbackServer:
    def __init__(self, port=8002, callback_handler=None, loop=None):
        self.port = port
        self.callback_handler = callback_handler
        self.loop = loop or asyncio.get_event_loop()
        self.app = Flask(__name__)
        self._setup_routes()
        self.thread = None

    def _setup_routes(self):
        @self.app.route('/clawdbot_callback', methods=['POST'])
        def clawdbot_callback():
            data = request.json or {}
            logger.info(f"Received callback from Clawdbot: {data}")
            
            if self.callback_handler:
                message = data.get("message", "Task completed!")
                status = data.get("status", "success")
                task = data.get("task", "Unknown Task")
                
                asyncio.run_coroutine_threadsafe(
                    self.callback_handler(task, message, status),
                    self.loop
                )
                
            return jsonify({"status": "received"}), 200

    def start(self):
        self.thread = threading.Thread(target=lambda: self.app.run(port=self.port, debug=False, use_reloader=False), daemon=True)
        self.thread.start()
        logger.info(f"Callback server started on port {self.port}")
