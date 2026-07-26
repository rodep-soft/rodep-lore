# カーネルとデバイス管理の深淵：udevルールとシステムプログラミング

ロボティクスや組み込みシステム開発において、USBシリアル変換ケーブル、カメラ、LiDARなどの周辺機器を正しく認識し、適切な権限でアクセスすることは、ソフトウェアを安定稼働させるための第一歩です。
Linuxにおいては、カーネルが検知したハードウェアのイベントをユーザースペースで処理する `udev` がこの役割を担います。

本稿では、udevの基本概念から、複雑なルールの記述方法、よくあるトラブルシューティング、さらにはRustを用いたデバイス制御の知見について詳細に解説します。

## 1. udevのアーキテクチャと基本概念

デバイスがシステムに接続されると、カーネルはデバイスノード（例：`/dev/ttyUSB0`）を作成し、uevent（ユーザー空間イベント）を発行します。`systemd-udevd` デーモンはこれを受け取り、設定されたルール（`/etc/udev/rules.d/` 等）に基づいて、パーミッションの変更、シンボリックリンクの作成、あるいは外部スクリプトの実行を行います。

### 1.1. udevadmを用いたデバイス情報の取得

udevルールを書くためには、対象となるデバイスの属性（ベンダーID、プロダクトID、シリアル番号など）を正確に把握する必要があります。これには `udevadm info` コマンドを使用します。

```bash
$ udevadm info --attribute-walk --name=/dev/ttyUSB0

Udevadm info starts with the device specified by the devpath and then
walks up the chain of parent devices. It prints for every device
found, all possible attributes in the udev rules key format.

  looking at device '/devices/pci0000:00/0000:00:14.0/usb1/1-4/1-4:1.0/ttyUSB0/tty/ttyUSB0':
    KERNEL=="ttyUSB0"
    SUBSYSTEM=="tty"

  looking at parent device '/devices/pci0000:00/0000:00:14.0/usb1/1-4/1-4:1.0/ttyUSB0':
    SUBSYSTEMS=="usb-serial"
    DRIVERS=="ftdi_sio"

  looking at parent device '/devices/pci0000:00/0000:00:14.0/usb1/1-4':
    SUBSYSTEMS=="usb"
    DRIVERS=="usb"
    ATTRS{idVendor}=="0403"
    ATTRS{idProduct}=="6001"
    ATTRS{serial}=="A6008isP"
    ATTRS{manufacturer}=="FTDI"
```

この出力から、ルールに使用できる属性（`ATTRS`）を抽出します。

## 2. 実践的なudevルールの記述

取得した属性を元に、ルールファイルを作成します。ファイル名は通常、2桁の数字から始まり、拡張子 `.rules` を持ちます。数字が小さいほど先に評価されます。

### 2.1. 固定シンボリックリンクの作成と権限付与

ロボットに複数のマイコンボード（ESP32、STM32など）を接続する場合、起動順序によって `/dev/ttyUSB0` と `/dev/ttyUSB1` が入れ替わってしまう問題が頻発します。これを防ぐため、一意なシンボリックリンクを作成します。

```udev
# /etc/udev/rules.d/99-robot-devices.rules

# メインモータ制御用STM32
SUBSYSTEM=="tty", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="374b", SYMLINK+="robot_base", MODE="0666"

# LiDARセンサー
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", ATTRS{serial}=="0001", SYMLINK+="lidar_urg", MODE="0666"
```

設定後、ルールを再読み込みし、トリガーを実行して反映させます。

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

これにより、プログラム側では常に `/dev/robot_base` というパスでデバイスにアクセスできるようになります。

### 2.2. systemdサービスとの連携

デバイスが接続された瞬間に特定のプログラム（ROS2のノードなど）を自動起動したい場合、udevから直接長時間のプロセスを起動するのはアンチパターンです。代わりに systemd サービスをトリガーします。

```udev
# /etc/udev/rules.d/99-camera.rules
ACTION=="add", SUBSYSTEM=="video4linux", ATTRS{idVendor}=="046d", ATTRS{idProduct}=="0825", TAG+="systemd", ENV{SYSTEMD_WANTS}="camera-publisher.service"
```

## 3. 泥臭いトラブルシューティング事例

### 3.1. Permission deniedエラーの解決

**事象:** ユーザープログラムからシリアルポートを開こうとすると `Permission denied` エラーが発生する。

**調査:**
デバイスファイルの所有者とグループを確認します。

```bash
$ ls -l /dev/ttyUSB0
crw-rw---- 1 root dialout 188, 0 Jan 26 15:00 /dev/ttyUSB0
```

**原因と解決策:**
デフォルトでは、シリアルポートは `root` ユーザーと `dialout` (または `uucp`) グループに属しています。プログラムを実行するユーザーがこのグループに属していないことが原因です。
udevルールで `MODE="0666"` を設定することも可能ですが、セキュリティ上、ユーザーをグループに追加するアプローチが推奨されます。

```bash
sudo usermod -aG dialout $USER
```
※ グループ追加後は、一度ログアウトして再ログインするか、`su - $USER` を実行してセッションを更新する必要があります。

### 3.2. ルールが適用されない問題

**事象:** 正しくルールを書いたはずなのに、シンボリックリンクが作成されない。

**調査:**
`udevadm test` コマンドを使用して、ルールのパース結果と適用プロセスをデバッグします。

```bash
$ sudo udevadm test /sys/class/tty/ttyUSB0
...
Reading rules file: /etc/udev/rules.d/99-robot-devices.rules
line 2: SYMLINK+ is not a valid key, ignoring
...
```

**原因:**
文法エラー（例: `SYMLINK=` と書くべきところを誤っている、カンマが抜けているなど）や、マッチ条件が厳しすぎることが原因です。ログの指示に従って修正します。

## 4. プログラミング言語からのデバイスアクセス（Rustの事例）

モダンなシステムプログラミング言語であるRustにおいて、デバイス情報を取り扱うためのクレートとして `udever` や `libudev-sys` などが存在します。
直接 `/dev` 以下をポーリングするのではなく、これらのクレートを用いてカーネルからのueventを非同期で待ち受ける実装を行うことで、CPUリソースを消費せずに動的なデバイスの抜き差しに対応可能な堅牢なシステムを構築できます。

```rust
// libudevクレートを用いたデバイス監視の疑似コード例
fn monitor_devices() {
    let context = libudev::Context::new().unwrap();
    let mut monitor = libudev::Monitor::new(&context).unwrap();
    monitor.match_subsystem("tty").unwrap();
    let mut socket = monitor.listen().unwrap();

    loop {
        if let Some(event) = socket.receive_event() {
            println!("Device event: {:?}", event.event_type());
            // イベントに応じた処理
        }
    }
}
```

## 5. 総括

udevとカーネルのデバイス管理機構を深く理解することは、ハードウェアと直接対話するソフトウェアを開発する上で極めて重要です。ブラックボックスとして扱うのではなく、`udevadm` などのツールを駆使して内部状態を可視化し、宣言的なルールによってデバイスを統制することが、安定したシステム運用の鍵となります。
