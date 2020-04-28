from typing import Optional, TYPE_CHECKING

from PyQt5.QtCore import QObject, pyqtSlot, Qt

from UM.Qt.ListModel import ListModel

if TYPE_CHECKING:
    from cura.CuraApplication import CuraApplication


class DiscoveredUltimakerCloudPrintersModel(ListModel):
    DeviceKeyRole = Qt.UserRole + 1
    DeviceNameRole = Qt.UserRole + 2
    DeviceTypeRole = Qt.UserRole + 3
    DeviceFirmwareVersionRole = Qt.UserRole + 4

    def __init__(self, application: "CuraApplication", parent: Optional["QObject"] = None) -> None:
        super().__init__(parent)

        self.addRoleName(self.DeviceKeyRole, "key")
        self.addRoleName(self.DeviceNameRole, "name")
        self.addRoleName(self.DeviceTypeRole, "machine_type")
        self.addRoleName(self.DeviceFirmwareVersionRole, "firmware_version")

        self._discovered_ultimaker_cloud_printers_list = []
        self._application = application

    def addDiscoveredUltimakerCloudPrinters(self, new_devices) -> None:
        for device in new_devices:
            self._discovered_ultimaker_cloud_printers_list.append({
                "key": device.getId(),
                "name": device.name,
                "machine_type": device.printerTypeName,
                "firmware_version": device.firmwareVersion
            })
        self._update()

    @pyqtSlot()
    def clear(self):
        self._discovered_ultimaker_cloud_printers_list = []
        self._update()

    def _update(self):
        items = []

        for cloud_printer in self._discovered_ultimaker_cloud_printers_list:
            items.append(cloud_printer)

        # Execute all filters.
        filtered_items = list(items)

        filtered_items.sort(key = lambda k: k["name"])
        self.setItems(filtered_items)
