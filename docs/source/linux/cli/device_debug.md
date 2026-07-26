# Device Debug

デバイス周りのトラブルシューティング用メモ.
一番死にやすいので、テキトーに飛ばさず上から順番に切り分ける。

## はじめに

デバイス周りは、物理・カーネル・権限・プロセス競合が絡むので沼りやすい.
困ったら「どの層で止まっているか」を順に潰す。

## 前提

Linux のデバイス周りを少し知っていることを前提にする。
カーネル、`/dev`、`udev`、基本的なコマンドを軽く触ったことがあると読みやすい。

## Everything is a file

Linux では、ハードウェアやソケット、プロセスまでファイルとして扱う.
つまり `open()` / `read()` / `write()` / `close()` の感覚で触れるのが基本になる。

例:

```bash
# シリアルポートから値を読む
cat /dev/ttyUSB0

# 出力を捨てる
echo hello > /dev/null

# LED を点灯する例
echo 1 > /sys/class/leds/input0::capslock/brightness
```

## File types

`ls -l` の先頭 1 文字でファイルの種類が分かる。

| 記号 | 種類 | 説明 |
| --- | --- | --- |
| `-` | 通常ファイル | テキストやバイナリなどの普通のファイル |
| `d` | ディレクトリ | ファイルをまとめる入れ物 |
| `c` | キャラクタデバイス | 1文字単位でやり取りするデバイス |
| `b` | ブロックデバイス | ブロック単位で扱うデバイス |
| `l` | シンボリックリンク | 他のファイルへの参照 |
| `p` | FIFO | プロセス間通信の通路 |
| `s` | ソケット | 通信に使う特殊ファイル |

## FS (Filesystem)

ストレージ上のブロックに、名前・権限・階層構造を与えるのがファイルシステム.
Linux はデータの配置を直接は知らないので、FS が秩序を与える.

よく見る例:

| FS | 主な用途 | 特徴 |
| --- | --- | --- |
| ext4 | Linux 標準 | 安定、汎用 |
| xfs | サーバ向け | 高速、大容量向き |
| btrfs | 先進型 | スナップショット、自己修復 |
| vfat / exfat | 互換用 | Windows とやり取りしやすい |
| ntfs | Windows 標準 | Linux でも扱える |

## Mount

ファイルシステムを別の場所に組み込んで見せるのがマウント.

```bash
mount
sudo mount /dev/sdb1 /mnt
sudo umount /mnt
sudo mount -t ext4 /dev/sdb2 /mnt
```

毎回手でやるのが面倒なら `/etc/fstab` に書く.

## FHS

Filesystem Hierarchy Standard は、Linux ディストリビューション間で配置を揃えるための基準.
`/etc` は設定、`/bin` は基本コマンド、`/dev` はデバイスファイル、といった整理のためにある.

## /dev (Device)

`/dev` 以下はデバイスファイルの置き場.
実際のハードウェア操作の入口になる。

### デバイス種別

| 種類 | 例 | 内容 |
| --- | --- | --- |
| ブロックデバイス | `/dev/sda`, `/dev/mmcblk0` | ディスクや SD カード |
| キャラクタデバイス | `/dev/ttyUSB0`, `/dev/ttyACM0`, `/dev/random` | バイト単位で読み書き |
| 仮想デバイス | `/dev/null`, `/dev/zero`, `/dev/urandom` | ハードではないが便利 |

`/dev` のファイルは `udev` が自動生成する.

## Udev

`udev` はデバイスが抜き差しされたときに `/dev` 配下を整理するデーモン.
シンボリックリンクや権限もここで整えられる.

```bash
systemctl status systemd-udevd
sudo udevadm info -a -n /dev/xxx
sudo udevadm monitor
sudo udevadm control --reload
sudo udevadm trigger
```

ルールは通常 `/etc/udev/rules.d/` に置く.

## Major / Minor

`/dev/sda` みたいな名前より、本質的には major / minor 番号で扱われる.

- major: どのドライバが担当するか
- minor: その中の個別デバイス番号

`ls -l /dev/xxx` で確認できる.

## Device Driver

デバイスドライバはハードウェアとカーネルの通訳.
今カーネルに入っているものは `lsmod` で見られる.

```bash
lsmod | grep usb
cat /proc/modules | grep usb
sudo modprobe uvcvideo
modinfo bluetooth
```

## Device Check Commands

### `lsusb`

USB バスに接続された機器一覧を出す.
USB に乗っていれば、ドライバが当たっていなくても見える.

