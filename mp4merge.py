# coding: utf8
import ConfigParser
import os
import wx
import threading
import subprocess
import filetype
import winreg
import shutil
import commands

class workerThread(threading.Thread):
    def __init__(self, threadNum, window, obj):
        """
        :param threadNum: 进程数
        :param window: wxFrame
        :param obj: 得到的目录或者文件路径
        这个类是视频合成的类，启动一个视频合成的进程，完成用户所选择的目录或者单文件的合成视频
        """
        threading.Thread.__init__(self)
        self.threadNum = threadNum
        self.window = window
        self.obj = obj
        self.timeToQuit = threading.Event()
        self.timeToQuit.clear()
        self.messageCount = 100
        self.messageDelay = 0
        self.getConfigDir()
        self.cf = ConfigParser.ConfigParser()
        self.cf.read(self.config)

        self.headVideo_unicode = self.cf.get('video', 'head_video').decode("utf-8")
        self.tailVideo_unicode = self.cf.get('video', 'tail_video').decode("utf-8")
        self.outputDir_unicode = self.cf.get('dir', 'output_dir').decode("utf-8")
        self.headVideo = self.headVideo_unicode.encode("gbk")
        self.tailVideo = self.tailVideo_unicode.encode("gbk")
        self.outputDir = self.outputDir_unicode.encode("gbk")

    def getConfigDir(self):
        """
        获取配置文件所在的位置，以及视频合成临时目录的位置
        :return:
        """
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders', )
        self.configDir = winreg.QueryValueEx(key, "Personal")[0]
        self.config = self.configDir + '\\mp4merge\\config.ini'
        self.tmpDir_unicode = self.configDir + '\\mp4merge\\temp'
        self.tmpDir = self.tmpDir_unicode.encode("gbk")

    def stop(self):
        """
        停止进程
        :return:
        """
        self.timeToQuit.set()

    def run(self):
        """
        启动合并视频进程
        如果传入的参数是文件，就合成单文件
        如果是目录，那么遍历目录文件，判断文件类型，将文件类型为mp4的文件合成，其他的都跳过
        如果没有选择，那么提示请选择
        :return:
        """
        msg = "test"
        if os.path.isfile(self.obj):
            pathName = self.obj
            fileName = os.path.basename(self.obj)
            self.transFile(pathName, fileName)
        elif os.path.isdir(self.obj):
            fileList = os.listdir(self.obj)
            if len(fileList) == 0:
                self.transCode("当前目录为空！")
                self.cmd = 'echo ' + self.content_gbk
                self.runCmd(self.cmd)
            else:
                for i in fileList:
                    j = self.obj + '\\' + i
                    if os.path.isfile(j):
                        fileType = filetype.guess(j)
                        if fileType is None:
                            self.transCode("文件类型不是MP4，跳过")
                            self.cmd = 'echo ' + i + self.content_gbk
                            self.runCmd(self.cmd)
                            continue
                        elif fileType.extension == 'mp4':
                            self.transFile(j, i)
                        else:
                            self.transCode("文件类型不是MP4，跳过")
                            self.cmd = 'echo ' + i + self.content_gbk
                            self.runCmd(self.cmd)
                            continue
                    else:
                        self.transCode("跳过目录")
                        self.cmd = 'echo ' + self.content_gbk + j
                        self.runCmd(self.cmd)
        else:
            self.transCode("当前未选择任何文件或目录！请打开一个MP4文件或者包含MP4文件的目录！")
            self.cmd = 'echo ' + self.content_gbk
            self.runCmd(self.cmd)

        wx.CallAfter(self.window.threadFinished, self)

    def transCode(self, content):
        """
        这是转码的功能，由于中文版windows某些cmd调用必须用gbk
        先把utf-8转为unicode，在把unicode转为gbk
        :param content:
        :return:
        """
        self.content = content
        self.content_unicode = self.content.decode("utf-8")
        self.content_gbk = self.content_unicode.encode("gbk")

    def runCmd(self, cmd):
        """
        运行命令的功能
        在win下运行cmd命令，并把输出以gbk格式打印到面板上，window指定了主程序的功能
        :param cmd:
        :return:
        """
        popenData = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE)
        for i in range(1, self.messageCount + 1):
            getData = unicode(popenData.stdout.readline(), 'gbk')
            self.timeToQuit.wait(self.messageDelay)
            if self.timeToQuit.isSet():
                break
            wx.CallAfter(self.window.logMessage, getData)
        popenData.wait()

    def transFile(self, pathName, fileName):
        """
        这是合成视频的逻辑，现将mp4转为TS视频流，再将视频流合成为mp4
        :param pathName:生成视频的目录
        :param fileName:要添加头部和尾部的视频
        :return:
        """
        realpath = '"' + pathName + '"'
        new_file = '"' + self.outputDir + '\\' + fileName + '"'
        check_file = self.outputDir + '\\' + fileName
        self.cmd = 'echo ----------------------------------------start----------------------------------------'
        self.runCmd(self.cmd)
        self.transCode("开始合成")
        self.cmd = 'echo ' + self.content_gbk + fileName
        self.runCmd(self.cmd)
        self.cmd = 'ffmpeg -i ' + realpath + ' -y -vcodec copy -acodec copy -vbsf h264_mp4toannexb ' + \
                   self.tmpDir + '\\tmp.ts'
        self.runCmd(self.cmd)
        self.cmd = 'ffmpeg -i "concat:' + self.headVideo + '|' + self.tmpDir + '\\tmp.ts' + '|' + self.tailVideo + \
                   '" -y -acodec copy -vcodec copy -absf aac_adtstoasc ' + new_file
        self.runCmd(self.cmd)

        if os.path.isfile(check_file):
            self.transCode("合成成功！")
            self.cmd = 'echo ' + fileName + self.content_gbk
            self.runCmd(self.cmd)
        else:
            self.transCode("合成失败！")
            self.cmd = 'echo ' + fileName + self.content_gbk
            self.runCmd(self.cmd)
        self.cmd = 'echo -----------------------------------------end----------------------------------------'
        self.runCmd(self.cmd)

