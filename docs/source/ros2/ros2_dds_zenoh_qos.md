# ROS2・DDS・Zenohにおける通信基盤とQoSの深層

本稿では、ROS2におけるプロセス間通信の根幹をなすDDS（Data Distribution Service）と、次世代通信基盤として注目されるZenohの比較、および実践的な設定やトラブルシューティングについて詳述します。

## 1. DDSからZenohへのパラダイムシフト

ROS2の標準的なミドルウェアインターフェース（RMW）は長らくDDSに依存してきました。DDSはRTPS（Real-Time Publish-Subscribe）プロトコルを基盤としており、純粋なUDPのみならず、マルチキャストを用いた高度なディスカバリ機構を備えています。しかし、ネットワークを跨ぐ通信や、制約の大きいネットワーク環境下では、DDSのマルチキャストディスカバリがボトルネックになるケースが多発します。

これに対する解決策として、`rmw_zenoh`への移行が議論されています。Zenohは、各コンテキストを単一のZenohセッションにマッピングし、そのセッションを全てのPublisher、Subscription、Service、Clientで共有します。コンテキストはローカルのグラフキャッシュを保持し、作成時および破棄時に一意のliveliness tokenを用いてトポロジを管理します。

### Zenohのルーティング設定と実行ログ

実際にZenohクライアントとして接続を確立する場合、環境変数を用いてエンドポイントをオーバーライドすることが可能です。以下は特定のTCPエンドポイントへ接続するための設定例です。

```bash
export ZENOH_CONFIG_OVERRIDE='mode="client";connect/endpoints=["tcp/100.71.63.36:7447"]'
ros2 run rmw_zenoh_cpp rmw_zenohd
```

このデーモンを起動した際の実践的なログは以下のようになります。

```text
2026-01-22T12:20:10.839902Z  INFO ThreadId(02) zenoh::net::runtime: Using ZID: c0f9d6fcf611640ef108608836df4a75
2026-01-22T12:20:10.840324Z  INFO ThreadId(02) zenoh::net::runtime::orchestrator: Zenoh can be reached at: tcp/[fd7a:115c:a1e0::5e01:dd67]:7447
2026-01-22T12:20:10.840329Z  INFO ThreadId(02) zenoh::net::runtime::orchestrator: Zenoh can be reached at: tcp/100.85.221.54:7447
2026-01-22T12:20:10.840331Z  INFO ThreadId(02) zenoh::net::runtime::orchestrator: Zenoh can be reached at: tcp/[fe80::b225:aaff:fe40:d461]:7447
2026-01-22T12:20:10.840335Z  INFO ThreadId(02) zenoh::net::runtime::orchestrator: Zenoh can be reached at: tcp/10.42.0.48:7447
Started Zenoh router with id c0f9d6fcf611640ef108608836df4a75
```

このように、IPv4およびIPv6の双方でリッスンが行われ、ZID（Zenoh ID）を用いてセッションが管理されます。プロセスを終了する際は、`^C`で安全にセッションを閉じることが推奨されます（`close session zid=...`が出力されます）。

## 2. QoS設定と通信の最適化

ROS2のQoS（Quality of Service）は、MQTTのQoS（At most once, At least once, Exactly onceなど）の概念を踏襲しつつ、OOP（オブジェクト指向プログラミング）的なプロセスモデルへと落とし込まれています。C++で実装されるROS2のノードは、UNIXのプロセス的な感覚を抽象化したものと言えます。

しかし、ロボット内部の閉じたネットワークだけでなく、外部のPC（ブローカー）を介した遠隔制御やテレメトリの収集を行う場合、純粋なMQTTを仲介するアーキテクチャが有効です。

```text
STM32(micro-ROS) <----> Laptop(ROS2 MQTT Node) <----> Host PC(MQTT Broker)
```

この構成を採用することで、ROSのツールチェーンに縛られることなく、Webシステムとの連携が容易になります。

## 3. プロセス管理とトラブルシューティング

ROS2デーモンやノードがゾンビプロセス化し、通信がスタックする問題は頻発します。このような場合、通常の`Ctrl+C`ではプロセスが完全にキルされないことがあります。これを確実に対処するためのコマンドは以下の通りです。

```bash
pkill -9 -f ros && ros2 daemon stop
```

このコマンドにより、プロセス名に`ros`を含む全てのプロセスにSIGKILLを送信し、その後ROS2固有のデーモンプロセスを安全に停止させます。

## 4. 大容量データ（画像）の転送とトランスポート

プロセス間で画像を転送する場合、`sensor_msgs/Image`の生データでは帯域を圧迫します。そこで`image_transport`を用いた圧縮が必須となります。最近では`ffmpeg_image_transport`を用いたH.264/HEVCストリーミングが検証されています。

```bash
ros-jazzy-ffmpeg-image-transport: 1.0.1-2 → 1.0.2-1
ros-jazzy-compressed-image-transport: 4.0.3-1 → 4.0.4-1
```

しかし、HEVCコーデックは現状では不安定な挙動を示すことが多く、ROS2の標準（デフォルト）として採用するにはリスクが伴います。現状では`compressed_image_transport`によるJPEG圧縮が安定しています。

## 5. 外部GUIとのインテグレーション

FlutterやTauriを用いたモダンなGUIとROS2を連携させる際、`rosbridge_server`が極めて有用です。WebSocket経由でJSON形式のメッセージを送受信することで、C++やRustのネイティブ環境に依存しないUI開発が可能になります。

```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

画像データなどは、ROSノード側でBase64にエンコードし、JSONにペイロードとして格納して送信します。Flutter側ではそれを受信してデコードするだけで、リアルタイムなカメラ映像の描画が実現できます。このアプローチにより、複雑なRMWのセットアップをクライアント端末側で行う必要がなくなり、開発効率が飛躍的に向上します。
