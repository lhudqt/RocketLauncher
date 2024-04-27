from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QComboBox, QLineEdit, QPushButton, QFormLayout, QHBoxLayout, QVBoxLayout, QMessageBox, QFileDialog, QDialog
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6 import QtGui
import minecraft_launcher_lib
import sys
import subprocess
import requests

def getName(uuid):
    response = requests.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}").json()
    return response["name"]

def getxstsuserhash(xbl):
    url = "https://xsts.auth.xboxlive.com/xsts/authorize"
    headers = {"Content-Type" : "application/json", "Accept" : "application/json"}
    data = {
            "Properties": {
                "SandboxId": "RETAIL",
                "UserTokens": [xbl]
            },
            "RelyingParty": "rp://api.minecraftservices.com/",
            "TokenType": "JWT"
            }
    response = requests.post(url, headers=headers, json=data)
    jsonresponse = response.json()
    return jsonresponse['DisplayClaims']['xui'][0]['uhs'],jsonresponse['Token']

def getssid(userhash, xsts):
        url = "https://api.minecraftservices.com/authentication/login_with_xbox"
        headers = {'Content-Type': 'application/json'}
        data = {
           "identityToken" : f"XBL3.0 x={userhash};{xsts}",
           "ensureLegacyEnabled" : "true"
        }
        response = requests.post(url, headers=headers, json=data)
        jsonresponse = response.json()
        return jsonresponse['access_token']

class SkinChangeWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Change Skin")
        self.setFixedSize(300, 200)

        self.skin_type_label = QLabel("Skin Type:")
        self.skin_type_combo = QComboBox()
        self.skin_type_combo.addItems(["Classic", "Slim"])

        self.directory_label = QLabel("Skin URL:")
        self.url_input = QLineEdit()

        self.back_button = QPushButton("Back")
        self.set_skin_button = QPushButton("Set Skin")

        self.back_button.clicked.connect(self.close)

        layout = QVBoxLayout()
        layout.addWidget(self.skin_type_label)
        layout.addWidget(self.skin_type_combo)

        directory_layout = QHBoxLayout()
        directory_layout.addWidget(self.url_input)

        layout.addWidget(self.directory_label)
        layout.addLayout(directory_layout)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.back_button)
        button_layout.addWidget(self.set_skin_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setWindowIcon(QtGui.QIcon('logo.png'))

class NameChangeWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Change Name")
        self.setFixedSize(300, 150)

        self.new_name_label = QLabel("Name:")
        self.new_name_input = QLineEdit()
        self.change_button = QPushButton("Change Name")
        self.back_button = QPushButton("Back")

        layout = QVBoxLayout()
        layout.addWidget(self.new_name_label)
        layout.addWidget(self.new_name_input)
        layout.addWidget(self.change_button)
        layout.addWidget(self.back_button)
        self.setLayout(layout)
        self.setWindowIcon(QtGui.QIcon('logo.png'))

class InstallThread(QThread):
    text = pyqtSignal("QString")
    error_occurred = pyqtSignal()

    def __init__(self) -> None:
        QThread.__init__(self)

    def set_data(self, version: str, directory, ssid: str) -> None:
        self._version = version
        self._directory = directory
        self._ssid = ssid
        #print(ssid)

    def run(self) -> None:
        try:
            profile = minecraft_launcher_lib.microsoft_account.get_profile(self._ssid)
            uuid = profile["id"]
            name = profile["name"]
            options = {
                "username": name,
                "uuid": uuid,
                "token": self._ssid,
                "launcherName": "Rocket Launcher",
                "launcherVersion": "1.0"
            }
            minecraft_launcher_lib.install.install_minecraft_version(self._version, self._directory)
            minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(self._version, self._directory, options)
            subprocess.run(minecraft_command)
        except Exception as e:
            print(e)
            self.error_occurred.emit()

class Window(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._install_thread = InstallThread()
        self._install_thread.error_occurred.connect(self.display_error_message)

        self._version_combo_box = QComboBox()
        self._ssid_edit = QLineEdit()
        self._xbl_edit = QLineEdit()
        self._xbl_refresh_button = QPushButton("Refresh XBL")
        self._name_change_button = QPushButton("Change Name")
        self._skin_change_button = QPushButton("Change Skin")
        self._install_multi_thread_button = QPushButton("Launch")

        for i in minecraft_launcher_lib.utils.get_version_list():
            if i["type"] == "release":
               self._version_combo_box.addItem(i["id"])

        self._install_thread.finished.connect(self._install_thread_finished)
        self._xbl_refresh_button.clicked.connect(self._xbl_refresh_button_clicked)
        self._name_change_button.clicked.connect(self._name_change_button_clicked)
        #self._skin_change_button.clicked.connect(self._skin_change_button_clicked)
        self._install_multi_thread_button.clicked.connect(self._install_minecraft_multi_thread)
        self._name_change_window = NameChangeWindow()
        self._name_change_window.change_button.clicked.connect(self.change_name)
        self._name_change_window.back_button.clicked.connect(self._name_change_window.close)
        self._skin_change_window = SkinChangeWindow()
        self._skin_change_button.clicked.connect(self._skin_change_button_clicked)
        self._skin_change_window.set_skin_button.clicked.connect(self.skin_change)

        ssid_layout = QHBoxLayout()
        ssid_layout.addWidget(self._ssid_edit)
        
        azureless_layout = QHBoxLayout()
        azureless_layout.addWidget(self._xbl_edit)
        azureless_layout.addWidget(self._xbl_refresh_button)

        change_layout = QHBoxLayout()
        change_layout.addWidget(self._skin_change_button)
        change_layout.addWidget(self._name_change_button)
        

        form_layout = QFormLayout()
        form_layout.addRow(QLabel("Version:"), self._version_combo_box)
        form_layout.addRow(QLabel("SSID:"), ssid_layout)
        form_layout.addRow(QLabel("XBL Token:"), azureless_layout)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self._install_multi_thread_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addLayout(change_layout)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)
        self.setWindowTitle("Rocket Launcher")
        self.setWindowIcon(QtGui.QIcon('logo.png'))

    def _install_thread_finished(self) -> None:
        self._install_multi_thread_button.setEnabled(True)

    def display_error_message(self) -> None:
        QMessageBox.information(self, "Error", "An unexpected error occured!")

    def _xbl_refresh_button_clicked(self) -> None:
        try:
            xbl = self._xbl_edit.text()
            xstsuserhash = getxstsuserhash(xbl)
            ssid = getssid(xstsuserhash[0], xstsuserhash[1])
            self._ssid_edit.setText(ssid)

        except Exception as e:
            print(e)
            self.display_error_message()

    def _name_change_button_clicked(self) -> None:
        self._name_change_window.show()

    def change_name(self):
        new_name = self._name_change_window.new_name_input.text()
        ssid = self._ssid_edit.text()
        headers = {"Authorization": f"Bearer {ssid}"}
        response = requests.put(f"https://api.minecraftservices.com/minecraft/profile/name/{new_name}", headers=headers)
        if response.status_code == 200:
            QMessageBox.information(self, "Name Changed", f"Successfully changed name to {new_name}")
            self._name_change_window.close()
        else:
            self.display_error_message()
            self._name_change_window.close()

    def _skin_change_button_clicked(self) -> None:
        self._skin_change_window.show()

    def skin_change(self) -> None:
        ssid = self._ssid_edit.text()
        skin_url = self._skin_change_window.url_input.text()
        skin_type = self._skin_change_window.skin_type_combo.currentText().lower()
        try:
            headers = {"Authorization": f"Bearer {ssid}", "Content-Type": "application/json"}
            data = {
                "variant": skin_type,
                "url": skin_url
            }
            response = requests.post(f"https://api.minecraftservices.com/minecraft/profile/skins", headers=headers, json=data)
            if response.status_code == 200:
                QMessageBox.information(self, "Skin Changed", f"Successfully changed skin!")
                self._skin_change_window.close()
            else:
                print(response.text)
                self.display_error_message()
                self._skin_change_window.close()
        except Exception as e:
            print(e)

    def _install_minecraft_multi_thread(self) -> None:
        self._install_multi_thread_button.setEnabled(False)

        self._install_thread.set_data(self._version_combo_box.currentText(), minecraft_launcher_lib.utils.get_minecraft_directory(), self._ssid_edit.text())
        self._install_thread.start()

def main():
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()