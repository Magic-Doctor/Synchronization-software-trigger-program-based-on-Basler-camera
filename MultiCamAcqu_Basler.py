'''

/***************** Basler相机 同步采集程序 ****************/

'''
import time

from PySide2.QtWidgets import *
from PySide2.QtUiTools import QUiLoader
from PySide2.QtGui import *
from PySide2.QtCore import Qt
from PySide2.QtCore import QRect


from pypylon import genicam
from pypylon import pylon

from threading import Thread
import cv2 as cv
# import matplotlib.pyplot as plt

import sys

from MultiCamAcqu_window2 import SubWindow # 加载子窗口


class MainWindow(SubWindow):

    def __init__(self):

        super().__init__()

        # 从文件中加载UI定义

        # 从 UI 定义中动态 创建一个相应的窗口对象
        self.ui = QUiLoader().load('MultiCam_Acqu.ui')

        self.tlFactory = None # 实例化容器
        self.cameras = None # 像机对象列表
        self.cam_name = [] # 像机名字列表
        self.lab_object = [] # 标签显示列表
        self.img_count = [] # 图片个数计数器
        self.switch = True # 像机窗口开关判断器
        self.frame_rate = None # 帧率
        self.OffsetFromMaster = [] # 同步时差
        ####
        self.Time = []
        self.Time_stamp_d = []
        ####

        self.DeviceShow()
        self.__InitWidgetSetting()

        self.ui.DeviceControBtn.clicked.connect(self.DeviceOpenClose)
        self.ui.ImgAcquBtn.clicked.connect(self.IssueImgAcqu)
        self.ui.ExposureSlider.valueChanged.connect(self.__ExpousreSlider)
        self.ui.ExposureLE.editingFinished.connect(self.__ExposureText)
        self.ui.AddressSettingBtn.triggered.connect(self.ImgSaveWindow)
        self.ui.DelayTimeTrig.triggered.connect(self.DelayTimeSetting)
        self.ui.PTPSwitch.stateChanged.connect(self.__SynShresholdEnabled)
        self.ui.ExitSettingBtn.triggered.connect(self.WindowClose)

        self.ui_sub.SaveBtn.clicked.connect(self.SaveImgAddress)

    # 列表显示已连接的像机
    def DeviceShow(self):

        # Get the transport layer factory.
        self.tlFactory = pylon.TlFactory.GetInstance()
        # Get all attached devices and exit application if no device is found.
        devices = self.tlFactory.EnumerateDevices()

        # Create an array of instant cameras for the found devices
        self.cameras = pylon.InstantCameraArray(len(devices))

        # Create and attach all Pylon Devices.
        for i, cam in enumerate(self.cameras):
            cam.Attach(self.tlFactory.CreateDevice(devices[i]))

            self.cam_name.append(cam.GetDeviceInfo().GetModelName() + '-' + str(i+1))
            self.img_count.append(0)
            self.ui.DeviceTable.insertRow(i) # 插入一行单元格
            self.ui.DeviceTable.setItem(i,0, QTableWidgetItem(self.cam_name[i])) # 像机名称显示在第一列
            self.ui.DeviceTable.setItem(i,1, QTableWidgetItem('(未设置)')) # 像机地址显示在第二列


         #self.ui.DeviceTable.setItem(0,1, QTableWidgetItem('C:\\Users\86152\Desktop\image\cam_1'))
         #self.ui.DeviceTable.setItem(1,1, QTableWidgetItem('C:\\Users\86152\Desktop\image\cam_2'))


        '''
        设置表格项需要导入 QTableWidgetItem类 写入单元格text:
        法1: 实例化Item = QTableWidgetItem()  -> 写入text Item.text('aa') -> 给予属性 表格对象Name.setItem(row.column,Item)
        法2: 表格对象Name.setItem(row,column,QTableWidgetItem('aa'))
        
        '''

    # 像机打开与关闭
    def DeviceOpenClose(self):

        print('激活了！')
        # 全部打开
        if self.ui.DeviceControlBox.currentIndex() == 0:

            if self.switch:

                for idx, cam in enumerate(self.cameras):

                    img_label = QLabel()
                    self.lab_object.append(img_label)
                    self.ui.MultiCamWindow.addTab(img_label, self.cam_name[idx])

                self.ui.ImgAcquBox.setEnabled(True)
                self.ui.ImgAcquBtn.setEnabled(True)
                self.ui.ImgAcquBox.setItemData(0, 1|32, Qt.UserRole - 1)
                self.ui.ImgAcquBox.setItemData(1, 1|32, Qt.UserRole - 1)
                self.ui.ImgAcquBox.setItemData(2, 1|32, Qt.UserRole - 1)
                self.switch = False

            else:

                QMessageBox.warning(
                    self.ui,
                    '异常',
                    '像机窗口已打开！')


        # 全部关闭
        if self.ui.DeviceControlBox.currentIndex() == 1:

            if not self.switch:


                self.cameras.StopGrabbing()
                self.cameras.Close()
                self.ui.MultiCamWindow.clear()

                self.ui.ImgAcquBox.setEnabled(False)
                self.ui.ImgAcquBtn.setEnabled(False)
                self.ui.ImgWidthLE.setEnabled(True)
                self.ui.ImgHeightLE.setEnabled(True)

                self.switch = True

                self.lab_object = []  # 重置标签对象
                self.img_count = [1]*len(self.img_count)  # 重置图片采集个数

            else:

                QMessageBox.warning(
                    self.ui,
                    '异常',
                    '像机窗口已关闭！')

    # 窗口初始加载设置
    def __InitWidgetSetting(self):

        self.ui.DeviceTable.setColumnWidth(0, 150)
        self.ui.DeviceTable.setColumnWidth(1, 300) # 设置单元格宽度
        self.ui.ImgAcquBox.setEnabled(False)
        self.ui.ImgAcquBtn.setEnabled(False) # 先禁止同步采集选项
        self.ui.SynOffShd.setEnabled(False)  # 禁止PTP阈值框

        '''
          QAbstractSlider类调用没有响应 因此调用其子类QSlider
        '''
        self.ui.ExposureLE.setText('30000')
        self.ui.ExposureSlider.setSliderPosition(30000)

        self.ui.ImgWidthLE.setText('5484') # 图片宽度（默认最大值）
        self.ui.ImgHeightLE.setText('3660') # 图像高度（默认最大值）
        self.ui.FrameTimeLE.setText('30') # 采集帧率（默认值）

        self.ui_sub.SavedCamBox.addItems(self.cam_name) # 将像机名称加载到子窗口

    # 曝光时间滑动条调节
    def __ExpousreSlider(self):

        try:

            for idx, cam in enumerate(self.cameras):

                # 设置图像曝光时间
                cam.ExposureTimeAbs.SetValue(int(self.ui.ExposureSlider.value()))

        except:

            pass

        finally:

            self.ui.ExposureLE.setText(str(self.ui.ExposureSlider.value()))

    # 曝光时间文本调节
    def __ExposureText(self):

        try:

            for idx, cam in enumerate(self.cameras):

                # 设置图像曝光时间
                cam.ExposureTimeAbs.SetValue(int(self.ui.ExposureLE.text()))

        except:

            pass

        finally:

            self.ui.ExposureSlider.setSliderPosition(int(self.ui.ExposureLE.text()))

    # 同步时差阈值配置
    def __SynShresholdEnabled(self):

        if self.ui.PTPSwitch.isChecked():

            self.ui.SynOffShd.setEnabled(True)

        else:

            self.ui.SynOffShd.setEnabled(False)

    # 执行图像采集
    def IssueImgAcqu(self):

        self.ui.ImgWidthLE.setEnabled(False)
        self.ui.ImgHeightLE.setEnabled(False) # 让像机分辨率不可编辑（采集后像机分辨率已经不能修改）

        # 自由连采
        if self.ui.ImgAcquBox.currentIndex() == 0:

            # 禁止其他选项可选
            self.ui.ImgAcquBox.setItemData(1,0,Qt.UserRole - 1)
            self.ui.ImgAcquBox.setItemData(2,0,Qt.UserRole - 1)

            if not self.cameras.IsGrabbing():

                # 执行
                self.__FreeRunningSetting()


                '''
                开启新线程采集图片
                在新线程中计算帧率
                
                '''
                # 开启新线程采集图片
                def __FreeRunningMultiThread():

                    # 图片处理
                    while True:

                        clock = time.time()

                        self.__Grab(False)
                        self.frame_rate = int(1/(time.time() - clock))
                        self.ui.fraRate.setText(str(self.frame_rate)+' (帧)') # 显示帧率


                thread = Thread(target=__FreeRunningMultiThread)
                thread.start()

            else:

                QMessageBox.warning(
                    self.ui,
                    '提示',
                    '像机正在进行自由采集！')

        # 同步单采
        if self.ui.ImgAcquBox.currentIndex() == 1:

            # 禁止其他选项可选
            self.ui.ImgAcquBox.setItemData(0,0,Qt.UserRole - 1)
            self.ui.ImgAcquBox.setItemData(2,0,Qt.UserRole - 1)
            self.ui.fraRate.setText(str(0) + ' (帧)')  # 帧率显示为0

            '''
            同步单采需要多次点击，但点击后__SynAcqu方法会反复执行，其中的像机同步配置，帧率，图像尺寸等参数在第一次执行时均已配置完成
            因此一旦同步单采完成第一次采集后，不需要再执行__SynAcqu方法，只考虑可能变化的曝光时间
            
            注意：像机同步配置完成后，图像分辨率不能再修改，会报错
            '''

            if not self.cameras.IsGrabbing():

                self.__SynAcqu()

            # else:
            #
            #     for idx, cam in enumerate(self.cameras):
            #
            #         # 设置图像曝光时间
            #         cam.ExposureTimeAbs.SetValue(int(self.ui.ExposureLE.text()))
            #
            #     print('设置成功')

            for i in range(len(self.img_count)):
                self.img_count[i] += 1  # 更新图像编号

            # 激发触发命令(无等待时间)
            self.act_cmd.IssueNoWait()


            # 激发触发命令(有等待时间)
            # timeout_ms = 1000
            # expected_results = 1
            # ok, results = act_cmd.IssueWait(timeout_ms, expected_results)

            # 图像处理
            self.__Grab(True)

        # 同步连采
        if self.ui.ImgAcquBox.currentIndex() == 2:

            # 禁止其他选项可选
            self.ui.ImgAcquBox.setItemData(0,0,Qt.UserRole - 1)
            self.ui.ImgAcquBox.setItemData(1,0,Qt.UserRole - 1)

            if not self.cameras.IsGrabbing():

                self.__SynAcqu()

                # 开启新线程采集图片
                def __SynMultiThread():

                    while True:

                        for i in range(len(self.img_count)):
                            self.img_count[i] += 1 # 更新图像编号

                        # 激发触发命令(无等待时间)
                        self.act_cmd.IssueNoWait()

                        # clock = time.time()

                        # 图像处理
                        # 相机数据传输不稳定时的异常处理
                        try:
                            self.__Grab(True)
                        # self.frame_rate = int(1/(time.time() - clock))
                        # self.ui.fraRate.setText(str(self.frame_rate)+' (帧)') # 显示帧率
                        except:

                            pass


                        if self.delay_time != None:
                            time.sleep(self.delay_time)
                            print(self.delay_time)


                thread = Thread(target=__SynMultiThread)
                thread.start()

                # time_b = time.time()
                # while True:
                #     # # 激发触发命令(无等待时间)
                #     # self.act_cmd.IssueNoWait()
                #
                #     # clock = time.time()
                #
                #     #####
                #     time_d = 0
                #     time_1 = time.time()
                #     #####
                #
                #     while time_d < 1:
                #         self.act_cmd.IssueNoWait()
                #         # 图像处理
                #         self.__Grab(True)
                #         # self.frame_rate = int(1/(time.time() - clock))
                #         # self.ui.fraRate.setText(str(self.frame_rate)+' (帧)') # 显示帧率
                #         time_d = time.time() - time_1
                #         self.Time.append(time.time() - time_b)
                #
                #     plt.plot(self.Time, self.Time_stamp_d)
                #     plt.show(block=False)
                #     plt.pause(1)
                #     plt.close()

            else:

                QMessageBox.warning(
                    self.ui,
                    '提示',
                    '像机正在进行同步连续采集！')

    # 自由采集配置
    def __FreeRunningSetting(self):

        for idx, cam in enumerate(self.cameras):
            cam.Open()
            print('像机已经打开')

            # 设置采集帧率
            cam.AcquisitionFrameRateEnable.SetValue(True)
            cam.AcquisitionFrameRateAbs.SetValue(int(self.ui.FrameTimeLE.text()))

            # 设置图像分辨率
            cam.Width = int(self.ui.ImgWidthLE.text())
            cam.Height = int(self.ui.ImgHeightLE.text())

            # 设置图像曝光时间
            cam.ExposureTimeAbs.SetValue(int(self.ui.ExposureLE.text()))

        # 开始自由连采
        self.cameras.StartGrabbing(pylon.GrabStrategy_LatestImages)
        cam.GevTimestampControlLatch.Execute()
        #     #
        timestamp = cam.GevTimestampValue.GetValue()
        print(timestamp)

    # 同步采集配置
    def __SynAcqu(self):

        # Create a suitable ActionCommand object. For that a GigETransportLayer object
        # is needed.
        gige_tl = self.tlFactory.CreateTl('BaslerGigE')
        action_key = 0x4711
        group_key = 0x112233
        group_mask = pylon.AllGroupMask
        for idx, cam in enumerate(self.cameras):
            # Initiate automatic configuration by registering ActionTriggerConfiguration.
            cam.RegisterConfiguration(
                pylon.ActionTriggerConfiguration(action_key, group_key, group_mask),
                pylon.RegistrationMode_Append,
                pylon.Cleanup_Delete
            )

            cam.Open()
            print('像机已经打开')

            # 设置采集帧率
            cam.AcquisitionFrameRateEnable.SetValue(True)
            cam.AcquisitionFrameRateAbs.SetValue(int(self.ui.FrameTimeLE.text()))

            # 设置触发模式
            cam.TriggerSelector.SetValue('FrameStart')
            cam.TriggerMode.SetValue('On')
            cam.TriggerSource.SetValue("Action1")

            # 设置图像分辨率
            cam.Width = int(self.ui.ImgWidthLE.text())
            cam.Height = int(self.ui.ImgHeightLE.text())

            # 设置图像曝光时间
            cam.ExposureTimeAbs.SetValue(int(self.ui.ExposureLE.text()))


            #     cam.GevTimestampControlLatch.Execute()
            #     #
            #     timestamp = cam.GevTimestampValue.GetValue()
                # print(timestamp)

            cam.GevIEEE1588.SetValue(True); # 开启PTP协议
            print('时间协议开启')


        self.cameras.StartGrabbing(pylon.GrabStrategy_LatestImages)

        if self.ui.PTPSwitch.isChecked():

            # self.__PTPStatusChecking()

            self.act_cmd = gige_tl.ScheduledActionCommand(action_key, group_key, group_mask, 0)

        else:

            # Using default value of "255.255.255.255" for fourth
            # parameter 'broadcastAddress'.
            self.act_cmd = gige_tl.ActionCommand(action_key, group_key, group_mask)

    # PTP同步状态检查
    def __PTPStatusChecking(self):

        for idx, cam in enumerate(self.cameras):

        # self.OffsetFromMaster = [None] * len(self.cam_name)

            if idx == 1:
                # print('GevIEEE1588DataSetLatch 执行成功')

                Time = []
                offset = []

                time_b = time.time()
                while True:

                    time_d = 0
                    time_1 = time.time()

                    while time_d < 1:

                        cam.GevIEEE1588DataSetLatch.Execute()
                        Time.append(time.time() - time_b)
                        offset.append(cam.GevIEEE1588OffsetFromMaster.Value)

                        time_d = time.time() - time_1

                    plt.plot(Time, offset)
                    plt.show(block=False)
                    plt.pause(1)
                    plt.close()

            # print(cam.GevIEEE1588Status())

        # self.OffsetFromMaster[idx] = cam.GevIEEE1588OffsetFromMaster

    # 抓取在像机缓存中的图片
    def __Grab(self, synJug):

        # Create the converter and set parameters.
        converter = pylon.ImageFormatConverter()
        converter.OutputPixelFormat = pylon.PixelType_Mono8
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        time_stamp = []

        for idx, cam in enumerate(self.cameras):

            result = cam.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            image = converter.Convert(result)

            image_pixel = image.GetArray()
            img = cv.cvtColor(image_pixel, cv.COLOR_BGR2RGB)

            video = QImage(img.data, img.shape[1], img.shape[0], img.shape[1] * 3, QImage.Format_RGB888) # 图像对象

            # self.lab_object[idx].setPixmap(QPixmap('C:\\Users\86152\Desktop\L1.bmp'))  # 在label中显示图像
            self.lab_object[idx].setPixmap(QPixmap.fromImage(video).scaledToHeight(
                self.lab_object[idx].geometry().height()))  # 在label中显示图像
            print('图像显示成功！')

            '''
            验证时间戳与result代码无关（只需要time.sleep）
            '''

            time_stamp.append(result.TimeStamp)

            item = QTableWidgetItem()
            address = self.ui.DeviceTable.item(idx,1).text()

            if address == '(未设置)' and synJug:

                continue

            elif synJug:
                try:

                    filename = f"{address}/image_{self.img_count[idx]}.bmp"
                    image.Save(pylon.ImageFileFormat_Bmp, filename)
                    # self.img_count[idx] += 1 # 每个像机采集图片后计数器更新

                except:

                    QMessageBox.warning(
                        self.ui,
                        '图片存储异常',
                        f'像机{self.cam_name[idx]}图片存储失败，检查存储地址是否有误!')

        # self.Time_stamp_d.append(time_stamp[1]-time_stamp[0])


    # 图片存储窗口
    def ImgSaveWindow(self):

        self.ui_sub.show() # 显示子窗口

    # 延时设置窗口
    def DelayTimeSetting(self):
        self.ui_sub2.show() # 显示延时设置窗口


    # 存储图片地址
    def SaveImgAddress(self):

        '''

        先判断是否选择了存储地址，若未选择，则点击“确定”按钮报出异常

        '''
        if not self.file_info["cam_address"] == None:

            self.ui.DeviceTable.setItem(self.file_info["cam_idx"], 1, QTableWidgetItem(self.file_info["cam_address"]))

            QMessageBox.information(None, '消息', '存储完成！', buttons=QMessageBox.Ok)

        else:

            QMessageBox.warning(
                None,
                '存储异常',
                '请选择存储地址！')

    # 窗口退出
    def WindowClose(self):

        self.ui.close()


if __name__ == '__main__':

    app = QApplication([])
    # app.setStyle(QStyleFactory.create('Fusion'))
    main_window = MainWindow()
    main_window.ui.show()
    app.exec_()