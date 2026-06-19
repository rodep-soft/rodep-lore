# カメラの扱い

## Linuxからみたカメラとは？

Linuxは`Everything is a file`の原理に基づき、カメラもデバイスファイルとして扱う. 
ユーザからは`/dev/video0`などの名前で映像データを流してくる特殊なファイルとして見える.

```bash
# 
$ ls /dev/video*

# 勿論catできる(r権限必要)
$ cat /dev/video0
```
## Camera Stack

一般的には、

Camera -> USB/CSI -> Kernel Driver -> V4L2 -> /dev/video* -> User Program

## Kernel Driver

ハードウェア初期化、データ転送、割り込み、OS(Linux)との接続などの仕事をする. 
LinuxではKernel moduleとしてロードされる. 速度の問題などでKernel Spaceで動く.

実体は`*.ko(Kernel Object)`ファイル.

```bash
# module一覧
$ lsmod

# load
$ sudo modprobe <module>

# unload
$ sudo modprobe -r <module>

# insmod, rmmodもあるが, modprobeとは違い依存関係を考慮しない.
```

### USBの場合

基本的に標準規格であるUVC(Universal Video Class)順処のため、ドライバはほぼ`uvcvideo`一択.

USBcamは扱いが簡単でDocker越しでも比較的用意に扱えるが、遅延や帯域に注意!

```bash
# Kernel module確認
# uvcvideo etc.
$ lsmod | grep uvc

# デバイス認識
$ dmesg | tail
```

### CSIの場合

UVCのような規格がないため、センサごとにドライバが必要. RaspberrypiCameraなど.

一般的に低遅延、高FPS、高画質.


## V4L2とは

Video4Linux2. LinuxのKernel Spaceにある映像入出力API. ドライバではない.

CMD

```bash
# デバイス一覧
$ v4l2-ctl --list-devices

# 解像度確認
$ v4l2-ctl --list-formats-ext
```

## 重要なシステムコール

User SpaceのアプリケーションがKernelに仕事を依頼するための入口.

### open()

カメラを開く際に使われる. 内部的には、vfs->videodev->uvcvideoに到達する.

```c
# 返り値はfile descriptor
int fd = open("/dev/video0", O_RDWR);
```
### close()

カメラを閉じる.

```c
close(fd);
```

### ioctl()

read(), write()だけでは表現できない特殊命令用.

前述したv4l2はカメラ専用のioctlプロトコル仕様のようなもの. 
ioctl番号の定義(VIDIOC_QUERYCAPなど)はlinux/videodev2.hに定義されている.

```c
# VIDIOC_QUERYCAP自体はただの数字
ioctl(fd, VIDIOC_QUERYCAP, &cap);
```

### mmap()

Kernel BufferからUser Bufferにcopyすると遅いので共有して渡す.

```c
void* buf = mmap(...);
```

### poll(), epoll()

etc. 追記する.




## OpenCV

User Spaceの画像処理フレームワーク. よくPythonやC++から使う. 
クロスプラットフォームなのでLinux, macOS, WindowsなどOSを気にせず書ける.

```c++
# 入力
# 
cv::VideoCapture cap(0);
```



### 後で書くこと

- ros2での扱い
- ffmpeg
- gstreamer
- dma buffer

OpenCV
↓
open("/dev/video0")
↓
ioctl()
↓
read() or mmap()
