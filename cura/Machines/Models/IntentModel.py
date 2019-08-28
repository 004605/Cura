# Copyright (c) 2019 Ultimaker B.V.
# Cura is released under the terms of the LGPLv3 or higher.

from typing import Optional, List, Dict, Any

from PyQt5.QtCore import Qt, QObject, pyqtProperty, pyqtSignal

from UM.Qt.ListModel import ListModel

from cura.Machines.ContainerTree import ContainerTree
from cura.Settings.IntentManager import IntentManager
import cura.CuraApplication


class IntentModel(ListModel):
    NameRole = Qt.UserRole + 1
    QualityTypeRole = Qt.UserRole + 2

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self.addRoleName(self.NameRole, "name")
        self.addRoleName(self.QualityTypeRole, "quality_type")

        self._intent_category = "engineering"

        machine_manager = cura.CuraApplication.CuraApplication.getInstance().getMachineManager()
        machine_manager.globalContainerChanged.connect(self._update)
        machine_manager.activeStackChanged.connect(self._update)
        self._update()

    intentCategoryChanged = pyqtSignal()

    def setIntentCategory(self, new_category: str) -> None:
        if self._intent_category != new_category:
            self._intent_category = new_category
            self.intentCategoryChanged.emit()
            self._update()

    @pyqtProperty(str, fset = setIntentCategory, notify = intentCategoryChanged)
    def intentCategory(self) -> str:
        return self._intent_category

    def _update(self) -> None:
        new_items = []  # type: List[Dict[str, Any]]
        global_stack = cura.CuraApplication.CuraApplication.getInstance().getGlobalContainerStack()
        if not global_stack:
            self.setItems(new_items)
            return
        quality_groups = ContainerTree.getInstance().getCurrentQualityGroups()

        for intent_category, quality_type in IntentManager.getInstance().getCurrentAvailableIntents():
            if intent_category == self._intent_category:
                new_items.append({"name": quality_groups[quality_type].name, "quality_type": quality_type})
        if self._intent_category == "default": #For Default we always list all quality types. We can't filter on available profiles since the empty intent is not a specific quality type.
            for quality_type in quality_groups.keys():
                new_items.append({"name": quality_groups[quality_type].name, "quality_type": quality_type})

        self.setItems(new_items)
