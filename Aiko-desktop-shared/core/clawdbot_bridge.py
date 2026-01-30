
import requests
import json
import logging

logger = logging.getLogger("Clawdbot")

class AikoActionBridge:
    def __init__(self, clawdbot_url="http://localhost:8000/api/v1/webhook/"):
        # The Clawdbot Gateway URL
        self.gateway_url = clawdbot_url

    async def delegate_to_clawdbot(self, task_description):
        """
        Sends a task from Aiko to Clawdbot for autonomous execution.
        """
        payload = {
            "agent": "Aiko",
            "task": task_description,
            "mode": "autonomous" # Ownership shift: Clawdbot owns the task
        }
        
        try:
            # Triggering Clawdbot via its unified API
            # Note: Using requests.post synchronously here since it's usually called from within an async loop 
            # but wrapping it for compatibility is better.
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.post(self.gateway_url, json=payload, timeout=5))
            
            if response.status_code == 200:
                logger.info(f"Delegated task to Clawdbot: {task_description}")
                return f"Task delegated! Clawdbot is now {task_description}."
            
            logger.error(f"Clawdbot Gateway returned {response.status_code}")
            return "I couldn't reach my helper bot (Status Code Error)."
        except Exception as e:
            logger.error(f"Connection error to Clawdbot: {e}")
            return f"Connection error to Clawdbot - {str(e)}"