class aboutDialog(wx.Dialog):
    def __init__(self, parent, title, txt1, txt2, txt3):
        """
        这个类主要是写了关于作者，版本的对话框，不多做解释
        :param title: 关于对话框的标题
        :param label: 关于对话框的内容
        """
        super(aboutDialog, self).__init__(parent, title=title, size=(250, 170), style=wx.DEFAULT_DIALOG_STYLE)
        panel = wx.Panel(self)
        self.txt1 = wx.StaticText(panel, label=txt1)
        self.txt2 = wx.StaticText(panel, label=txt2)
        self.txt3 = wx.StaticText(panel, label=txt3)
        self.btn = wx.Button(panel, wx.ID_OK, label="确定")
        aboutInner1 = wx.BoxSizer(wx.HORIZONTAL)
        aboutInner2 = wx.BoxSizer(wx.HORIZONTAL)
        aboutInner3 = wx.BoxSizer(wx.HORIZONTAL)
        aboutInner1.Add(self.txt1, 0, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=20)
        aboutInner2.Add(self.txt2, 0, flag=wx.LEFT | wx.RIGHT, border=20)
        aboutInner3.Add(self.txt3, 0, flag=wx.LEFT | wx.RIGHT, border=20)
        aboutMain = wx.BoxSizer(wx.VERTICAL)
        aboutMain.Add(aboutInner1, 0, flag=wx.EXPAND | wx.ALL)
        aboutMain.Add(aboutInner2, 0, flag=wx.EXPAND | wx.ALL)
        aboutMain.Add(aboutInner3, 0, flag=wx.EXPAND | wx.ALL)
        aboutMain.Add(self.btn, 0, flag=wx.ALIGN_CENTER | wx.TOP | wx.LEFT | wx.RIGHT, border=20)
        panel.SetSizer(aboutMain)

