# Copyright 2026 Sébastien Demanou. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import asyncio
import logging
from collections.abc import Coroutine
from collections.abc import Mapping
from typing import cast
from typing import Protocol
from urllib.parse import unquote

from dbus_next import Message
from dbus_next.aio import MessageBus
from dbus_next.proxy_object import BaseProxyInterface
from dbus_next.signature import Variant

from bluegate.bluetooth.agent import AGENT_PATH
from bluegate.bluetooth.agent import PairingAgent
from bluegate.bluetooth.bus import SystemBusClient
from bluegate.bluetooth.events import BluetoothEventBroker
from bluegate.models.adapter import Adapter
from bluegate.models.adapter import AdapterPatch
from bluegate.models.device import Device
from bluegate.models.events import AdapterChangedEvent
from bluegate.models.events import CharacteristicChangedEvent
from bluegate.models.events import DeviceChangedEvent
from bluegate.models.events import DeviceRemovedEvent
from bluegate.models.gatt import GattCharacteristic
from bluegate.models.gatt import GattDescriptor
from bluegate.models.gatt import GattService

logger = logging.getLogger(__name__)

BLUEZ_SERVICE = "org.bluez"
OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
ADAPTER_IFACE = "org.bluez.Adapter1"
DEVICE_IFACE = "org.bluez.Device1"
GATT_SERVICE_IFACE = "org.bluez.GattService1"
GATT_CHARACTERISTIC_IFACE = "org.bluez.GattCharacteristic1"
GATT_DESCRIPTOR_IFACE = "org.bluez.GattDescriptor1"
AGENT_MANAGER_PATH = "/org/bluez"
AGENT_MANAGER_IFACE = "org.bluez.AgentManager1"


class BluetoothManager(Protocol):
  async def initialize(self) -> None: ...

  async def shutdown(self) -> None: ...

  @property
  def dbus_connected(self) -> bool: ...

  @property
  def bluez_available(self) -> bool: ...

  async def list_adapters(self) -> list[Adapter]: ...

  async def get_adapter(self, adapter_id: str) -> Adapter | None: ...

  async def patch_adapter(self, adapter_id: str, patch: AdapterPatch) -> Adapter | None: ...

  async def start_discovery(self, adapter_id: str) -> bool: ...

  async def stop_discovery(self, adapter_id: str) -> bool: ...

  async def list_devices(self) -> list[Device]: ...

  async def get_device(self, device_id: str) -> Device | None: ...

  async def pair_device(self, device_id: str) -> bool: ...

  async def connect_device(self, device_id: str) -> bool: ...

  async def disconnect_device(self, device_id: str) -> bool: ...

  async def trust_device(self, device_id: str, trusted: bool) -> bool: ...

  async def remove_device(self, device_id: str) -> bool: ...

  async def list_services(self, device_id: str) -> list[GattService]: ...

  async def get_service(self, device_id: str, service_id: str) -> GattService | None: ...

  async def list_characteristics(self, device_id: str, service_id: str) -> list[GattCharacteristic]: ...

  async def get_characteristic(self, device_id: str, service_id: str, characteristic_id: str) -> GattCharacteristic | None: ...

  async def read_characteristic(self, device_id: str, service_id: str, characteristic_id: str) -> GattCharacteristic | None: ...

  async def write_characteristic(
    self, device_id: str, service_id: str, characteristic_id: str, value: bytes
  ) -> GattCharacteristic | None: ...

  async def start_notify(self, device_id: str, service_id: str, characteristic_id: str) -> GattCharacteristic | None: ...

  async def stop_notify(self, device_id: str, service_id: str, characteristic_id: str) -> GattCharacteristic | None: ...

  async def list_descriptors(self, device_id: str, service_id: str, characteristic_id: str) -> list[GattDescriptor]: ...

  async def get_descriptor(
    self, device_id: str, service_id: str, characteristic_id: str, descriptor_id: str
  ) -> GattDescriptor | None: ...

  async def read_descriptor(
    self, device_id: str, service_id: str, characteristic_id: str, descriptor_id: str
  ) -> GattDescriptor | None: ...

  async def write_descriptor(
    self, device_id: str, service_id: str, characteristic_id: str, descriptor_id: str, value: bytes
  ) -> GattDescriptor | None: ...


