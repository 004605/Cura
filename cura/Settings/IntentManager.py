#Copyright (c) 2019 Ultimaker B.V.
#Cura is released under the terms of the LGPLv3 or higher.

from PyQt5.QtCore import QObject, pyqtSignal
from typing import Any, Dict, List, Set, Tuple, TYPE_CHECKING
from cura.CuraApplication import CuraApplication
from cura.Settings.ExtruderManager import ExtruderManager
from UM.Settings.InstanceContainer import InstanceContainer

if TYPE_CHECKING:
    from UM.Settings.InstanceContainer import InstanceContainer

##  Front-end for querying which intents are available for a certain
#   configuration.
#
#   CURRENTLY THIS CLASS CONTAINS ONLY SOME PSEUDOCODE OF WHAT WE ARE SUPPOSED
#   TO IMPLEMENT.
class IntentManager(QObject):
    __instance = None

    def __init__(self) -> None:
        super().__init__()
        CuraApplication.getInstance().getMachineManager().activeStackChanged.connect(self.configurationChanged)
        self.configurationChanged.connect(self.selectDefaultIntent)
        pass

    ##  This class is a singleton.
    @classmethod
    def getInstance(cls):
        if not cls.__instance:
            cls.__instance = IntentManager()
        return cls.__instance

    configurationChanged = pyqtSignal()

    ##  Gets the metadata dictionaries of all intent profiles for a given
    #   configuration.
    #
    #   \param definition_id ID of the printer.
    #   \param nozzle_name Name of the nozzle.
    #   \param material_id ID of the material.
    #   \return A list of metadata dictionaries matching the search criteria, or
    #   an empty list if nothing was found.
    def intentMetadatas(self, definition_id: str, nozzle_name: str, material_id: str) -> List[Dict[str, Any]]:
        registry = CuraApplication.getInstance().getContainerRegistry()
        return registry.findContainersMetadata(definition = definition_id, variant = nozzle_name, material_id = material_id)

    ##  Collects and returns all intent categories available for the given
    #   parameters. Note that the 'default' category is always available.
    #
    #   \param definition_id ID of the printer.
    #   \param nozzle_name Name of the nozzle.
    #   \param material_id ID of the material.
    #   \return A set of intent category names.
    def intentCategories(self, definition_id: str, nozzle_id: str, material_id: str) -> List[str]:
        categories = set()
        for intent in self.intentMetadatas(definition_id, nozzle_id, material_id):
            categories.add(intent["intent_category"])
        categories.add("default") #The "empty" intent is not an actual profile specific to the configuration but we do want it to appear in the categories list.
        return list(categories)

    ##  List of intents to be displayed in the interface.
    #
    #   For the interface this will have to be broken up into the different
    #   intent categories. That is up to the model there.
    #
    #   \return A list of tuples of intent_category and quality_type. The actual
    #   instance may vary per extruder.
    def currentAvailableIntents(self) -> List[Tuple[str, str]]:
        application = CuraApplication.getInstance()
        global_stack = application.getGlobalContainerStack()
        if global_stack is None:
            return [("default", "normal")]
        quality_groups = application.getQualityManager().getQualityGroups(global_stack)
        available_quality_types = {quality_group.quality_type for quality_group in quality_groups.values() if quality_group.node_for_global is not None}
        # available_quality_types could just be 'quality_group.keys()', except for that the node_for_global may be None

        final_intent_ids = set() #type: Set[str]
        current_definition_id = global_stack.definition.getMetaDataEntry("id")
        for extruder_stack in ExtruderManager.getInstance().getUsedExtruderStacks():
            nozzle_name = extruder_stack.variant.getMetaDataEntry("name")
            material_id = extruder_stack.material.getMetaDataEntry("base_file")
            final_intent_ids |= {metadata["id"] for metadata in self.intentMetadatas(current_definition_id, nozzle_name, material_id) if metadata["quality_type"] in available_quality_types}

        result = set() #type: Set[Tuple[str, str]]
        for intent_id in final_intent_ids:
            intent_metadata = application.getContainerRegistry().findContainersMetadata(id = intent_id)[0]
            result.add((intent_metadata["intent_category"], intent_metadata["quality_type"]))
        return list(result)

    ##  List of intent categories available in either of the extruders.
    #
    #   This is purposefully inconsistent with the way that the quality types
    #   are listed. The quality types will show all quality types available in
    #   the printer using any configuration. This will only list the intent
    #   categories that are available using the current configuration (but the
    #   union over the extruders).
    #   \return List of all categories in the current configurations of all
    #   extruders.
    def currentAvailableIntentCategories(self) -> List[str]:
        global_stack = CuraApplication.getInstance().getGlobalContainerStack()
        if global_stack is None:
            return ["default"]
        current_definition_id = global_stack.definition.getMetaDataEntry("id")
        final_intent_categories = set() #type: Set[str]
        for extruder_stack in ExtruderManager.getInstance().getUsedExtruderStacks():
            nozzle_name = extruder_stack.variant.getMetaDataEntry("name")
            material_id = extruder_stack.material.getMetaDataEntry("base_file")
            final_intent_categories.update(self.intentCategories(current_definition_id, nozzle_name, material_id))
        return list(final_intent_categories)

    ##  The intent that gets selected by default when no intent is available for
    #   the configuration, an extruder can't match the intent that the user
    #   selects, or just when creating a new printer.
    def defaultIntent(self) -> InstanceContainer:
        return CuraApplication.getInstance().empty_intent_container

    ##  Apply intent on the stacks.
    def selectIntent(self, intent_category, quality_type) -> None:
        application = CuraApplication.getInstance()
        global_stack = application.getGlobalContainerStack()
        if global_stack is None:
            return
        current_definition_id = global_stack.definition.getMetaDataEntry("id")
        for extruder_stack in ExtruderManager.getInstance().getUsedExtruderStacks():
            nozzle_name = extruder_stack.variant.getMetaDataEntry("name")
            material_id = extruder_stack.material.getMetaDataEntry("base_file")
            intent = application.getContainerRegistry().findContainers(definition = current_definition_id, variant = nozzle_name, material = material_id, quality_type = quality_type, intent_category = intent_category)
            if intent:
                extruder_stack.intent = intent[0]
            else:
                extruder_stack.intent = self.defaultIntent()

        application.getMachineManager().setQualityGroupByQualityType(quality_type)

    ##  Selects the default intents on every extruder.
    def selectDefaultIntent(self) -> None:
        for extruder_stack in ExtruderManager.getInstance().getUsedExtruderStacks():
            extruder_stack.intent = self.defaultIntent()