class viewVideo(wx.Dialog):
    def __init__(self, parent, title):
        """
        这个类主要实现了查看当前定义的头部和尾部视频的对话框
        :param parent:
        :param title:
        """
        super(viewVideo, self).__init__(parent, title=title, size=(500, 253), style=wx.DEFAULT_DIALOG_STYLE)
        panel = wx.Panel(self)
        self.getConfigDir()
        self.cf = ConfigParser.ConfigParser()
        self.cf.read(self.config)
        self.headVideo_unicode = self.cf.get('video', 'head_video').decode("utf-8")
        self.tailVideo_unicode = self.cf.get('video', 'tail_video').decode("utf-8")
        self.headVideo = self.headVideo_unicode.encode("gbk")
        self.tailVideo = self.tailVideo_unicode.encode("gbk")

        video1 = wx.TextCtrl(panel, style=wx.TE_READONLY)
        video2 = wx.TextCtrl(panel, style=wx.TE_READONLY)
        openBtn1 = wx.Button(panel, label="查看")
        openBtn2 = wx.Button(panel, label="查看")
        returnBtn = wx.Button(panel, wx.ID_OK, label="返回")
        videoInner1 = wx.BoxSizer(wx.HORIZONTAL)
        videoInner2 = wx.BoxSizer(wx.HORIZONTAL)
        text1 = wx.StaticBox(panel, -1, '当前头部视频')
        text2 = wx.StaticBox(panel, -1, '当前尾部视频')
        textSizer1 = wx.StaticBoxSizer(text1, wx.VERTICAL)
        textSizer2 = wx.StaticBoxSizer(text2, wx.VERTICAL)

        videoInner1.Add(video1, 1, flag=wx.ALL | wx.EXPAND, border=5)
        videoInner1.Add(openBtn1, 0, flag=wx.ALL, border=5)
        videoInner2.Add(video2, 1, flag=wx.ALL | wx.EXPAND, border=5)
        videoInner2.Add(openBtn2, 0, flag=wx.ALL, border=5)
        textSizer1.Add(videoInner1, 0, flag=wx.ALL | wx.EXPAND, border=5)
        textSizer2.Add(videoInner2, 0, flag=wx.ALL | wx.EXPAND, border=5)
        videoMain = wx.BoxSizer(wx.VERTICAL)
        videoMain.Add(textSizer1, 0, flag=wx.ALL | wx.EXPAND, border=5)
        videoMain.Add(textSizer2, 0, flag=wx.ALL | wx.EXPAND, border=5)
        videoMain.Add(returnBtn, 0, flag=wx.ALIGN_CENTER | wx.ALL, border=5)

        panel.SetSizer(videoMain)

        self.Bind(wx.EVT_BUTTON, self.openVideo1, openBtn1)
        self.Bind(wx.EVT_BUTTON, self.openVideo2, openBtn2)

        self.setVideoPath(video1, self.headVideo)
        self.setVideoPath(video2, self.tailVideo)

    def getConfigDir(self):
        """
        获取配置文件位置
        :return:
        """
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders', )
        self.configDir = winreg.QueryValueEx(key, "Personal")[0]
        self.config = self.configDir + '\\mp4merge\\config.ini'

    def openVideo1(self, evt):
        """
        打开头部文件
        :param evt:
        :return:
        """
        try:
            os.startfile(self.headVideo)
        except WindowsError:
            self.onMsgBox(self)
        else:
            pass

    def openVideo2(self, evt):
        """
        打开尾部文件
        :param evt:
        :return:
        """
        try:
            os.startfile(self.tailVideo)
        except WindowsError:
            self.onMsgBox(self)
        else:
            pass

    def setVideoPath(self, txt, fileName):
        """
        在txt框中显示视频路径
        :param txt:
        :param fileName:
        :return:
        """
        self.txt = txt
        fileName_gbk = fileName.decode("gbk")
        self.txt.SetValue(fileName_gbk)

    def onMsgBox(self, evt):
        """
        不存在就提示
        :param evt:
        :return:
        """
        wx.MessageBox("文件不存在，请重新配置！", "提示", wx.OK | wx.ICON_INFORMATION)

