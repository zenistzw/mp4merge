# coding: utf8
import ConfigParser
import os
import wx
import threading
import subprocess
import filetype
import winreg
import shutil


class workerThread(threading.Thread):
    def __init__(self, threadNum, window, obj):
        """
        :param threadNum: 进程数
        :param window: wxFrame
        :param obj: 得到的目录或者文件路径
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
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders', )
        self.configDir = winreg.QueryValueEx(key, "Personal")[0]
        self.config = self.configDir + '\\mp4merge\\config.ini'
        self.tmpDir_unicode = self.configDir + '\\mp4merge\\temp'
        self.tmpDir = self.tmpDir_unicode.encode("gbk")


    def stop(self):
        self.timeToQuit.set()

    def run(self):
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
        self.content = content
        self.content_unicode = self.content.decode("utf-8")
        self.content_gbk = self.content_unicode.encode("gbk")

    def runCmd(self, cmd):
        popenData = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE)
        for i in range(1, self.messageCount + 1):
            getData = unicode(popenData.stdout.readline(), 'gbk')
            self.timeToQuit.wait(self.messageDelay)
            if self.timeToQuit.isSet():
                break
            wx.CallAfter(self.window.logMessage, getData)

    def transFile(self, pathName, fileName):
        new_file = self.outputDir + '\\' + fileName
        self.cmd = 'echo ----------------------------------------start----------------------------------------'
        self.runCmd(self.cmd)
        self.transCode("开始合成")
        self.cmd = 'echo ' + self.content_gbk + fileName
        self.runCmd(self.cmd)
        self.cmd = 'ffmpeg -i ' + pathName + ' -y -vcodec copy -acodec copy -vbsf h264_mp4toannexb ' + self.tmpDir + '\\tmp.ts'
        self.runCmd(self.cmd)
        self.cmd = 'ffmpeg -i "concat:' + self.headVideo + '|' + self.tmpDir + '\\tmp.ts' + '|' + self.tailVideo + '" -y -acodec copy -vcodec copy -absf aac_adtstoasc ' + new_file
        self.runCmd(self.cmd)
        if os.path.isfile(new_file):
            self.transCode("合成成功！")
            self.cmd = 'echo ' + fileName + self.content_gbk
            self.runCmd(self.cmd)
        else:
            self.transCode("合成失败！")
            self.cmd = 'echo merge' + fileName + self.content_gbk
            self.runCmd(self.cmd)
        self.cmd = 'echo -----------------------------------------end----------------------------------------'
        self.runCmd(self.cmd)


class aboutDialog(wx.Dialog):
    def __init__(self, parent, title, txt1, txt2, txt3):
        """
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
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders', )
        self.configDir = winreg.QueryValueEx(key, "Personal")[0]
        self.config = self.configDir + '\\mp4merge\\config.ini'

    def openVideo1(self, evt):
        try:
            os.startfile(self.headVideo)
        except WindowsError:
            self.onMsgBox(self)
        else:
            pass

    def openVideo2(self, evt):
        try:
            os.startfile(self.tailVideo)
        except WindowsError:
            self.onMsgBox(self)
        else:
            pass

    def setVideoPath(self, txt, fileName):
        self.txt = txt
        fileName_gbk = fileName.decode("gbk")
        self.txt.SetValue(fileName_gbk)

    def onMsgBox(self, evt):
        wx.MessageBox("文件不存在，请重新配置！", "提示", wx.OK | wx.ICON_INFORMATION)

class configFile(wx.Dialog):
    def __init__(self, parent, title):
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
        text1 = wx.StaticBox(panel, -1, label="配置选项")
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
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders', )
        self.configDir = winreg.QueryValueEx(key, "Personal")[0]
        self.config = self.configDir + '\\mp4merge\\config.ini'
        self.videoDir = self.configDir + '\\video'

    def configNew(self, evt):
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
        self.configNew(evt)
        self.Close()

    def defaultConfig(self, evt):
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
        self.txt = txt
        path_gbk = path.decode("gbk")
        self.txt.SetValue(path_gbk)

    def openPath(self, evt):
        dlg = wx.DirDialog(self, "选择目录", style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.dirPath = dlg.GetPath()
        else:
            return
        self.dirText.SetValue(self.dirPath)
        dlg.Destroy()
        self.configBtn.Enable()

    def openFile1(self, evt):
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
        wx.Frame.__init__(self, None, title="MP4头部尾部添加器v1.0", size=(800, 500))
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
        configVideo = wx.MenuItem(optionMenu, appConfig, "&配置\tCtrl+Alt+S")
        configVideo.SetBitmap(wx.Bitmap("static/config.ico"))
        optionMenu.Append(catVideo)
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
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders', )
        self.configDir = winreg.QueryValueEx(key, "Personal")[0]
        self.config = self.configDir + '\\mp4merge\\config.ini'
        self.tmpDir = self.configDir + '\\mp4merge\\temp'
        self.videoDir = self.configDir + '\\video'

    def onQuit(self, evt):
        self.Close()

    def onModalVersion(self, evt):
        aboutDialog(self, "版本", "名称:MP4视频头部尾部添加器v1.0", "依赖:FFMPEG", "").ShowModal()

    def onModalAuthor(self, evt):
        aboutDialog(self, "作者", "Author:kevinliu", "地址:上海长宁区来福士广场T2楼2103", "").ShowModal()

    def openVideoDir(self, evt):
        # os.system("explorer videos")
        cf = ConfigParser.ConfigParser()
        cf.read(self.config)
        outputDir_unicode = cf.get('dir', 'output_dir').decode("utf-8")
        outputDir = outputDir_unicode.encode("gbk")
        subprocess.call(["explorer", outputDir])

    def openHeadVideo(self, evt):
        viewVideo(self, "视频头尾详情").ShowModal()

    def setting(self, evt):
        configFile(self, "配置").ShowModal()

    def onMsgBox(self, evt):
        wx.MessageBox("任务已完成", "提示", wx.OK | wx.ICON_INFORMATION)

    def openFile(self, evt):
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
        dlg = wx.DirDialog(self, "打开目录", style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.filePath = dlg.GetPath()
        else:
            return
        self.text.SetValue(self.filePath)
        dlg.Destroy()

    def onStartButton(self, evt):
        self.buttonLock()
        self.obj = self.filePath.encode("gbk")
        self.StartFunction()

    def StartFunction(self):
        self.count += 1
        thread = workerThread(self.count, self, self.obj)
        self.threads.append(thread)
        self.updateCount()
        thread.start()

    def onStopButton(self, evt):
        self.stopThreads()
        self.updateCount()

    def onCloseWindow(self, evt):
        self.stopThreads()
        self.updateCount()
        self.Destroy()

    def stopThreads(self):
        while self.threads:
            thread = self.threads[0]
            thread.stop()
            self.threads.remove(thread)

    def logMessage(self, msg):
        self.log.AppendText(msg)

    def threadFinished(self, thread):
        self.threads.remove(thread)
        self.updateCount()
        self.onMsgBox(self)

    def buttonLock(self):
        self.startBtn.Disable()

    def buttonUnlock(self):
        self.startBtn.Enable()

    def updateCount(self):
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
