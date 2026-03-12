import sys
from PyQt5.QtWidgets import (QApplication)
from PyQt5.QtWidgets import (QWidget, QDesktopWidget,
                             QMessageBox, QHBoxLayout, QVBoxLayout, QSlider, QListWidget,
                             QPushButton, QLabel, QComboBox, QFileDialog)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
import os, time
import configparser
import random
from PyQt5.QtCore import QCoreApplication

class MP3Player(QWidget):
    def __init__(self):
        super().__init__()

        self.startTimeLabel = QLabel('00:00')
        self.endTimeLabel = QLabel('00:00')
        self.slider = QSlider(Qt.Horizontal, self)
        self.PlayModeBtn = QPushButton(self)
        self.playBtn = QPushButton(self)
        self.prevBtn = QPushButton(self)
        self.nextBtn = QPushButton(self)
        self.musicBtn = QPushButton(self)
        self.openBtn = QPushButton(self)
        self.musicList = QListWidget()
        self.song_formats = ['mp3', 'm4a', 'flac', 'wav', 'ogg']
        self.songs_list = []
        self.cur_playing_song = ''
        self.is_pause = True
        self.player = QMediaPlayer()
        self.is_switching = False
        self.playMode = 0
        self.settingfilename = 'config2.ini'
        self.textLable = QLabel('前进的路上，也要记得欣赏沿途的风景呀!')
        self.infoLabel = QLabel('So Bring,傻逼二次元')

        # --- 修改了这里的图片相对路径 ---
        self.playBtn.setStyleSheet("QPushButton{border-image: url(data/music/music_pic/play.png)}")
        self.playBtn.setFixedSize(48, 48)
        self.nextBtn.setStyleSheet("QPushButton{border-image: url(data/music/music_pic/next.png)}")
        self.nextBtn.setFixedSize(48, 48)
        self.prevBtn.setStyleSheet("QPushButton{border-image: url(data/music/music_pic/prev.png)}")
        self.prevBtn.setFixedSize(48, 48)

        self.musicBtn.setStyleSheet("QPushButton{border-image: url(data/music/music_pic/music2.png)}")
        self.musicBtn.setFixedSize(44, 44)

        self.openBtn.setStyleSheet("QPushButton{border-image: url(data/music/music_pic/open.png)}")
        self.openBtn.setFixedSize(24, 24)
        self.PlayModeBtn.setStyleSheet("QPushButton{border-image: url(data/music/music_pic/sequential.png)}")
        self.PlayModeBtn.setFixedSize(24, 24)
        # --------------------------------

        self.timer = QTimer(self)
        self.timer.start(1000)
        self.timer.timeout.connect(self.playByMode)

        self.hBoxSlider = QHBoxLayout()
        self.hBoxSlider.addWidget(self.startTimeLabel)
        self.hBoxSlider.addWidget(self.slider)
        self.hBoxSlider.addWidget(self.endTimeLabel)

        self.hBoxButton = QHBoxLayout()
        self.hBoxButton.addWidget(self.PlayModeBtn)
        self.hBoxButton.addStretch(1)
        self.hBoxButton.addWidget(self.prevBtn)
        self.hBoxButton.addWidget(self.playBtn)
        self.hBoxButton.addWidget(self.nextBtn)
        self.hBoxButton.addWidget(self.musicBtn)
        self.hBoxButton.addStretch(1)
        self.hBoxButton.addWidget(self.openBtn)

        self.vBoxControl = QVBoxLayout()
        self.vBoxControl.addLayout(self.hBoxSlider)
        self.vBoxControl.addLayout(self.hBoxButton)

        self.hBoxAbout = QHBoxLayout()
        self.hBoxAbout.addWidget(self.textLable)
        self.hBoxAbout.addStretch(1)
        self.hBoxAbout.addWidget(self.infoLabel)

        self.vboxMain = QVBoxLayout()
        self.vboxMain.addWidget(self.musicList)
        self.vboxMain.addLayout(self.vBoxControl)
        self.vboxMain.addLayout(self.hBoxAbout)

        self.setLayout(self.vboxMain)

        self.openBtn.clicked.connect(self.openMusicFloder)
        self.playBtn.clicked.connect(self.playMusic)
        self.prevBtn.clicked.connect(self.prevMusic)
        self.nextBtn.clicked.connect(self.nextMusic)
        self.musicList.itemDoubleClicked.connect(self.doubleClicked)
        self.slider.sliderMoved[int].connect(lambda: self.player.setPosition(self.slider.value()))
        self.PlayModeBtn.clicked.connect(self.playModeSet)

        self.loadingSetting()

        # 创建音量调节滑块并设置初始属性，以及相关事件连接
        self.volumeSlider = QSlider(Qt.Vertical, self)
        self.volumeSlider.setRange(0, 100)
        self.volumeSlider.setValue(50)
        self.volumeSlider.setFixedSize(20, 100)
        self.volumeSlider.hide()
        self.volumeSlider.valueChanged[int].connect(self.changeVolume)

        # 设置音量调节滑块的位置，初始位置根据音乐按钮位置设置
        music_btn_pos = self.musicBtn.pos()
        self.volumeSlider.move(music_btn_pos.x() + self.musicBtn.width() // 2 - self.volumeSlider.width() // 2,
                               music_btn_pos.y() - self.volumeSlider.height() - 10)

        # 音乐按钮点击事件，用于显示/隐藏音量调节滑块
        self.musicBtn.clicked.connect(self.toggleVolumeSlider)

        self.initUI()

    # 事件过滤器处理音乐按钮位置变化事件
    def moveEvent(self, event):
        music_btn_pos = self.musicBtn.pos()
        self.volumeSlider.move(music_btn_pos.x() + self.musicBtn.width() // 2 - self.volumeSlider.width() // 2,
                               music_btn_pos.y() - self.volumeSlider.height() - 10)
        return super().moveEvent(event)

    # 重写 resizeEvent 方法，处理窗口大小变化事件
    def resizeEvent(self, event):
        super().resizeEvent(event)
        music_btn_pos = self.musicBtn.pos()
        self.volumeSlider.move(music_btn_pos.x() + self.musicBtn.width() // 2 - self.volumeSlider.width() // 2,
                               music_btn_pos.y() - self.volumeSlider.height() - 10)

    # changeVolume 方法用于调整音量
    def changeVolume(self, value):
        self.player.setVolume(value)

    def toggleVolumeSlider(self):
        if self.volumeSlider.isVisible():
            self.volumeSlider.hide()
        else:
            self.volumeSlider.show()

    # 初始化界面
    def initUI(self):
        self.resize(600, 400)
        self.center()
        self.setWindowTitle('音乐播放器')
        # --- favicon.ico 在根目录，所以直接写文件名即可 ---
        self.setWindowIcon(QIcon('favicon.ico'))
        self.show()

    # 窗口显示居中
    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    # 打开文件夹
    def openMusicFloder(self):
        self.cur_path = QFileDialog.getExistingDirectory(self, "选取音乐文件夹", './')
        if self.cur_path:
            self.cur_path = self.cur_path.replace(' ', '%20')  # 处理空格
            self.showMusicList()
            self.cur_playing_song = ''
            self.startTimeLabel.setText('00:00')
            self.endTimeLabel.setText('00:00')
            self.slider.setSliderPosition(0)
            self.updateSetting()
            self.is_pause = True
            # --- 替换相对路径 ---
            self.playBtn.setStyleSheet("QPushButton{border-image: url(data/music/music_pic/play.png)}")

    # 显示音乐列表
    def showMusicList(self):
        self.musicList.clear()
        for song in os.listdir(self.cur_path):
            if song.split('.')[-1] in self.song_formats:
                song_path = os.path.abspath(os.path.join(self.cur_path, song))
                self.songs_list.append([song, song_path.replace('\\', '/')])
                self.musicList.addItem(song)
        if self.musicList.count() > 0:
            self.musicList.setCurrentRow(0)
            self.cur_playing_song = self.songs_list[self.musicList.currentRow()][-1]

    # 提示
    def Tips(self, message):
        QMessageBox.about(self, "提示", message)

    # 设置当前播放的音乐
    def setCurPlaying(self):
        row = self.musicList.currentRow()
        if row < 0 or row >= len(self.songs_list):
            return
        self.cur_playing_song = self.songs_list[row][-1]
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(self.cur_playing_song)))

    # 播放/暂停播放
    def playMusic(self):
        if self.musicList.count() == 0:
            self.Tips('当前路径内无可播放的音乐文件')
            return
        if not self.player.isAudioAvailable():
            self.setCurPlaying()
        if self.is_pause or self.is_switching:
            self.player.play()
            self.is_pause = False
            # --- 替换相对路径 ---
            self.playBtn.setStyleSheet("QPushButton{border-image: url(data/music/music_pic/pause.png)}")
        elif (not self.is_pause) and (not self.is_switching):
            self.player.pause()
            self.is_pause = True
            # --- 替换相对路径 ---
            self.playBtn.setStyleSheet("QPushButton{border-image: url(data/music/music_pic/play.png)}")

    # 上一曲
    def prevMusic(self):
        self.slider.setValue(0)
        if self.musicList.count() == 0:
            self.Tips('当前路径内无可播放的音乐文件')
            return
        pre_row = self.musicList.currentRow() - 1 if self.musicList.currentRow() != 0 else self.musicList.count() - 1
        self.musicList.setCurrentRow(pre_row)
        self.is_switching = True
        self.setCurPlaying()
        self.playMusic()
        self.is_switching = False

    # 下一曲
    def nextMusic(self):
        self.slider.setValue(0)
        if self.musicList.count() == 0:
            self.Tips('当前路径内无可播放的音乐文件')
            return
        next_row = self.musicList.currentRow() + 1 if self.musicList.currentRow() != self.musicList.count() - 1 else 0
        self.musicList.setCurrentRow(next_row)
        self.is_switching = True
        self.setCurPlaying()
        self.playMusic()
        self.is_switching = False

    # 双击歌曲名称播放音乐
    def doubleClicked(self):
        self.slider.setValue(0)
        self.is_switching = True
        self.setCurPlaying()
        self.playMusic()
        self.is_switching = False

    # 根据播放模式自动播放，并刷新进度条
    def playByMode(self):
        if (not self.is_pause) and (not self.is_switching):
            self.slider.setMinimum(0)
            self.slider.setMaximum(self.player.duration())
            self.slider.setValue(self.slider.value() + 1000)
        self.startTimeLabel.setText(time.strftime('%M:%S', time.localtime(self.player.position() / 1000)))
        self.endTimeLabel.setText(time.strftime('%M:%S', time.localtime(self.player.duration() / 1000)))

        # 顺序播放
        if (self.playMode == 0) and (not self.is_pause) and (not self.is_switching):
            if self.musicList.count() == 0:
                return
            if self.player.position() == self.player.duration() and self.player.duration() > 0:
                self.nextMusic()
        # 单曲循环
        elif (self.playMode == 1) and (not self.is_pause) and (not self.is_switching):
            if self.musicList.count() == 0:
                return
            if self.player.position() == self.player.duration() and self.player.duration() > 0:
                self.is_switching = True
                self.setCurPlaying()
                self.slider.setValue(0)
                self.playMusic()
                self.is_switching = False
        # 随机播放
        elif (self.playMode == 2) and (not self.is_pause) and (not self.is_switching):
            if self.musicList.count() == 0:
                return
            if self.player.position() == self.player.duration() and self.player.duration() > 0:
                self.is_switching = True
                self.musicList.setCurrentRow(random.randint(0, self.musicList.count() - 1))
                self.setCurPlaying()
                self.slider.setValue(0)
                self.playMusic()
                self.is_switching = False

    # 更新配置文件
    def updateSetting(self):
        config = configparser.ConfigParser()
        config.read(self.settingfilename)
        if not os.path.isfile(self.settingfilename):
            config.add_section('MP3Player')
        config.set('MP3Player', 'PATH', self.cur_path)
        with open(self.settingfilename, 'w') as f:
            config.write(f)

    # 加载配置文件
    def loadingSetting(self):
        config = configparser.ConfigParser()
        config.read(self.settingfilename)
        if not os.path.isfile(self.settingfilename):
            return
        try:
            self.cur_path = config.get('MP3Player', 'PATH')
            if os.path.exists(self.cur_path):
                self.showMusicList()
        except configparser.NoOptionError:
            pass
        except configparser.NoSectionError:
            pass

    # 播放模式设置
    def playModeSet(self):
        # 设置为单曲循环模式
        if self.playMode == 0:
            self.playMode = 1
            # --- 替换相对路径 ---
            self.PlayModeBtn.setStyleSheet("QPushButton{border-image: url(data/music/music_pic/circulation.png)}")
        # 设置为随机播放模式
        elif self.playMode == 1:
            self.playMode = 2
            # --- 替换相对路径 ---
            self.PlayModeBtn.setStyleSheet("QPushButton{border-image: url(data/music/music_pic/random.png)}")
        # 设置为顺序播放模式
        elif self.playMode == 2:
            self.playMode = 0
            # --- 替换相对路径 ---
            self.PlayModeBtn.setStyleSheet("QPushButton{border-image: url(data/music/music_pic/sequential.png)}")

    # 确认用户是否要真正退出
    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Message',
                                     "确定要退出吗？", QMessageBox.Yes |
                                     QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.player.stop()  # 停止音乐播放
            event.ignore()  # 忽略默认的关闭事件
            self.hide()  # 隐藏当前窗口，而不是彻底结束进程
        else:
            event.ignore()

    # 在 MP3Player 类中添加一个方法来实现随机播放音乐
    def playRandomMusic(self):
        if self.songs_list:
            random.shuffle(self.songs_list)
            self.cur_playing_song = self.songs_list[0][1]
            self.setCurPlaying()
            self.playMusic()


def run():
    app = QApplication(sys.argv)
    ex = MP3Player()

    if len(ex.songs_list) > 0:
        row_to_play = 2 if len(ex.songs_list) > 2 else 0
        ex.musicList.setCurrentRow(row_to_play)
        ex.setCurPlaying()
        ex.playMusic()
    else:
        print("提示：列表内没有音乐。请在界面上点击文件夹图标导入音乐路径。")

    sys.exit(app.exec_())


if __name__ == '__main__':
    run()