class createTsVideo(wx.Dialog):
    def __init__(self, parent, title):
        """
        这个类主要是用户生成头部和尾部文件的对话框
        :param parent:
        :param title:
        """
        super(createTsVideo, self).__init__(parent, title=title, size=(500, 170), style=wx.DEFAULT_DIALOG_STYLE)
        panel = wx.Panel(self)
        self.getConfigDir()
        self.cf = ConfigParser.ConfigParser()
        self.cf.read(self.config)
        self.outputDir_unicode = self.cf.get('dir', 'output_dir').decode("utf-8")
        self.outputDir = self.outputDir_unicode.encode("gbk")

        self.videoPathText = wx.TextCtrl(panel, style=wx.TE_READONLY)
        self.selectVideoBtn = wx.Button(panel, label="选择")
        myText = wx.StaticBox(panel, 0, label="生成头部尾部视频")
        self.openVideoPathBtn = wx.Button(panel, label="查看生成视频")
        self.createVideoBtn = wx.Button(panel, label="生成TS视频")
        self.returnMainPanelBtn = wx.Button(panel, wx.ID_OK, label="返回")

        myTextSizer = wx.StaticBoxSizer(myText, wx.VERTICAL)
        textInner = wx.BoxSizer(wx.HORIZONTAL)
        btnInner = wx.BoxSizer(wx.HORIZONTAL)
        textInner.Add(self.videoPathText, 1, flag=wx.ALL | wx.EXPAND, border=5)
        textInner.Add(self.selectVideoBtn, 0, flag=wx.ALL, border=5)
        btnInner.Add(self.openVideoPathBtn, 0, flag=wx.ALL, border=5)
        btnInner.Add(self.createVideoBtn, 0, flag=wx.ALL, border=5)
        btnInner.Add(self.returnMainPanelBtn, 0, flag=wx.ALL, border=5)
        myTextSizer.Add(textInner, 0, flag=wx.ALL | wx.EXPAND, border=5)
        createTsVideoMain = wx.BoxSizer(wx.VERTICAL)
        createTsVideoMain.Add(myTextSizer, 0, flag=wx.ALL | wx.EXPAND, border=5)
        createTsVideoMain.Add(btnInner, 0, flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        panel.SetSizer(createTsVideoMain)

        self.createVideoBtn.Disable()
        self.openVideoPathBtn.Disable()

        self.Bind(wx.EVT_BUTTON, self.openFile, self.selectVideoBtn)
        self.Bind(wx.EVT_BUTTON, self.createVideo, self.createVideoBtn)
        self.Bind(wx.EVT_BUTTON, self.openVideoDir, self.openVideoPathBtn)

    def getConfigDir(self):
        """
        获取配置文件位置，默认视频输出目录位置
        :return:
        """
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders', )
        self.configDir = winreg.QueryValueEx(key, "Personal")[0]
        self.config = self.configDir + '\\mp4merge\\config.ini'

    def openVideoDir(self, evt):
        """
        菜单
        打开输出视频目录
        :param evt:
        :return:
        """
        cf = ConfigParser.ConfigParser()
        cf.read(self.config)
        outPutDir_unicode = cf.get('dir', 'output_dir').decode("utf-8")
        outPutDir = outPutDir_unicode.encode("gbk")
        pathName = self.videoPath.encode("gbk")
        fileName = os.path.basename(pathName)[:-4] + '.ts'
        outPutVideo = outPutDir + '\\' + fileName
        os.popen("explorer /select,"+ outPutVideo)

    def openFile(self,evt):
        """
        选择文件对话框
        :param evt:
        :return:
        """
        dlg = wx.FileDialog(self, "选择文件", "", "", "MP4 files (*.mp4)|*.mp4", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.videoPath = dlg.GetPath()
        else:
            return
        self.videoPathText.SetValue(self.videoPath)
        dlg.Destroy()
        self.createVideoBtn.Enable()
        self.openVideoPathBtn.Disable()

    def runCmd(self, cmd):
        """
        运行命令的功能
        在win下运行cmd命令，并把输出以gbk格式打印到面板上，window指定了主程序的功能
        :param cmd:
        :return:
        """
        process = subprocess.Popen(self.cmd, shell=True)
        process.wait()

    def convertVideo(self, pathName, fileName):
        """
        生成ts文件的命令
        :param pathName: 文件详细地址
        :param fileName: 文件名（不含后缀）
        :return:
        """
        realpath = '"' + pathName + '"'
        new_file = '"' + self.outputDir + '\\' + fileName + '.ts"'
        check_file = self.outputDir + '\\' + fileName + '.ts'
        self.cmd = 'ffmpeg -i ' + realpath + ' -y -vcodec copy -acodec copy -vbsf h264_mp4toannexb ' + new_file
        self.runCmd(self.cmd)
        if os.path.isfile(check_file):
            self.onMsgBox1()
            self.openVideoPathBtn.Enable()
        else:
            self.onMsgBox2()

    def createVideo(self,evt):
        """
        生成ts格式文件
        :param evt:
        :return:
        """
        pathName = self.videoPath.encode("gbk")
        fileName = os.path.basename(pathName)[:-4]
        self.convertVideo(pathName, fileName)

    def onMsgBox1(self):
        """
        任务完成提示
        :param evt:
        :return:
        """
        wx.MessageBox("任务已完成", "提示", wx.OK | wx.ICON_INFORMATION)

    def onMsgBox2(self):
        """
        任务完成提示
        :param evt:
        :return:
        """
        wx.MessageBox("任务失败", "提示", wx.OK | wx.ICON_ERROR)

class configFile(wx.Dialog):
    def __init__(self, parent, title):
        """
        这个类主要是用户自己定义配置文件的对话框
        :param parent:
        :param title:
        """
        super(configFile, self).__init__(parent, title=title, size=(500, 270), style=wx.DEFAULT_DIALOG_STYLE)
        self.video1Path = ''
        self.video2Path = ''
        self.dirPath = ''
        panel = wx.Panel(self)
        self.getConfigDir()
        self.cf = ConfigParser.ConfigParser()
        self.cf.read(self.config)
        self.headVideo_unicode = self.cf.get('video', 'head_video').decode("utf-8")
        self.tailVideo_unicode = self.cf.get('video', 'tail_video').decode("utf-8")
        self.outputDir_unicode = self.cf.get('dir', 'output_dir').decode("utf-8")
        self.headVideo = self.headVideo_unicode.encode("gbk")
        self.tailVideo = self.tailVideo_unicode.encode("gbk")
        self.outputDir = self.outputDir_unicode.encode("gbk")

        headText = wx.StaticText(panel, label="头部设置")
        tailText = wx.StaticText(panel, label="尾部设置")
        dirStatic = wx.StaticText(panel, label="输出目录")
        self.video1 = wx.TextCtrl(panel, style=wx.TE_READONLY)
        self.video2 = wx.TextCtrl(panel, style=wx.TE_READONLY)
        self.dirText = wx.TextCtrl(panel, style=wx.TE_READONLY)
        self.openBtn1 = wx.Button(panel, label="选择")
        self.openBtn2 = wx.Button(panel, label="选择")
        self.openBtn3 = wx.Button(panel, label="选择")
        self.defaultBtn = wx.Button(panel, label="恢复默认")
        self.configBtn = wx.Button(panel, label="应用")
        self.confirmBtn = wx.Button(panel, label="确定")
        self.returnBtn = wx.Button(panel, wx.ID_OK, label="返回")
        videoInner1 = wx.BoxSizer(wx.HORIZONTAL)
        videoInner2 = wx.BoxSizer(wx.HORIZONTAL)
        dirInner = wx.BoxSizer(wx.HORIZONTAL)
        btnInner = wx.BoxSizer(wx.HORIZONTAL)
        text1 = wx.StaticBox(panel, 0, label="配置选项")
        textSizer = wx.StaticBoxSizer(text1, wx.VERTICAL)
        videoInner1.Add(headText, 0, flag=wx.ALL, border=10)
        videoInner1.Add(self.video1, 1, flag=wx.ALL | wx.EXPAND, border=5)
        videoInner1.Add(self.openBtn1, 0, flag=wx.ALL, border=5)
        videoInner2.Add(tailText, 0, flag=wx.ALL, border=10)
        videoInner2.Add(self.video2, 1, flag=wx.ALL | wx.EXPAND, border=5)
        videoInner2.Add(self.openBtn2, 0, flag=wx.ALL, border=5)
        dirInner.Add(dirStatic, 0, flag=wx.ALL, border=10)
        dirInner.Add(self.dirText, 1, flag=wx.ALL | wx.EXPAND, border=5)
        dirInner.Add(self.openBtn3, 0, flag=wx.ALL, border=5)
        btnInner.Add(self.defaultBtn, 0, flag=wx.ALL, border=5)
        btnInner.Add(self.configBtn, 0, flag=wx.ALL, border=5)
        btnInner.Add(self.confirmBtn, 0, flag=wx.ALL, border=5)
        btnInner.Add(self.returnBtn, 0, flag=wx.ALL, border=5)
        textSizer.Add(videoInner1, 0, flag=wx.ALL | wx.EXPAND, border=5)
        textSizer.Add(videoInner2, 0, flag=wx.ALL | wx.EXPAND, border=5)
        textSizer.Add(dirInner, 0, flag=wx.ALL | wx.EXPAND, border=5)
        videoMain = wx.BoxSizer(wx.VERTICAL)
        videoMain.Add(textSizer, 0, flag=wx.ALL | wx.EXPAND, border=5)
        videoMain.Add(btnInner, 0, flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        panel.SetSizer(videoMain)

        self.configBtn.Disable()

        self.setVideoPath(self.video1, self.headVideo)
        self.setVideoPath(self.video2, self.tailVideo)
        self.setVideoPath(self.dirText, self.outputDir)

        self.Bind(wx.EVT_BUTTON, self.openPath, self.openBtn3)
        self.Bind(wx.EVT_BUTTON, self.openFile1, self.openBtn1)
        self.Bind(wx.EVT_BUTTON, self.openFile2, self.openBtn2)
        self.Bind(wx.EVT_BUTTON, self.configNew, self.configBtn)
        self.Bind(wx.EVT_BUTTON, self.defaultConfig, self.defaultBtn)
        self.Bind(wx.EVT_BUTTON, self.confirmConfig, self.confirmBtn)

    def getConfigDir(self):
        """
        获取配置文件位置，默认视频输出目录位置
        :return:
        """
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders', )
        self.configDir = winreg.QueryValueEx(key, "Personal")[0]
        self.config = self.configDir + '\\mp4merge\\config.ini'
        self.videoDir = self.configDir + '\\video'

    def configNew(self, evt):
        """
        这个是对话框应用按钮的方法
        获取配置文件中的原来的配置
        获取新的配置
        判断新的配置是不是为空，如果为空，那么把原来的值付给它
        把新的配置写到配置文件中
        :param evt:
        :return:
        """
        self.cf.read(self.config)
        self.headVideo = self.cf.get('video', 'head_video')
        self.tailVideo = self.cf.get('video', 'tail_video')
        self.outputDir = self.cf.get('dir', 'output_dir')
        self.newDir = self.dirPath.encode("utf-8")
        self.newVideo1 = self.video1Path.encode("utf-8")
        self.newVideo2 = self.video2Path.encode("utf-8")
        if self.newDir.strip() == '':
            self.newDir = self.outputDir
        if self.newVideo1.strip() == '':
            self.newVideo1 = self.headVideo
        if self.newVideo2.strip() == '':
            self.newVideo2 = self.tailVideo
        self.cf.set('dir', 'output_dir', self.newDir)
        self.cf.set('video', 'head_video', self.newVideo1)
        self.cf.set('video', 'tail_video', self.newVideo2)
        self.cf.write(open(self.config, "w"))
        self.configBtn.Disable()

    def confirmConfig(self, evt):
        """
        这个是对话框确定按钮的方法
        调用应用配置，并关闭对话框
        :param evt:
        :return:
        """
        self.configNew(evt)
        self.Close()

    def defaultConfig(self, evt):
        """
        这个是对话框默认配置按钮的方法
        先把默认的输出目录，头部和尾部视频写到配置文件
        再把显示部分的输出目录，头部和尾部视频更改
        然后把选择事件中的输出目录，头部和尾部视频更改赋值为空值
        最后一步是为了在点击确定的时候确保是默认配置
        :param evt:
        :return:
        """
        self.cf.set('dir', 'output_dir', self.videoDir)
        self.cf.set('video', 'head_video', '1.ts')
        self.cf.set('video', 'tail_video', '3.ts')
        self.cf.write(open(self.config, "w"))
        self.setVideoPath(self.video1, '1.ts')
        self.setVideoPath(self.video2, '3.ts')
        self.setVideoPath(self.dirText, self.videoDir)
        self.dirPath = ''
        self.video1Path = ''
        self.video2Path = ''

    def setVideoPath(self, txt, path):
        """
        显示txt文本框的显示方法
        :param txt:
        :param path:
        :return:
        """
        self.txt = txt
        path_gbk = path.decode("gbk")
        self.txt.SetValue(path_gbk)

    def openPath(self, evt):
        """
        选择输出目录的方法
        :param evt:
        :return:
        """
        dlg = wx.DirDialog(self, "选择目录", style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.dirPath = dlg.GetPath()
        else:
            return
        self.dirText.SetValue(self.dirPath)
        dlg.Destroy()
        self.configBtn.Enable()

    def openFile1(self, evt):
        """
        选择头部视频的方法
        :param evt:
        :return:
        """
        dlg = wx.FileDialog(
            self,
            "选择文件",
            "",
            "",
            "ts files (*.ts)|*.ts",
            wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.video1Path = dlg.GetPath()
        else:
            return
        self.video1.SetValue(self.video1Path)
        dlg.Destroy()
        self.configBtn.Enable()

    def openFile2(self, evt):
        """
        选择尾部视频的方法
        :param evt:
        :return:
        """
        dlg = wx.FileDialog(
            self,
            "选择文件",
            "",
            "",
            "ts files (*.ts)|*.ts",
            wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.video2Path = dlg.GetPath()
        else:
            return
        self.video2.SetValue(self.video2Path)
        dlg.Destroy()
        self.configBtn.Enable()

class myFrame(wx.Frame):
    def __init__(self):
        """
        主程序界面
        """
        wx.Frame.__init__(self, None, title="MP4 Merge", size=(800, 500))
        self.threads = []
        self.count = 0
        self.filePath = ''
        self.getConfigDir()
        self.initConfig()
        # 控件id
        appExit = 1
        appOpenFile = 2
        appOpenDir = 3
        appVersion = 4
        appAuthor = 5
        appVideoDir = 6
        appConfig = 7
        appCat = 8
        appCreate = 9
        # 文件菜单
        menuBar = wx.MenuBar()
        fileMenu = wx.Menu()
        fileExit = wx.MenuItem(fileMenu, appExit, "&退出\tCtrl+Q")
        fileExit.SetBitmap(wx.Bitmap("static/exit.ico"))
        fileOpen = wx.MenuItem(fileMenu, appOpenFile, "&打开文件\tCtrl+O")
        fileOpen.SetBitmap(wx.Bitmap("static/file.ico"))
        dirOpen = wx.MenuItem(fileMenu, appOpenDir, "&打开目录\tCtrl+F")
        dirOpen.SetBitmap(wx.Bitmap("static/filedir.ico"))
        fileVideo = wx.MenuItem(fileMenu, appVideoDir, "&视频生成目录\tCtrl+N")
        fileVideo.SetBitmap(wx.Bitmap("static/filevideodir.ico"))
        fileMenu.Append(fileOpen)
        fileMenu.Append(dirOpen)
        fileMenu.Append(fileVideo)
        fileMenu.Append(fileExit)
        menuBar.Append(fileMenu, "&文件")
        # 选项菜单
        optionMenu = wx.Menu()
        catVideo = wx.MenuItem(optionMenu, appCat, "&视频头尾详情\tCtrl+I")
        catVideo.SetBitmap(wx.Bitmap("static/info.ico"))
        createVideo = wx.MenuItem(optionMenu, appCreate, "&生成头尾工具")
        createVideo.SetBitmap(wx.Bitmap("static/wrench.ico"))
        configVideo = wx.MenuItem(optionMenu, appConfig, "&配置\tCtrl+Alt+S")
        configVideo.SetBitmap(wx.Bitmap("static/config.ico"))
        optionMenu.Append(catVideo)
        optionMenu.Append(createVideo)
        optionMenu.Append(configVideo)
        menuBar.Append(optionMenu, "&选项")
        # 关于菜单
        aboutMenu = wx.Menu()
        aboutVersion = wx.MenuItem(aboutMenu, appVersion, "&版本")
        aboutVersion.SetBitmap(wx.Bitmap("static/version.ico"))
        aboutAuthor = wx.MenuItem(aboutMenu, appAuthor, "&作者")
        aboutAuthor.SetBitmap(wx.Bitmap("static/author.ico"))
        aboutMenu.Append(aboutVersion)
        aboutMenu.Append(aboutAuthor)
        menuBar.Append(aboutMenu, "&关于")
        # 监听事件
        self.SetMenuBar(menuBar)
        self.Bind(wx.EVT_MENU, self.onQuit, id=appExit)
        self.Bind(wx.EVT_MENU, self.openFile, id=appOpenFile)
        self.Bind(wx.EVT_MENU, self.openPath, id=appOpenDir)
        self.Bind(wx.EVT_MENU, self.openVideoDir, id=appVideoDir)
        self.Bind(wx.EVT_MENU, self.onModalVersion, id=appVersion)
        self.Bind(wx.EVT_MENU, self.onModalAuthor, id=appAuthor)
        self.Bind(wx.EVT_MENU, self.openHeadVideo, id=appCat)
        self.Bind(wx.EVT_MENU, self.setting, id=appConfig)
        self.Bind(wx.EVT_MENU, self.createVideo, id=appCreate)
        # 窗口控件
        panel = wx.Panel(self)
        self.icon = wx.Icon('static/main.ico', wx.BITMAP_TYPE_ICO)
        self.videoPath = wx.StaticText(panel, label="当前路径:")
        self.text = wx.TextCtrl(panel, style=wx.TE_READONLY)
        self.startBtn = wx.Button(panel, label="合并视频")
        self.log = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.tc = wx.StaticText(panel, label="任务进程: 00")
        inner = wx.BoxSizer(wx.HORIZONTAL)
        inner.Add(self.videoPath, 0, flag=wx.ALL, border=10)
        inner.Add(self.text, 1, flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.BOTTOM, border=5)
        inner.Add(self.startBtn, 0, flag=wx.LEFT | wx.ALL, border=5)
        main = wx.BoxSizer(wx.VERTICAL)
        main.Add(inner, 0, wx.EXPAND | wx.ALL)
        main.Add(self.log, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=5)
        main.Add(self.tc, 0, wx.ALIGN_LEFT | wx.BOTTOM | wx.LEFT, border=5)
        panel.SetSizer(main)
        # 窗口监听事件
        self.Bind(wx.EVT_BUTTON, self.onStartButton, self.startBtn)
        self.Bind(wx.EVT_CLOSE, self.onCloseWindow)
        # 初始化进程数
        self.updateCount()
        self.SetIcon(self.icon)

    def initConfig(self):
        """
        初始化配置文件，目录
        如果配置文件，目录不存在，那么就创建目录，初始化配置文件
        :return:
        """
        if os.path.exists(self.tmpDir):
            pass
        else:
            os.makedirs(self.tmpDir)
        if os.path.exists(self.videoDir):
            pass
        else:
            os.makedirs(self.videoDir)
        if os.path.isfile(self.config):
            pass
        else:
            shutil.copyfile('config.ini', self.config)
            cf = ConfigParser.ConfigParser()
            cf.read(self.config)
            cf.set('dir', 'output_dir', self.videoDir)
            cf.write(open(self.config, "w"))

    def getConfigDir(self):
        """
        获取默认配置文件，临时目录，默认输出目录位置
        这个目录位置是根据注册表中的信息来的，是按用户的
        :return:
        """
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders', )
        self.configDir = winreg.QueryValueEx(key, "Personal")[0]
        self.config = self.configDir + '\\mp4merge\\config.ini'
        self.tmpDir = self.configDir + '\\mp4merge\\temp'
        self.videoDir = self.configDir + '\\video'

    def onQuit(self, evt):
        """
        关闭程序
        :param evt:
        :return:
        """
        self.Close()

    def onModalVersion(self, evt):
        """
        版本信息
        :param evt:
        :return:
        """
        aboutDialog(self, "版本", "名称:MP4视频头部尾部添加器v1.0", "依赖:FFMPEG", "").ShowModal()

    def onModalAuthor(self, evt):
        """
        作者信息
        :param evt:
        :return:
        """
        aboutDialog(self, "作者", "作者:kevinliu", "地址:上海长宁区来福士广场T2楼2103", "").ShowModal()

    def openVideoDir(self, evt):
        """
        菜单
        打开输出视频目录
        :param evt:
        :return:
        """
        cf = ConfigParser.ConfigParser()
        cf.read(self.config)
        outputDir_unicode = cf.get('dir', 'output_dir').decode("utf-8")
        outputDir = outputDir_unicode.encode("gbk")
        subprocess.call(["explorer", outputDir])

    def openHeadVideo(self, evt):
        """
        菜单
        头尾详情对话框
        :param evt:
        :return:
        """
        viewVideo(self, "视频头尾详情").ShowModal()

    def setting(self, evt):
        """
        菜单
        配置对话框
        :param evt:
        :return:
        """
        configFile(self, "配置").ShowModal()

    def createVideo(self, evt):
        """
        菜单
        配置对话框
        :param evt:
        :return:
        """
        createTsVideo(self, "生成头尾视频").ShowModal()

    def onMsgBox(self, evt):
        """
        任务完成提示
        :param evt:
        :return:
        """
        wx.MessageBox("任务已完成", "提示", wx.OK | wx.ICON_INFORMATION)

    def openFile(self, evt):
        """
        菜单
        打开单文件
        :param evt:
        :return:
        """
        dlg = wx.FileDialog(
            self,
            "打开文件",
            "",
            "",
            "MP4 files (*.mp4)|*.mp4",
            wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.filePath = dlg.GetPath()
        else:
            return
        self.text.SetValue(self.filePath)
        dlg.Destroy()

    def openPath(self, evt):
        """
        菜单
        打开目录
        :param evt:
        :return:
        """
        dlg = wx.DirDialog(self, "打开目录", style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.filePath = dlg.GetPath()
        else:
            return
        self.text.SetValue(self.filePath)
        dlg.Destroy()

    def onStartButton(self, evt):
        """
        合成视频按钮
        :param evt:
        :return:
        """
        self.buttonLock()
        self.obj = self.filePath.encode("gbk")
        self.StartFunction()

    def StartFunction(self):
        """
        开始合成调用的方法
        :return:
        """
        self.count += 1
        thread = workerThread(self.count, self, self.obj)
        self.threads.append(thread)
        self.updateCount()
        thread.start()

    def onStopButton(self, evt):
        """
        停止按钮
        :param evt:
        :return:
        """
        self.stopThreads()
        self.updateCount()

    def onCloseWindow(self, evt):
        """
        关闭窗口
        :param evt:
        :return:
        """
        self.stopThreads()
        self.updateCount()
        self.Destroy()

    def stopThreads(self):
        """
        停止进程
        :return:
        """
        while self.threads:
            thread = self.threads[0]
            thread.stop()
            self.threads.remove(thread)

    def logMessage(self, msg):
        """
        信息输出窗口的方法
        :param msg:
        :return:
        """
        self.log.AppendText(msg)

    def threadFinished(self, thread):
        """
        进程结束时调用的方法
        :param thread:
        :return:
        """
        self.threads.remove(thread)
        self.updateCount()
        self.onMsgBox(self)

    def buttonLock(self):
        """
        锁住开始合成按钮
        :return:
        """
        self.startBtn.Disable()

    def buttonUnlock(self):
        """
        解锁按钮
        :return:
        """
        self.startBtn.Enable()

    def updateCount(self):
        """
        更新任务计数，解锁开始合成按钮
        :return:
        """
        self.tc.SetLabel("任务进程: %d" % len(self.threads))
        if len(self.threads) == 0:
            self.buttonUnlock()

def main():
    app = wx.App()
    frm = myFrame()
    frm.Show()
    app.MainLoop()

if __name__ == '__main__':
    main()
