import QtQuick 2.0
import QtQuick.Controls 2.3
import Cura 1.6 as Cura

import UM 1.2 as UM

Button
{
    // This is a work around for a qml issue. Since the default button uses a private implementation for contentItem
    // (the so called IconText), which handles the mnemonic conversion (aka; ensuring that &Button) text property
    // is rendered with the B underlined. Since we're also forced to mix controls 1.0 and 2.0 actions together,
    // we need a special property for the text of the label if we do want it to be rendered correclty, but don't want
    // another shortcut to be added (which will cause for "QQuickAction::event: Ambiguous shortcut overload: " to
    // happen.
    property string labelText: ""
    id: button
    hoverEnabled: true

    background: Rectangle
    {
        id: backgroundRectangle
        border.width: 1
        border.color: button.checked ? UM.Theme.getColor("setting_control_border_highlight") : "transparent"
        color: button.hovered ? UM.Theme.getColor("action_button_hovered") : "transparent"
        radius: UM.Theme.getSize("action_button_radius").width
    }

    // Workarround to ensure that the mnemonic highlighting happens correctly
    function replaceText(txt)
    {
        var index = txt.indexOf("&")
        if(index >= 0)
        {
            txt = txt.replace(txt.substr(index, 2), ("<u>" + txt.substr(index + 1, 1) + "</u>"))
        }
        return txt
    }

    contentItem: Label
    {
        id: textLabel
        text: button.text != "" ? replaceText(button.text) : replaceText(button.labelText)
        height: contentHeight
        verticalAlignment: Text.AlignVCenter
        anchors.left: button.left
        anchors.leftMargin: UM.Theme.getSize("wide_margin").width
    }
}