### `ls /dev/ttyUSB*` とは何が違う？

`lsusb` は「刺さっているデバイス自体」を見る.
`/dev/ttyUSB*` は、カーネルがドライバを当ててデバイスとして認識した後に出る.

つまり:

- `lsusb` に出ない: 物理・電源・デバイス本体を疑う
- `lsusb` に出るが `/dev` が無い: ドライバや `udev` を疑う

### `lsblk`

ディスクやパーティションを見る.
ファイルシステムも一緒に見たいなら `lsblk -f` が便利.

### `lspci`

PCI / PCIe の機器を見る.
GPU や内蔵コントローラの確認によく使う.

### `dmesg`

カーネルログを見る.
デバイスの抜き差しやドライバロードの様子を追える.

```bash
sudo dmesg | tail -15
dmesg -w
```

### `lsof`

誰がそのデバイスを開いているか確認する.
シリアルポートが使えないときは、まずこれを打つ.

```bash
lsof /dev/ttyUSB0
fuser /dev/ttyUSB0
```

## デバッグ順

基本はこの順番で確認する.

1. 物理 - ケーブル、電源、抜け、接触不良
2. 列挙 - `lsusb`
3. カーネルログ - `dmesg` / `journalctl -kb`
4. デバイスノード - `/dev`
5. ドライバ - `lsusb -t`
6. 権限 / `udev`
7. プロセス競合 - `lsof` / `fuser`

## まず見るもの

### 列挙

```bash
lsusb
```

USB バスに乗っているデバイスはここに出る。
ここに出ないなら、まずは物理・電源・デバイス本体を疑う。

`lsusb` に出るのに `/dev/ttyUSB*` や `/dev/video*` が出ないなら、ドライバや `udev` 側を疑う。

### カーネルログ

```bash
dmesg -w
```

抜き差ししながらログを見ると、どこで失敗しているかを追いやすい。
過去ログを見たいときは `dmesg` 単体、より広く見るなら以下も使う。

```bash
journalctl -kb
```

### デバイスノード

```bash
ls /dev/ttyUSB*
ls /dev/video*
```

`lsusb` で見えているのにデバイスノードが無いなら、ドライバ未バインドか `udev` の問題を疑う。
ここをハードコードして制御するのは避け、基本は `udev` の symlink か安定した識別子を使う。

### ドライババインド

```bash
lsusb -t
```

どのカーネルドライバに紐付いているかを確認する。
`lsusb` では見えるのに使えない、というときの次の一手。

## udev を見る

```bash
udevadm info -a -n /dev/xxx
udevadm monitor
```

`VID` / `PID` / `iSerial` / `KERNEL` などを確認する。
ルールを書いたら、実際に `/etc/udev/rules.d/` に入っているかも確認する。

```bash
less /etc/udev/rules.d/xxx.rules
```

時間がないなら、まずは動くことを優先して一時的にパス直指定で切り抜けるのもあり。

## 競合と権限

### つかまれていないか

```bash
lsof /dev/xxx
fuser /dev/xxx
```

他のプロセスが掴んでいると、正しく見えていても開けないことがある。
`fuser -k /dev/xxx` は強力なので、止めてよい相手か確認してから使う。

### 権限

```bash
ll /dev/xxx
chmod 777 /dev/xxx
```

`udev` で権限を切るのが本筋だが、切り分けの最後に一時的に試すのはあり。
恒久対応は `udev` ルールに寄せる。

## 物理に戻る

コマンドを打っても原因が絞れないときは、もう一度これをやる。

1. 抜き差しする
2. ポートを変える
3. ケーブルを変える
4. 電源を見直す

KERNEL 名で `udev` を縛っている構成では、ポート変更で名前が変わることがあるので注意。

## カメラ

カメラ系は `v4l2-ctl` で先に確認すると速い。

```bash
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video* --list-formats-ext
v4l2-ctl -d /dev/video* --stream-mmap --stream-count=100
```

見るポイントは以下。

- どのデバイスがどのカメラか
- 対応フォーマットが本当にあるか
- 解像度が設定値に存在するか
- FPS が想定通りか
- 単体ストリームが通るか

MJPG が使えると思い込まず、実際に対応フォーマットを見てから設定する。

## ざっくり判断基準

- `lsusb` に出ない: 物理・電源・デバイス本体
- `lsusb` に出るが `/dev` が無い: ドライバ・`udev`
- `/dev` はあるが開けない: 権限・競合
- カメラ単体テストで落ちる: デバイス側か設定値
