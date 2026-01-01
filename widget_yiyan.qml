import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import RinUI
import Widgets

Widget {
    id: root
    text: "每日一言 | LaoShui"
    width: 320 // 显式设置宽度，确保 Text wrap 正常工作

    onBackendChanged: {
        if (backend) {
            backend.init_content()
        }
    }
    
    Flickable {
        id: flickable
        anchors.fill: parent
        // anchors.margins: 12 // Removed to fill the space
        contentWidth: width
        contentHeight: contentLayout.height
        clip: true
        interactive: true

        ColumnLayout {
            id: contentLayout
            width: parent.width
            spacing: 8
            
            Text {
                id: contentText
                text: "加载中..." 
                font.pointSize: 16
                font.bold: true
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
                
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignHCenter
                
                color: root.miniMode ? "#000" : (Theme.isDark() ? "#fff" : "#000")
                
                onTextChanged: restartAnimTimer.restart()
            }
            
            Text {
                id: authorText
                text: ""
                font.pointSize: 12
                horizontalAlignment: Text.AlignRight
                
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignRight
                
                color: root.miniMode ? "#555" : (Theme.isDark() ? "#ccc" : "#555")
            }
        }
    }

    // 延迟启动动画的 Timer
    Timer {
        id: restartAnimTimer
        interval: 500
        onTriggered: checkAndStartScroll()
    }

    // 自动滚动动画
    SequentialAnimation {
        id: autoScrollAnim
        loops: Animation.Infinite
        
        // 1. 向下滚动
        NumberAnimation {
            id: scrollDown
            target: flickable
            property: "contentY"
            duration: 0 
            easing.type: Easing.Linear
        }
        
        // 2. 立即平滑回滚顶部
        NumberAnimation {
            target: flickable
            property: "contentY"
            to: 0
            duration: 1000
            easing.type: Easing.InOutQuad
        }
    }

    function checkAndStartScroll() {
        autoScrollAnim.stop()
        flickable.contentY = 0
        
        // 加载中或无内容时不滚动
        if (contentText.text === "加载中..." || contentText.text === "") return;
        
        if (contentLayout.height > flickable.height) {
            var distance = contentLayout.height - flickable.height
            scrollDown.to = distance
            // 速度：每像素 50ms
            scrollDown.duration = Math.max(1000, distance * 50)
            autoScrollAnim.start()
        }
    }

    // 确保组件加载完成后尝试获取数据
    Component.onCompleted: {
        if (backend) {
            backend.init_content()
        }
    }

    // 监听高度变化（如窗口缩放）
    onHeightChanged: restartAnimTimer.restart()
    
    // 连接后端信号
    Connections {
        target: backend
        function onContentUpdated(content, author) {
            contentText.text = content;
            authorText.text = "—— " + author;
        }
    }
}