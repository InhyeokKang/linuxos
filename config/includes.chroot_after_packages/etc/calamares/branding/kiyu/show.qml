import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation
{
    id: presentation

    function nextSlide() {
        presentation.goToNextSlide();
    }

    Timer {
        id: advanceTimer
        interval: 8000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: nextSlide()
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#1b2233" }
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.8
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            color: "white"
            font.pixelSize: 22
            text: "가볍고, 빠르고, 안전하게.\nkiyu 를 설치하는 동안 잠시만 기다려 주세요."
        }
    }
    Slide {
        Rectangle { anchors.fill: parent; color: "#1b2233" }
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.8
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            color: "white"
            font.pixelSize: 22
            text: "윈도우에서 쓰던 단축키가 그대로 동작합니다.\nWin+E 탐색기, Win+D 바탕화면, Ctrl+Shift+Esc 작업 관리자"
        }
    }
    Slide {
        Rectangle { anchors.fill: parent; color: "#1b2233" }
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.8
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            color: "white"
            font.pixelSize: 22
            text: "앱은 '소프트웨어' 스토어에서 설치하세요.\n게임은 시작 메뉴 > 'kiyu 게임 설정' 한 번이면 Steam 이 준비됩니다."
        }
    }
    Slide {
        Rectangle { anchors.fill: parent; color: "#1b2233" }
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.8
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            color: "white"
            font.pixelSize: 22
            text: "보안 업데이트는 자동으로 설치됩니다.\n방화벽은 기본으로 켜져 있고, 앱은 샌드박스 안에서 실행됩니다."
        }
    }

    function onActivate() { }
    function onLeave() { }
}