class BlueZManager:
  def __init__(
    self,
    bus_client: SystemBusClient,
    event_broker: BluetoothEventBroker | None = None,
    agent_capability: str = "DisplayYesNo",
  ) -> None:
    self._bus_client = bus_client
    self._event_broker = event_broker
    self._agent_capability = agent_capability
    self._bus: MessageBus | None = None
    self._bluez_available = False
    self._signal_matches: list[str] = []
    self._background_tasks: set[asyncio.Task[None]] = set()
    self._pairing_agent: PairingAgent | None = None

  async def initialize(self) -> None:
    try:
      self._bus = await self._bus_client.connect()
      await self._get_managed_objects()
      self._bluez_available = True
      await self._subscribe_to_signals()
      await self._register_agent()
      logger.info("Connected to D-Bus system bus and BlueZ")
    except Exception as exc:
      self._bluez_available = False
      logger.warning("BlueZ initialization failed: %s", exc)

  async def shutdown(self) -> None:
    await self._unregister_agent()
    await self._unsubscribe_from_signals()
    await self._bus_client.disconnect()
    self._bus = None
    self._bluez_available = False

  @property
  def dbus_connected(self) -> bool:
    return self._bus_client.connected

  @property
  def bluez_available(self) -> bool:
    return self._bluez_available

  @property
  def pairing_agent(self) -> PairingAgent | None:
    return self._pairing_agent

  async def list_adapters(self) -> list[Adapter]:
    managed = await self._get_managed_objects()
    devices_per_adapter = self._count_devices_by_adapter(managed)

    adapters: list[Adapter] = []
    for path, ifaces in managed.items():
      props = ifaces.get(ADAPTER_IFACE)
      if props is None:
        continue

      adapter_id = path.rsplit("/", 1)[-1]
      adapters.append(
        Adapter(
          id=adapter_id,
          object_path=path,
          name=self._as_str(props.get("Name")),
          alias=self._as_str(props.get("Alias")),
          address=self._as_str(props.get("Address")),
          powered=self._as_bool(props.get("Powered")),
          discoverable=self._as_bool(props.get("Discoverable")),
          pairable=self._as_bool(props.get("Pairable")),
          discovering=self._as_bool(props.get("Discovering")),
          device_count=devices_per_adapter.get(adapter_id, 0),
        )
      )

    adapters.sort(key=lambda item: item.id)
    return adapters

  async def get_adapter(self, adapter_id: str) -> Adapter | None:
    for adapter in await self.list_adapters():
      if adapter.id == adapter_id:
        return adapter

    return None

  async def patch_adapter(self, adapter_id: str, patch: AdapterPatch) -> Adapter | None:
    adapter = await self.get_adapter(adapter_id)
    if adapter is None:
      return None

    properties = await self._get_properties_interface(adapter.object_path)

    if patch.powered is not None:
      await properties.call_set(ADAPTER_IFACE, "Powered", Variant("b", patch.powered))

    if patch.discoverable is not None:
      await properties.call_set(ADAPTER_IFACE, "Discoverable", Variant("b", patch.discoverable))

    if patch.pairable is not None:
      await properties.call_set(ADAPTER_IFACE, "Pairable", Variant("b", patch.pairable))

    return await self.get_adapter(adapter_id)

  async def start_discovery(self, adapter_id: str) -> bool:
    adapter = await self.get_adapter(adapter_id)
    if adapter is None:
      return False

    iface = await self._get_interface(adapter.object_path, ADAPTER_IFACE)
    await iface.call_start_discovery()
    return True

  async def stop_discovery(self, adapter_id: str) -> bool:
    adapter = await self.get_adapter(adapter_id)
    if adapter is None:
      return False

    iface = await self._get_interface(adapter.object_path, ADAPTER_IFACE)
    await iface.call_stop_discovery()
    return True

  async def list_devices(self) -> list[Device]:
    managed = await self._get_managed_objects()
    devices: list[Device] = []

    for path, ifaces in managed.items():
      props = ifaces.get(DEVICE_IFACE)
      if props is None:
        continue

      adapter_path = self._as_object_path(props.get("Adapter"))
      adapter_id = adapter_path.rsplit("/", 1)[-1] if adapter_path else "unknown"
      address = self._as_str(props.get("Address"))
      device_id = address or self._device_id_from_path(path)

      devices.append(
        Device(
          id=device_id,
          object_path=path,
          adapter_id=adapter_id,
          name=self._as_str(props.get("Name")),
          alias=self._as_str(props.get("Alias")),
          address=address,
          address_type=self._as_str(props.get("AddressType")),
          icon=self._as_str(props.get("Icon")),
          device_class=self._as_int(props.get("Class")),
          appearance=self._as_int(props.get("Appearance")),
          rssi=self._as_int(props.get("RSSI")),
          tx_power=self._as_int(props.get("TxPower")),
          paired=self._as_bool(props.get("Paired")),
          trusted=self._as_bool(props.get("Trusted")),
          connected=self._as_bool(props.get("Connected")),
          blocked=self._as_bool(props.get("Blocked")),
          services_resolved=self._as_bool(props.get("ServicesResolved")),
          uuids=self._as_str_list(props.get("UUIDs")),
        )
      )

    devices.sort(key=lambda item: item.id)
    return devices

  async def get_device(self, device_id: str) -> Device | None:
    normalized_target = self._normalize_device_id(device_id)

    for device in await self.list_devices():
      if self._normalize_device_id(device.id) == normalized_target:
        return device

    return None

  async def pair_device(self, device_id: str) -> bool:
    device = await self.get_device(device_id)
    if device is None:
      return False

    iface = await self._get_interface(device.object_path, DEVICE_IFACE)
    await iface.call_pair()
    return True

  async def connect_device(self, device_id: str) -> bool:
    device = await self.get_device(device_id)
    if device is None:
      return False

    iface = await self._get_interface(device.object_path, DEVICE_IFACE)
    await iface.call_connect()
    return True

  async def disconnect_device(self, device_id: str) -> bool:
    device = await self.get_device(device_id)
    if device is None:
      return False

    iface = await self._get_interface(device.object_path, DEVICE_IFACE)
    await iface.call_disconnect()
    return True

  async def trust_device(self, device_id: str, trusted: bool) -> bool:
    device = await self.get_device(device_id)
    if device is None:
      return False

    properties = await self._get_properties_interface(device.object_path)
    await properties.call_set(DEVICE_IFACE, "Trusted", Variant("b", trusted))

    return True

  async def remove_device(self, device_id: str) -> bool:
    device = await self.get_device(device_id)
    if device is None:
      return False

    adapter = await self.get_adapter(device.adapter_id)
    if adapter is None:
      return False

    iface = await self._get_interface(adapter.object_path, ADAPTER_IFACE)
    await iface.call_remove_device(device.object_path)

    return True

  async def list_services(self, device_id: str) -> list[GattService]:
    device = await self.get_device(device_id)
    if device is None:
      return []

    managed = await self._get_managed_objects()
    services: list[GattService] = []

    for path, ifaces in managed.items():
      props = ifaces.get(GATT_SERVICE_IFACE)
      if props is None or not path.startswith(device.object_path + "/"):
        continue

      services.append(
        GattService(
          id=path.rsplit("/", 1)[-1],
          object_path=path,
          device_id=device.id,
          uuid=self._as_str(props.get("UUID")) or "",
          primary=self._as_bool(props.get("Primary")),
        )
      )

    services.sort(key=lambda item: item.id)
    return services

  async def get_service(self, device_id: str, service_id: str) -> GattService | None:
    for service in await self.list_services(device_id):
      if service.id == service_id:
        return service

    return None

  async def list_characteristics(self, device_id: str, service_id: str) -> list[GattCharacteristic]:
    service = await self.get_service(device_id, service_id)
    if service is None:
      return []

    managed = await self._get_managed_objects()
    characteristics: list[GattCharacteristic] = []

    for path, ifaces in managed.items():
      props = ifaces.get(GATT_CHARACTERISTIC_IFACE)
      if props is None or not path.startswith(service.object_path + "/"):
        continue

      characteristics.append(self._build_characteristic(path, props, device_id, service_id))

    characteristics.sort(key=lambda item: item.id)
    return characteristics

  async def get_characteristic(self, device_id: str, service_id: str, characteristic_id: str) -> GattCharacteristic | None:
    for characteristic in await self.list_characteristics(device_id, service_id):
      if characteristic.id == characteristic_id:
        return characteristic

    return None

  async def read_characteristic(self, device_id: str, service_id: str, characteristic_id: str) -> GattCharacteristic | None:
    characteristic = await self.get_characteristic(device_id, service_id, characteristic_id)
    if characteristic is None:
      return None

    iface = await self._get_interface(characteristic.object_path, GATT_CHARACTERISTIC_IFACE)
    await iface.call_read_value({})

    return await self.get_characteristic(device_id, service_id, characteristic_id)

  async def write_characteristic(
    self, device_id: str, service_id: str, characteristic_id: str, value: bytes
  ) -> GattCharacteristic | None:
    characteristic = await self.get_characteristic(device_id, service_id, characteristic_id)
    if characteristic is None:
      return None

    iface = await self._get_interface(characteristic.object_path, GATT_CHARACTERISTIC_IFACE)
    await iface.call_write_value(list(value), {})

    return await self.get_characteristic(device_id, service_id, characteristic_id)

  async def start_notify(self, device_id: str, service_id: str, characteristic_id: str) -> GattCharacteristic | None:
    characteristic = await self.get_characteristic(device_id, service_id, characteristic_id)
    if characteristic is None:
      return None

    iface = await self._get_interface(characteristic.object_path, GATT_CHARACTERISTIC_IFACE)
    await iface.call_start_notify()

    return await self.get_characteristic(device_id, service_id, characteristic_id)

  async def stop_notify(self, device_id: str, service_id: str, characteristic_id: str) -> GattCharacteristic | None:
    characteristic = await self.get_characteristic(device_id, service_id, characteristic_id)
    if characteristic is None:
      return None

    iface = await self._get_interface(characteristic.object_path, GATT_CHARACTERISTIC_IFACE)
    await iface.call_stop_notify()

    return await self.get_characteristic(device_id, service_id, characteristic_id)

  async def list_descriptors(self, device_id: str, service_id: str, characteristic_id: str) -> list[GattDescriptor]:
    characteristic = await self.get_characteristic(device_id, service_id, characteristic_id)
    if characteristic is None:
      return []

    managed = await self._get_managed_objects()
    descriptors: list[GattDescriptor] = []

    for path, ifaces in managed.items():
      props = ifaces.get(GATT_DESCRIPTOR_IFACE)
      if props is None or not path.startswith(characteristic.object_path + "/"):
        continue

      descriptors.append(
        GattDescriptor(
          id=path.rsplit("/", 1)[-1],
          object_path=path,
          device_id=device_id,
          service_id=service_id,
          characteristic_id=characteristic_id,
          uuid=self._as_str(props.get("UUID")) or "",
          flags=self._as_str_list(props.get("Flags")),
          value=self._as_hex(props.get("Value")),
        )
      )

    descriptors.sort(key=lambda item: item.id)
    return descriptors

  async def get_descriptor(
    self, device_id: str, service_id: str, characteristic_id: str, descriptor_id: str
  ) -> GattDescriptor | None:
    for descriptor in await self.list_descriptors(device_id, service_id, characteristic_id):
      if descriptor.id == descriptor_id:
        return descriptor

    return None

  async def read_descriptor(
    self, device_id: str, service_id: str, characteristic_id: str, descriptor_id: str
  ) -> GattDescriptor | None:
    descriptor = await self.get_descriptor(device_id, service_id, characteristic_id, descriptor_id)
    if descriptor is None:
      return None

    iface = await self._get_interface(descriptor.object_path, GATT_DESCRIPTOR_IFACE)
    await iface.call_read_value({})

    return await self.get_descriptor(device_id, service_id, characteristic_id, descriptor_id)

  async def write_descriptor(
    self, device_id: str, service_id: str, characteristic_id: str, descriptor_id: str, value: bytes
  ) -> GattDescriptor | None:
    descriptor = await self.get_descriptor(device_id, service_id, characteristic_id, descriptor_id)
    if descriptor is None:
      return None

    iface = await self._get_interface(descriptor.object_path, GATT_DESCRIPTOR_IFACE)
    await iface.call_write_value(list(value), {})

    return await self.get_descriptor(device_id, service_id, characteristic_id, descriptor_id)

  def _build_characteristic(
    self, path: str, props: Mapping[str, Variant], device_id: str, service_id: str
  ) -> GattCharacteristic:
    return GattCharacteristic(
      id=path.rsplit("/", 1)[-1],
      object_path=path,
      device_id=device_id,
      service_id=service_id,
      uuid=self._as_str(props.get("UUID")) or "",
      flags=self._as_str_list(props.get("Flags")),
      notifying=self._as_bool(props.get("Notifying")),
      value=self._as_hex(props.get("Value")),
    )

  async def _get_managed_objects(self) -> dict[str, dict[str, dict[str, Variant]]]:
    manager = await self._get_interface("/", OBJECT_MANAGER)
    objects = await manager.call_get_managed_objects()
    return cast(dict[str, dict[str, dict[str, Variant]]], objects)

  async def _get_interface(self, path: str, interface_name: str) -> BaseProxyInterface:
    if self._bus is None:
      raise RuntimeError("D-Bus is not connected")

    introspection = await self._bus.introspect(BLUEZ_SERVICE, path)
    proxy_object = self._bus.get_proxy_object(BLUEZ_SERVICE, path, introspection)

    return proxy_object.get_interface(interface_name)

  async def _get_properties_interface(self, path: str) -> BaseProxyInterface:
    return await self._get_interface(path, PROPERTIES_IFACE)

  async def _subscribe_to_signals(self) -> None:
    if self._bus is None or self._event_broker is None:
      return

    match_rule = f"type='signal',sender={BLUEZ_SERVICE}"
    await self._bus.call(
      Message(
        destination="org.freedesktop.DBus",
        path="/org/freedesktop/DBus",
        interface="org.freedesktop.DBus",
        member="AddMatch",
        signature="s",
        body=[match_rule],
      )
    )
    self._signal_matches.append(match_rule)
    self._bus.add_message_handler(self._handle_signal_message)

  async def _unsubscribe_from_signals(self) -> None:
    if self._bus is not None:
      self._bus.remove_message_handler(self._handle_signal_message)

    self._signal_matches.clear()

  async def _register_agent(self) -> None:
    if self._bus is None or self._event_broker is None:
      return

    try:
      agent = PairingAgent(self._event_broker)
      self._bus.export(AGENT_PATH, agent)
      agent_manager = await self._get_interface(AGENT_MANAGER_PATH, AGENT_MANAGER_IFACE)
      await agent_manager.call_register_agent(AGENT_PATH, self._agent_capability)
      await agent_manager.call_request_default_agent(AGENT_PATH)
      self._pairing_agent = agent
      logger.info("Registered Bluetooth pairing agent (capability=%s)", self._agent_capability)
    except Exception as exc:
      self._pairing_agent = None
      logger.warning("Bluetooth pairing agent registration failed: %s", exc)

  async def _unregister_agent(self) -> None:
    if self._bus is None or self._pairing_agent is None:
      return

    try:
      agent_manager = await self._get_interface(AGENT_MANAGER_PATH, AGENT_MANAGER_IFACE)
      await agent_manager.call_unregister_agent(AGENT_PATH)
    except Exception as exc:
      logger.warning("Bluetooth pairing agent unregistration failed: %s", exc)
    finally:
      self._bus.unexport(AGENT_PATH)
      self._pairing_agent = None

  def _handle_signal_message(self, message: Message) -> None:
    if message.message_type.name != "SIGNAL" or self._event_broker is None:
      return

    if message.interface == OBJECT_MANAGER and message.member == "InterfacesRemoved":
      self._spawn_background_task(self._handle_interfaces_removed(message))
    elif message.interface == PROPERTIES_IFACE and message.member == "PropertiesChanged":
      self._spawn_background_task(self._handle_properties_changed(message))

  def _spawn_background_task(self, coroutine: Coroutine[None, None, None]) -> None:
    task = asyncio.create_task(coroutine)
    self._background_tasks.add(task)
    task.add_done_callback(self._background_tasks.discard)

  async def _handle_interfaces_removed(self, message: Message) -> None:
    path, removed_interfaces = message.body

    if DEVICE_IFACE not in removed_interfaces or self._event_broker is None:
      return

    device_id = self._device_id_from_path(path)
    await self._event_broker.publish(DeviceRemovedEvent(device_id=device_id))

  async def _handle_properties_changed(self, message: Message) -> None:
    if self._event_broker is None:
      return

    path = message.path
    if path is None:
      return

    leaf = path.rsplit("/", 1)[-1]

    if leaf.startswith("hci"):
      adapter = await self.get_adapter(leaf)
      if adapter is not None:
        await self._event_broker.publish(AdapterChangedEvent(adapter=adapter))
      return

    if leaf.startswith("char") and "/service" in path:
      await self._handle_characteristic_properties_changed(path)
      return

    device_id = self._device_id_from_path(path)
    device = await self.get_device(device_id)
    if device is not None:
      await self._event_broker.publish(DeviceChangedEvent(device=device))

  async def _handle_characteristic_properties_changed(self, path: str) -> None:
    if self._event_broker is None:
      return

    parts = path.rstrip("/").split("/")
    if len(parts) < 3:
      return

    characteristic_id = parts[-1]
    service_id = parts[-2]
    device_path = "/".join(parts[:-2])
    device_id = self._device_id_from_path(device_path)

    characteristic = await self.get_characteristic(device_id, service_id, characteristic_id)
    if characteristic is not None:
      await self._event_broker.publish(CharacteristicChangedEvent(characteristic=characteristic))

  @staticmethod
  def _count_devices_by_adapter(managed: Mapping[str, Mapping[str, Mapping[str, Variant]]]) -> dict[str, int]:
    counts: dict[str, int] = {}

    for _, ifaces in managed.items():
      props = ifaces.get(DEVICE_IFACE)
      if props is None:
        continue

      adapter_path = BlueZManager._as_object_path(props.get("Adapter"))
      if adapter_path is None:
        continue

      adapter_id = adapter_path.rsplit("/", 1)[-1]
      counts[adapter_id] = counts.get(adapter_id, 0) + 1

    return counts

  @staticmethod
  def _normalize_device_id(value: str) -> str:
    return unquote(value).replace("_", ":").upper()

  @staticmethod
  def _device_id_from_path(path: str) -> str:
    leaf = path.rsplit("/", 1)[-1]
    if leaf.startswith("dev_"):
      return leaf.removeprefix("dev_").replace("_", ":")

    return leaf

  @staticmethod
  def _as_str(value: Variant | None) -> str | None:
    if value is None:
      return None

    if isinstance(value.value, str):
      return value.value

    return None

  @staticmethod
  def _as_object_path(value: Variant | None) -> str | None:
    if value is None:
      return None

    if isinstance(value.value, str):
      return value.value

    return None

  @staticmethod
  def _as_int(value: Variant | None) -> int | None:
    if value is None:
      return None

    if isinstance(value.value, int):
      return value.value

    return None

  @staticmethod
  def _as_bool(value: Variant | None) -> bool:
    if value is None:
      return False

    if isinstance(value.value, bool):
      return value.value

    return False

  @staticmethod
  def _as_str_list(value: Variant | None) -> list[str]:
    if value is None:
      return []

    if isinstance(value.value, list):
      return [item for item in value.value if isinstance(item, str)]

    return []

  @staticmethod
  def _as_hex(value: Variant | None) -> str | None:
    if value is None:
      return None

    if isinstance(value.value, (bytes, bytearray)):
      return value.value.hex()

    if isinstance(value.value, list):
      try:
        return bytes(value.value).hex()
      except (TypeError, ValueError):
        return None

    return None


def create_bluetooth_manager(
  system_bus_address: str | None,
  event_broker: BluetoothEventBroker | None = None,
  agent_capability: str = "DisplayYesNo",
) -> BlueZManager:
  return BlueZManager(SystemBusClient(system_bus_address), event_broker, agent_capability)
