<div align="center">
<a href="http://www.tianzel.cn"><img src="http://www.tianzel.cn/wp-content/uploads/2017/11/8c025e4bb65a0e77ff02722eeb67e4e0-e1511170058957.jpg"/></a>
</div>

<h2>mp4merge</h2>

<a><img src="https://img.shields.io/badge/platform-windows-green.svg"/></a> 
<a><img src="https://img.shields.io/badge/doc-latest-green.svg"></a>

<hr/>

## 简介

- 这是一个为MP4视频文件添加头部和尾部的工具软件。往往视频网站需要上传大量的视频资源，而视频资源又需要打上自己公司的开头和结尾，使用格式工厂合成MP4视频往往需要大量的时间和重复的操作，使用本软件可以定义好视频的开头和结尾，批量添加视频

- 软件在仓促中完成，有些功能和设计还不完善，后期会慢慢改进

- 软件在windows下开发，目前只能在windows下使用，考虑到使用习惯，不准备移植到其他系统

- 软件依赖FFMPEG，在此感谢FFMPEG

## 安装

- FFMPEG 安装以及设置FFMPEG环境变量（必须）

- pip install wxpython filetype pyinstaller

- [Download](https://github.com/Kevinliu1989/mp4merge/archive/master.zip) mp4merge

- 解压后进入目录编译：cmd下执行pyinstaller -w -i static\main.ico mp4merge.py

- 先用FFMPEG生成你的头部和尾部ts视频流文件，分别命名为1.ts和3.ts放入编译好的目录，另外，别忘了把static目录和config.ini也放到编译好的目录

- 执行mp4merge.exe

## 软件界面
以下是合并单个视频，选择目录可以合并目录下所有MP4视频（不包含二级以上目录）。也可以在选项->设置里面自己定义开头的视频和结尾的视频以及输出目录。
目前头尾视频只支持ts格式，暂时没有写生成头部和尾部ts文件的功能。
<a href="http://www.tianzel.cn"><img src="http://www.tianzel.cn/wp-content/uploads/2017/12/201712051914.gif"/></a>
