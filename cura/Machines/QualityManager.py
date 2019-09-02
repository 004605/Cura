# Copyright (c) 2019 Ultimaker B.V.
# Cura is released under the terms of the LGPLv3 or higher.

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from UM.Logger import Logger
from UM.Util import parseBool
from UM.Settings.InstanceContainer import InstanceContainer
from UM.Decorators import deprecated

import cura.CuraApplication
from cura.Settings.ExtruderStack import ExtruderStack

from cura.Machines.ContainerTree import ContainerTree  # The implementation that replaces this manager, to keep the deprecated interface working.
from .QualityChangesGroup import QualityChangesGroup
from .QualityGroup import QualityGroup
from .QualityNode import QualityNode

if TYPE_CHECKING:
    from UM.Settings.Interfaces import DefinitionContainerInterface
    from cura.Settings.GlobalStack import GlobalStack
    from .QualityChangesGroup import QualityChangesGroup


#
# Similar to MaterialManager, QualityManager maintains a number of maps and trees for quality profile lookup.
# The models GUI and QML use are now only dependent on the QualityManager. That means as long as the data in
# QualityManager gets updated correctly, the GUI models should be updated correctly too, and the same goes for GUI.
#
# For now, updating the lookup maps and trees here is very simple: we discard the old data completely and recreate them
# again. This means the update is exactly the same as initialization. There are performance concerns about this approach
# but so far the creation of the tables and maps is very fast and there is no noticeable slowness, we keep it like this
# because it's simple.
#
class QualityManager(QObject):
    __instance = None

    @classmethod
    @deprecated("Use the ContainerTree structure instead.", since = "4.3")
    def getInstance(cls) -> "QualityManager":
        if cls.__instance is None:
            cls.__instance = QualityManager()
        return cls.__instance

    qualitiesUpdated = pyqtSignal()

    def __init__(self, parent = None) -> None:
        super().__init__(parent)
        application = cura.CuraApplication.CuraApplication.getInstance()
        self._material_manager = application.getMaterialManager()
        self._container_registry = application.getContainerRegistry()

        self._empty_quality_container = application.empty_quality_container
        self._empty_quality_changes_container = application.empty_quality_changes_container

        # For quality lookup
        self._machine_nozzle_buildplate_material_quality_type_to_quality_dict = {}  # type: Dict[str, QualityNode]

        # For quality_changes lookup
        self._machine_quality_type_to_quality_changes_dict = {}  # type: Dict[str, QualityNode]

        self._default_machine_definition_id = "fdmprinter"

        self._container_registry.containerMetaDataChanged.connect(self._onContainerMetadataChanged)
        self._container_registry.containerAdded.connect(self._onContainerMetadataChanged)
        self._container_registry.containerRemoved.connect(self._onContainerMetadataChanged)

    def _onContainerMetadataChanged(self, container: InstanceContainer) -> None:
        self._onContainerChanged(container)

    def _onContainerChanged(self, container: InstanceContainer) -> None:
        container_type = container.getMetaDataEntry("type")
        if container_type not in ("quality", "quality_changes"):
            return

    # Returns a dict of "custom profile name" -> QualityChangesGroup
    def getQualityChangesGroups(self, machine: "GlobalStack") -> List[QualityChangesGroup]:
        variant_names = [extruder.variant.getName() for extruder in machine.extruders.values()]
        material_bases = [extruder.material.getMetaDataEntry("base_file") for extruder in machine.extruders.values()]
        extruder_enabled = [extruder.isEnabled for extruder in machine.extruders.values()]
        machine_node = ContainerTree.getInstance().machines[machine.definition.getId()]
        return machine_node.getQualityChangesGroups(variant_names, material_bases, extruder_enabled)

    ##  Gets the quality groups for the current printer.
    #
    #   Both available and unavailable quality groups will be included. Whether
    #   a quality group is available can be known via the field
    #   ``QualityGroup.is_available``. For more details, see QualityGroup.
    #   \return A dictionary with quality types as keys and the quality groups
    #   for those types as values.
    def getQualityGroups(self, global_stack: "GlobalStack") -> Dict[str, QualityGroup]:
        # Gather up the variant names and material base files for each extruder.
        variant_names = [extruder.variant.getName() for extruder in global_stack.extruders.values()]
        material_bases = [extruder.material.getMetaDataEntry("base_file") for extruder in global_stack.extruders.values()]
        extruder_enabled = [extruder.isEnabled for extruder in global_stack.extruders.values()]
        definition_id = global_stack.definition.getId()
        return ContainerTree.getInstance().machines[definition_id].getQualityGroups(variant_names, material_bases, extruder_enabled)

    def getQualityGroupsForMachineDefinition(self, machine: "GlobalStack") -> Dict[str, QualityGroup]:
        machine_definition_id = getMachineDefinitionIDForQualitySearch(machine.definition)

        # To find the quality container for the GlobalStack, check in the following fall-back manner:
        #   (1) the machine-specific node
        #   (2) the generic node
        machine_node = self._machine_nozzle_buildplate_material_quality_type_to_quality_dict.get(machine_definition_id)
        default_machine_node = self._machine_nozzle_buildplate_material_quality_type_to_quality_dict.get(
            self._default_machine_definition_id)
        nodes_to_check = [machine_node, default_machine_node]

        # Iterate over all quality_types in the machine node
        quality_group_dict = dict()
        for node in nodes_to_check:
            if node and node.quality_type:
                quality_group = QualityGroup(node.getMetaDataEntry("name", ""), node.quality_type)
                quality_group.setGlobalNode(node)
                quality_group_dict[node.quality_type] = quality_group

        return quality_group_dict

    ##  Get the quality group for the preferred quality type for a certain
    #   global stack.
    #
    #   If the preferred quality type is not available, ``None`` will be
    #   returned.
    #   \param machine The global stack of the machine to get the preferred
    #   quality group for.
    #   \return The preferred quality group, or ``None`` if that is not
    #   available.
    def getDefaultQualityType(self, machine: "GlobalStack") -> Optional[QualityGroup]:
        machine_node = ContainerTree.getInstance().machines[machine.definition.getId()]
        quality_groups = self.getQualityGroups(machine)
        result = quality_groups.get(machine_node.preferred_quality_type)
        if result is not None and result.is_available:
            return result
        return None  # If preferred quality type is not available, leave it up for the caller.


    #
    # Methods for GUI
    #

    ##  Deletes a custom profile. It will be gone forever.
    #   \param quality_changes_group The quality changes group representing the
    #   profile to delete.
    @pyqtSlot(QObject)
    def removeQualityChangesGroup(self, quality_changes_group: "QualityChangesGroup") -> None:
        return cura.CuraApplication.CuraApplication.getInstance().getQualityManagementModel().removeQualityChangesGroup(quality_changes_group)

    ##  Rename a custom profile.
    #
    #   Because the names must be unique, the new name may not actually become
    #   the name that was given. The actual name is returned by this function.
    #   \param quality_changes_group The custom profile that must be renamed.
    #   \param new_name The desired name for the profile.
    #   \return The actual new name of the profile, after making the name
    #   unique.
    @pyqtSlot(QObject, str, result = str)
    def renameQualityChangesGroup(self, quality_changes_group: "QualityChangesGroup", new_name: str) -> str:
        return cura.CuraApplication.CuraApplication.getInstance().getQualityManagementModel().removeQualityChangesGroup(quality_changes_group, new_name)

    ##  Duplicates a given quality profile OR quality changes profile.
    #   \param new_name The desired name of the new profile. This will be made
    #   unique, so it might end up with a different name.
    #   \param quality_model_item The item of this model to duplicate, as
    #   dictionary. See the descriptions of the roles of this list model.
    @pyqtSlot(str, "QVariantMap")
    def duplicateQualityChanges(self, quality_changes_name: str, quality_model_item: Dict[str, Any]) -> None:
        return cura.CuraApplication.CuraApplication.getInstance().getQualityManagementModel().duplicateQualityChanges(quality_changes_name, quality_model_item)

    ##  Create quality changes containers from the user containers in the active
    #   stacks.
    #
    #   This will go through the global and extruder stacks and create
    #   quality_changes containers from the user containers in each stack. These
    #   then replace the quality_changes containers in the stack and clear the
    #   user settings.
    #   \param base_name The new name for the quality changes profile. The final
    #   name of the profile might be different from this, because it needs to be
    #   made unique.
    @pyqtSlot(str)
    def createQualityChanges(self, base_name: str) -> None:
        return cura.CuraApplication.CuraApplication.getInstance().getQualityManagementModel().createQualityChanges(base_name)

    #
    # Create a quality changes container with the given setup.
    #
    def _createQualityChanges(self, quality_type: str, new_name: str, machine: "GlobalStack",
                              extruder_stack: Optional["ExtruderStack"]) -> "InstanceContainer":
        base_id = machine.definition.getId() if extruder_stack is None else extruder_stack.getId()
        new_id = base_id + "_" + new_name
        new_id = new_id.lower().replace(" ", "_")
        new_id = self._container_registry.uniqueName(new_id)

        # Create a new quality_changes container for the quality.
        quality_changes = InstanceContainer(new_id)
        quality_changes.setName(new_name)
        quality_changes.setMetaDataEntry("type", "quality_changes")
        quality_changes.setMetaDataEntry("quality_type", quality_type)

        # If we are creating a container for an extruder, ensure we add that to the container
        if extruder_stack is not None:
            quality_changes.setMetaDataEntry("position", extruder_stack.getMetaDataEntry("position"))

        # If the machine specifies qualities should be filtered, ensure we match the current criteria.
        machine_definition_id = getMachineDefinitionIDForQualitySearch(machine.definition)
        quality_changes.setDefinition(machine_definition_id)

        quality_changes.setMetaDataEntry("setting_version", cura.CuraApplication.CuraApplication.getInstance().SettingVersion)
        return quality_changes


