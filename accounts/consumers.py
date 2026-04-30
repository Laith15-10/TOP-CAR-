import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class OrderConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for tracking order updates.
    Only the order owner (customer) and the assigned driver may connect.
    """

    async def connect(self):
        self.order_id = self.scope['url_route']['kwargs']['order_id']
        self.room_group_name = f'order_{self.order_id}'

        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        authorized = await self.check_order_authorization(user, self.order_id)
        if not authorized:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def order_update(self, event):
        await self.send(text_data=json.dumps(event['data']))

    async def driver_location(self, event):
        await self.send(text_data=json.dumps(event['data']))

    @database_sync_to_async
    def check_order_authorization(self, user, order_id):
        from .models import ServiceOrder
        try:
            order = ServiceOrder.objects.select_related('customer', 'driver_assigned__user').get(pk=order_id)
            if user.is_staff:
                return True
            if order.customer_id and order.customer_id == user.pk:
                return True
            if order.driver_assigned and order.driver_assigned.user_id == user.pk:
                return True
            return False
        except ServiceOrder.DoesNotExist:
            return False


class DriverConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for drivers receiving orders and sending location.
    Only the authenticated driver who owns the driver_id record may connect.
    """

    async def connect(self):
        self.driver_id = self.scope['url_route']['kwargs']['driver_id']
        self.room_group_name = f'driver_{self.driver_id}'

        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        authorized = await self.check_driver_authorization(user, self.driver_id)
        if not authorized:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.set_driver_online(True)

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            await self.set_driver_online(False)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')

        if msg_type == 'location_update':
            lat = data.get('lat')
            lon = data.get('lon')
            order_id = data.get('order_id')
            if lat is not None and lon is not None:
                await self.update_driver_location(lat, lon)
            if order_id:
                # Verify the order is actually assigned to this driver before broadcasting
                if await self.verify_order_driver(order_id):
                    await self.channel_layer.group_send(
                        f'order_{order_id}',
                        {
                            'type': 'driver_location',
                            'data': {'type': 'driver_location', 'lat': lat, 'lon': lon},
                        }
                    )

    async def new_order(self, event):
        await self.send(text_data=json.dumps(event['data']))

    @database_sync_to_async
    def check_driver_authorization(self, user, driver_id):
        from .models import Driver
        if user.is_staff:
            return True
        return Driver.objects.filter(pk=driver_id, user=user).exists()

    @database_sync_to_async
    def verify_order_driver(self, order_id):
        from .models import ServiceOrder
        return ServiceOrder.objects.filter(pk=order_id, driver_assigned__pk=self.driver_id).exists()

    @database_sync_to_async
    def set_driver_online(self, online):
        from .models import Driver
        try:
            driver = Driver.objects.get(pk=self.driver_id)
            driver.is_active = online
            driver.save(update_fields=['is_active'])
        except Driver.DoesNotExist:
            pass

    @database_sync_to_async
    def update_driver_location(self, lat, lon):
        from .models import Driver
        try:
            driver = Driver.objects.get(pk=self.driver_id)
            driver.lat = lat
            driver.lon = lon
            driver.save(update_fields=['lat', 'lon'])
        except Driver.DoesNotExist:
            pass
