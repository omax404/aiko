"""
AIKO VTS CONNECTOR (RESET)
Handles communication with VTube Studio API.
"""
import asyncio
import json
import os
import logging
from core.utils import async_retry

logger = logging.getLogger("VTS")

try:
    import websockets
except ImportError:
    websockets = None
    print(" [!] VTS Connector requires 'websockets'. Please run: pip install websockets")

VTS_PORT = 8001
PLUGIN_NAME = "Aiko"
DEVELOPER = "AikoDev"

class VTSConnector:
    def __init__(self, port=8001):
        self.port = port
        self.websocket = None
        self.connected = False
        self.token = None
        self.auth_token_path = "vts_token.txt"
        self.load_token()
        
    def load_token(self):
        if os.path.exists(self.auth_token_path):
            try:
                with open(self.auth_token_path, "r") as f:
                    self.token = f.read().strip()
            except IOError as e:
                logger.warning(f"Could not load token: {e}")
                self.token = None
                
    def save_token(self, token):
        self.token = token
        with open(self.auth_token_path, "w") as f:
            f.write(token)
            
    @async_retry(max_attempts=3, backoff_factor=2.0)
    async def _establish_connection(self):
        return await websockets.connect(f"ws://localhost:{self.port}")

    async def connect(self):
        """Connect to VTube Studio."""
        if websockets is None: return False
        
        try:
            self.websocket = await self._establish_connection()
            # Try to authenticate
            auth_success = await self.authenticate()
            if auth_success:
                self.connected = True
                logger.info("Connection Established & Authenticated.")
                return True
            else:
                logger.error("Authentication Failed during Connect.")
                self.connected = False
                await self.close()
                return False
                
        except Exception as e:
            logger.error(f"Connection Failed: {e}")
            self.connected = False
            return False
            
    async def authenticate(self) -> bool:
        """Authenticate with VTS. Returns True if successful."""
        if not self.websocket: return False
        
        # 1. Request Token if missing
        if not self.token:
            print(" [VTS] Requesting Authorization... Please check VTube Studio popup!")
            req = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": "auth-token-req",
                "messageType": "AuthenticationTokenRequest",
                "data": {
                    "pluginName": PLUGIN_NAME,
                    "pluginDeveloper": DEVELOPER,
                }
            }
            await self.websocket.send(json.dumps(req))
            
            try:
                # Wait 130s for user to click Allow
                print(" [VTS] Waiting for User Approval... (130s)")
                resp_str = await asyncio.wait_for(self.websocket.recv(), timeout=130)
                resp = json.loads(resp_str)
                
                if "data" in resp and "authenticationToken" in resp["data"]:
                    self.token = resp["data"]["authenticationToken"]
                    self.save_token(self.token)
                    print(" [VTS] Token Acquired & Saved.")
                else:
                    print(f" [VTS] Authorization Denied: {resp}")
                    return False
            except asyncio.TimeoutError:
                print(" [VTS] Timed out waiting for approval via Popup.")
                return False
                
        # 2. Authenticate Session
        if self.token:
            auth_req = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": "auth-login",
                "messageType": "AuthenticationRequest",
                "data": {
                    "pluginName": PLUGIN_NAME,
                    "pluginDeveloper": DEVELOPER,
                    "authenticationToken": self.token
                }
            }
            await self.websocket.send(json.dumps(auth_req))
            resp = json.loads(await self.websocket.recv())
            if resp.get("data", {}).get("authenticated"):
                print(" [VTS] Authenticated Successfully!")
                return True
            else:
                print(" [VTS] Auth Failed with saved token. Clearing.")
                self.token = None 
                if os.path.exists(self.auth_token_path):
                    os.remove(self.auth_token_path)
                return False
        return False
            
    async def get_hotkeys(self):
        """Get list of available hotkeys."""
        if not self.connected: return []
        req = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "hotkeys-list",
            "messageType": "HotkeysInCurrentModelRequest",
            "data": {}
        }
        try:
            await self.websocket.send(json.dumps(req))
            resp = json.loads(await self.websocket.recv())
            if "data" in resp and "availableHotkeys" in resp["data"]:
                return resp["data"]["availableHotkeys"]
        except Exception as e:
            logger.debug(f"Helpers error: {e}")
        return []

    async def trigger_hotkey(self, hotkey_id: str):
        """Trigger a hotkey by ID."""
        if not self.connected: return
        req = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": f"exec-{hotkey_id}",
            "messageType": "HotkeyTriggerRequest",
            "data": {
                "hotkeyID": hotkey_id
            }
        }
        try:
            await self.websocket.send(json.dumps(req))
        except Exception as e:
            logger.error(f"Hotkey trigger error: {e}")
            self.connected = False
            
    async def set_parameters(self, params: list):
        """
        Set multiple parameters at once.
        params: list of dicts {"id": "ParamName", "value": 0.5}
        """
        if not self.connected: return
        req = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "set-params",
            "messageType": "InjectParameterDataRequest",
            "data": {
                "parameterValues": params
            }
        }
        try:
            await self.websocket.send(json.dumps(req))
        except Exception as e:
            logger.debug(f"Param injection error for {params}: {e}")
            self.connected = False

    async def set_mouth_open(self, value: float):
        """Set MouthOpen parameter (0.0 to 1.0)."""
        await self.set_parameters([{"id": "MouthOpen", "value": value}])

    async def set_expression(self, expression_name: str):
        """Try to trigger a hotkey that matches the expression name."""
        if not self.connected: return
        
        hotkeys = await self.get_hotkeys()
        for hk in hotkeys:
            if expression_name.lower() in hk.get("name", "").lower():
                await self.trigger_hotkey(hk.get("hotkeyID"))
                logger.info(f"Triggered expression hotkey: {hk.get('name')}")
                return
        
        logger.warning(f"No hotkey found for expression: {expression_name}")
            
    async def close(self):
        if self.websocket:
            await self.websocket.close()
