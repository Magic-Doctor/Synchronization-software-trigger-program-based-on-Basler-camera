from PySide2.QtWidgets import *
from PySide2.QtUiTools import QUiLoader


class SubWindow:

    def __init__(self):

        self.ui_sub = QUiLoader().load('Save_Image.ui')
        self.ui_sub2 = QUiLoader().load('DelayTimeCap.ui')
        self.delay_time = None


        self.file_info = {
            "cam_idx": None,
            "cam_address": None
        }

        self.ui_sub.SaveFileBtn.clicked.connect(self.GetImgAddress)
        self.ui_sub2.DelayButton.clicked.connect(self.GetDelTime)

    def GetImgAddress(self):

        self.file_info["cam_idx"] = self.ui_sub.SavedCamBox.currentIndex()
        file_address = QFileDialog.getExistingDirectory(None, '选择存储文件夹', './',  QFileDialog.ShowDirsOnly)
        self.ui_sub.AddShowLine.setText(file_address)
        self.file_info["cam_address"] = file_address

    def GetDelTime(self):

        self.delay_time = int(self.ui_sub2.DelayTimeText.text())

