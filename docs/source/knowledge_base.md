# ロボティクスチーム 技術ナレッジまとめ

本ドキュメントは、チームの過去のチャット履歴から抽出した有用な技術リソース、コードスニペット、および設計・実装上の知見を体系的にまとめたものです。

## 1. ROS 2 & ロボティクス

### 公式リソース & Tips
- **[Understanding ROS 2 Parameters](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Parameters/Understanding-ROS2-Parameters.html)**: パラメータ管理の基礎。PIDゲイン等、動的に変更したい変数は `declare_parameter` などを活用することで再起動なしで調整可能。
- **[Getting Backtraces in ROS 2](https://docs.ros.org/en/jazzy/How-To-Guides/Getting-Backtraces-in-ROS-2.html)**: C++ノードがクラッシュした際のバックトレース取得方法。
- **[REP-0144 (ROS C++ Style Guide)](https://reps.openrobotics.org/rep-0144/)**: ROS公式のC++コーディング規約。
- **Intra-process通信について**: ゼロコピー通信（Intra-process）は単一プロセス内で `std::unique_ptr` を受け渡すことで実現される。これを有効活用するためには Component 化が必須。

### RMW (ROS Middleware) & ネットワーク通信
- **[Working with Zenoh](https://docs.ros.org/en/jazzy/Installation/RMW-Implementations/Non-DDS-Implementations/Working-with-Zenoh.html)** / **[rmw_zenoh](https://github.com/ros2/rmw_zenoh)**: 安定したマルチキャストやWi-Fi環境下で有利な非DDS（Zenoh）実装。
- **[The Foxglove Bridge and Tailscale VPN](https://foxglove.dev/blog/the-foxglove-bridge-and-tailscale-vpn)**: Tailscaleを介して外部ネットワークからROS 2のデータを安全に可視化（Foxglove）する手法。

### マイコン・エッジ向けROS (micro-ROS / mROS)
- **[micro-ROS Hardware Support](https://micro.ros.org/docs/overview/hardware/)**: 各種マイコン向けのmicro-ROS対応リスト。
- **[mROS 2](https://github.com/mROS-base/mros2) / [mros2-esp32](https://github.com/mROS-base/mros2-esp32)**: 組み込みデバイス向け軽量ROSノード実装。

### SLAM / ナビゲーション / ビジョン
- **[Nav2 SLAM tutorial](https://docs.nav2.org/tutorials/docs/navigation2_with_slam.html)** / **[slam_toolbox](https://github.com/SteveMacenski/slam_toolbox/tree/jazzy)**: 2D SLAMとナビゲーションの構築。高頻度のLiDARスキャン（40Hzなど）をそのまま流すとキューが詰まるため、`urg_node2`のskip設定や、中間のノードで間引き処理を行うことが推奨される。
- **[ffmpeg_image_transport](https://github.com/ros-misc-utilities/ffmpeg_image_transport)**: FFMPEGを用いた高効率な画像/映像転送。
- **[AprilTag ROS](https://github.com/christianrauch/apriltag_ros)** / **[Gazebo AprilTag](https://github.com/koide3/gazebo_apriltag)**: ビジョンベースの位置推定用マーカ。

### デバイスドライバ & 連携
- **[ros2_socketcan](https://github.com/autowarefoundation/ros2_socketcan)**: SocketCANを利用してROS 2とCANバスをブリッジするドライバ。
- **[ros2-rust](https://github.com/ros2-rust/ros2_rust/tree/main)**: RustからROS 2を使用するためのクライアントライブラリ。

---

## 2. マイコン・電子工作・組み込み

### 開発ボード & IMU
- **[STM32 Nucleo-64 Boards User Manual](https://www.st.com/resource/en/user_manual/um1724-stm32-nucleo64-boards-mb1136-stmicroelectronics.pdf)**
- **[PlatformIO ST STM32](https://docs.platformio.org/en/latest/platforms/ststm32.html)**
- **[BNO055 データシート](https://akizukidenshi.com/goodsaffix/AE-BNO055-BO_20220413.pdf)** / **[libbno055 (Rust実装)](https://crates.io/crates/libbno055)**: 9軸センサ。

### モータードライバ
- **[L298N](https://aisumegane.com/l298n/)**: 一般的なDCモータードライバ。
- **[RoboClaw User Manual](https://downloads.basicmicro.com/docs/roboclaw_user_manual.pdf)**: より高度な制御が可能な高性能モーターコントローラ。

### CAN通信 (MCP2515モジュール)
SPI接続のCANコントローラ「MCP2515」を使用する際、モジュール上のクリスタル発振器の周波数（8MHz か 16MHz）をライブラリの設定と一致させる必要がある（初期化失敗の原因になりやすい）。
```cpp
// mcp_canライブラリの初期化例
if (CAN0.begin(MCP_ANY, CAN_500KBPS, MCP_8MHZ) == CAN_OK) {
  Serial.println("CAN INIT OK");
}
```

### 便利スクリプト (STM32 フラッシュ用Makefile例)
```makefile
BAUD_RATE = 115200
USB_PORT = /dev/ttyACM0

flash:
    st-flash write build/mystm32project.bin 0x08000000

read:
    stty -F $(USB_PORT) $(BAUD_RATE)
    cat $(USB_PORT)
```

---

## 3. Linux・OS・インフラ

### Docker / コンテナ管理
- **[Docker Compose Watch](https://docs.docker.com/reference/cli/docker/compose/watch/)**: ホスト側のファイル変更を検知してコンテナに即座に同期・リロードさせる開発環境構築機能。
- 組み込みLinux (Yocto等) をホストOSとし、その上でDockerデーモンを走らせて制御以外のアプリを隔離するアーキテクチャは、環境の再現性や切り戻しが容易で強力。

### Linuxネットワーク & システム管理
- **名前解決トラブルシューティング**: Ubuntuなどでは `systemd-resolved` により `/etc/resolv.conf` がスタブリゾルバ（`127.0.0.53`等）を指している。実際のDNSを確認するには `resolvctl status` を使用する。
- **通信の安定化策案**: MPTCP (Multipath TCP) を有効化し、仮想インターフェースを介してShadowsocksなどのプロキシに向けることで、複数のネットワークインターフェースを束ねた安定化が図れる。
- **ディスク容量のメンテナンス**: `docker images`, `aur build` のキャッシュ、`journalctl` ログ、不要なカーネル、`node_modules` などが容量を圧迫しやすいため、定期的なメンテナンス（庭師作業）が必要。
- **ログの確認**: GUIやサービスのトラブル時は、闇雲に再起動する前に `journalctl -u <サービス名>.service` でエラーログを確認する癖をつける。

---

## 4. プログラミング言語・開発ツール

### Rust
- **[Embassy](https://github.com/embassy-rs/embassy)**: STM32等向けの次世代・非同期組み込みフレームワーク。
- **[Clap](https://docs.rs/clap/latest/clap/)**: CLIアプリケーション構築のデファクトスタンダード。
- **[Axum](https://docs.rs/axum/latest/axum/)**: 高性能な非同期Webフレームワーク。
- **[serialport-rs](https://docs.rs/serialport/)** / **[socketcan-rs](https://docs.rs/socketcan/)**: 各種デバイス通信用ライブラリ。

### Python
- **[uv (astral)](https://docs.astral.sh/uv/)**: Cargoライクで非常に高速な次世代Pythonパッケージマネージャ。
- **[Python Control Systems Library](https://python-control.readthedocs.io/en/0.10.2/)**: 伝達関数のモデリングやステップ応答、ボード線図の描画など。

### アーキテクチャ & マインドセット
- **自己文書化コード (Self-documenting code)**: 「コメントを大量に書くよりも、変数名・関数名やクラス設計によってコード自体が仕様を語るようにする」ことが重要。
- 知識の伝達は「体系立てたレクチャー」だけでなく、開発の場（コミュニティ・オブ・プラクティス）に身を置き、コードリーディングやトラブルシューティング（エラーログを読む等）を通じて暗黙知（Tacit Knowledge）を獲得していく過程が非常に大きい。

---

## 5. 制御工学・数理モデル

### 車輪ロボットの逆運動学 (メカナム/オムニホイール)
ロボットの目標並進速度 $(v_x, v_y)$ と角速度 $\omega$ から、各車輪 $i$ の目標回転角速度 $\omega_i$ を算出する式：
$$R\omega_i = \frac{1}{\sin\gamma_i} \Big[ \sin(\alpha_i+\gamma_i) v_x - \cos(\alpha_i+\gamma_i) v_y - \big( x_i\cos(\alpha_i+\gamma_i) + y_i\sin(\alpha_i+\gamma_i) \big) \omega \Big]$$

### 信号処理 (Scipy.signal)
センサのノイズ除去やフィルタリング設計の参考リソース。
- **[Scipy Signal Filtering](https://docs.scipy.org/doc/scipy/reference/signal.html#filtering)**
- **[Savitzky-Golay filter (Wikipedia)](https://en.wikipedia.org/wiki/Savitzky%E2%80%93Golay_filter)**: 平滑化のためのデジタルフィルタ。