#
# Gets the machine definition ID that can be used to search for Quality containers that are suitable for the given
# machine. The rule is as follows:
#   1. By default, the machine definition ID for quality container search will be "fdmprinter", which is the generic
#      machine.
#   2. If a machine has its own machine quality (with "has_machine_quality = True"), we should use the given machine's
#      own machine definition ID for quality search.
#      Example: for an Ultimaker 3, the definition ID should be "ultimaker3".
#   3. When condition (2) is met, AND the machine has "quality_definition" defined in its definition file, then the
#      definition ID specified in "quality_definition" should be used.
#      Example: for an Ultimaker 3 Extended, it has "quality_definition = ultimaker3". This means Ultimaker 3 Extended
#               shares the same set of qualities profiles as Ultimaker 3.
#
def getMachineDefinitionIDForQualitySearch(machine_definition: "DefinitionContainerInterface",
                                           default_definition_id: str = "fdmprinter") -> str:
    machine_definition_id = default_definition_id
    if parseBool(machine_definition.getMetaDataEntry("has_machine_quality", False)):
        # Only use the machine's own quality definition ID if this machine has machine quality.
        machine_definition_id = machine_definition.getMetaDataEntry("quality_definition")
        if machine_definition_id is None:
            machine_definition_id = machine_definition.getId()

    return machine_definition_id
