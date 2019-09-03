import QtQuick 2.0
import QtQuick.Controls 2.3
import QtQuick.Layouts 1.3
import UM 1.1 as UM

Item
{
    id: base
    property ButtonGroup buttonGroup: null

    property color activeColor: UM.Theme.getColor("primary")
    property color inactiveColor: UM.Theme.getColor("slider_groove")
    property color defaultItemColor: UM.Theme.getColor("small_button_active")
    property int checkboxSize: UM.Theme.getSize("radio_button").height * 0.75
    property int inactiveMarkerSize: 2 * barSize
    property int barSize: UM.Theme.getSize("slider_groove_radius").height
    property var isCheckedFunction // Function that accepts the modelItem and returns if the item should be active.

    implicitWidth: 200
    implicitHeight: checkboxSize

    property var dataModel: null

    // The horizontal inactive bar that sits behind the buttons
    Rectangle
    {
        id: inactiveLine
        color: inactiveColor

        height: barSize

        anchors
        {
            left: buttonBar.left
            right: buttonBar.right
            leftMargin: (checkboxSize - inactiveMarkerSize) / 2
            rightMargin: (checkboxSize - inactiveMarkerSize) / 2
            verticalCenter: parent.verticalCenter
        }
    }


    RowLayout
    {
        id: buttonBar
        anchors.top: parent.top
        height: checkboxSize
        width: parent.width
        spacing: 0

        Repeater
        {
            id: repeater
            model: base.dataModel
            height: checkboxSize
            Item
            {
                Layout.fillWidth: true
                Layout.fillHeight: true
                // The last item of the repeater needs to be shorter, as we don't need another part to fit
                // the horizontal bar. The others should essentially not be limited.
                Layout.maximumWidth: index + 1 === repeater.count ? activeComponent.width: 200000000

                property bool isEnabled: model.available
                // The horizontal bar between the checkable options.
                // Note that the horizontal bar points towards the previous item.
                Rectangle
                {
                    property Item previousItem: repeater.itemAt(index - 1)

                    height: barSize
                    width: buttonBar.width / (repeater.count - 1) - activeComponent.width - 2
                    color: defaultItemColor

                    anchors
                    {
                        right: activeComponent.left
                        verticalCenter: parent.verticalCenter
                    }
                    visible: previousItem !== null && previousItem.isEnabled && isEnabled
                }
                Loader
                {
                    id: activeComponent
                    sourceComponent: isEnabled? checkboxComponent : disabledComponent
                    width: checkboxSize

                    property var modelItem: model
                }
            }
        }
    }

    Component
    {
        id: disabledComponent
        Item
        {
            height: checkboxSize
            width: checkboxSize

            Rectangle
            {
                // This can (and should) be done wiht a verticalCenter. For some reason it does work in QtCreator
                // but not when using the exact same QML in Cura.
                anchors.verticalCenter: parent.verticalCenter
                anchors.horizontalCenter: parent.horizontalCenter
                height: inactiveMarkerSize
                width: inactiveMarkerSize
                radius: width / 2
                color: inactiveColor
            }
        }
    }

    Component
    {
        id: checkboxComponent
        CheckBox
        {
            id: checkbox
            ButtonGroup.group: buttonGroup
            width: checkboxSize
            height: checkboxSize
            property var modelData: modelItem

            checked: isCheckedFunction(modelItem)
            indicator: Rectangle
            {
                height: checkboxSize
                width: checkboxSize
                radius: width / 2

                border.color: defaultItemColor

                Rectangle
                {
                    anchors
                    {
                        margins: 3
                        fill: parent
                    }
                    radius: width / 2
                    color: activeColor
                    visible: checkbox.checked
                }
            }
        }
    }
}
