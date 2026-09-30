from channels.generic.websocket import AsyncWebsocketConsumer
import json
import datetime

class SchedulerStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.run_id = self.scope['url_route']['kwargs']['run_id']
        self.group_name = f"scheduler_{self.run_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def scheduler_status(self, event):
        try:
            await self.send(text_data=json.dumps(event["data"]))
            await self.close()
        except Exception as e:
            print(f"[ERROR] scheduler_status failed: {e}")
