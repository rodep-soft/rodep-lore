# Dds And Zenoh

## ROS 2におけるDDSの実装差異とチューニング戦略

ROS 2の最大の革新の一つは、通信ミドルウェアとしてDDS（Data Distribution Service）を採用した点にあります。しかし、DDSの実装（ベンダ）によってその特性は大きく異なり、システムのデプロイメント環境に応じた適切な選定とチューニングが求められます。

### DDS実装の特性と選定基準

ROS 2では、環境変数 `RMW_IMPLEMENTATION` を切り替えることで、アプリケーションコードを変更せずにミドルウェアを変更できます。主要な実装には以下の特徴があります。

* **Fast DDS (eProsima)**
  現在のデフォルト実装です。同一ホスト内の通信において、共有メモリ（Shared Memory Transport）をデフォルトで活用し、大容量データの高速転送に優れています。一方で、複雑なネットワーク環境ではディスカバリパケットが輻輳しやすい傾向があります。
* **Cyclone DDS (Eclipse)**
  マルチキャストが制限されたWi-Fi環境や、パケットロスが発生しやすい不安定なネットワーク下において、ディスカバリ処理が比較的安定して動作する傾向があります。小規模から中規模の分散システムで高い信頼性を発揮します。
* **Connext DDS (RTI)**
  商用実装であり、極めて高度なチューニング機能と強力なサポートツール群（Admin Consoleなど）を提供します。航空宇宙や自動運転など、ミッションクリティカルな要件が求められるシステムで採用されます。

### 大規模ネットワークにおけるディスカバリ問題の解決

標準的なDDSのディスカバリ（Simple Discovery）は、UDPマルチキャストを用いてノード同士を動的に発見します。しかし、ノード数やトピック数が増大すると、ディスカバリアトラフィックがネットワーク帯域を圧迫し、いわゆる「マルチキャストストーム」を引き起こす危険性があります。

この課題に対処するため、Fast DDSが提供する「Discovery Server」機能を活用することが推奨されます。特定のノードをディスカバリサーバとして稼働させ、各ノードはユニキャストでサーバに接続することで、マルチキャスト通信を完全に排除し、大規模な分散システムにおいても安定した通信基盤を構築することが可能となります。

### 通信パフォーマンスの最適化

有線LAN、Wi-Fi、あるいはVPNを経由するような複合的なネットワークトポロジにおいて、DDSのデフォルト設定では最適なパフォーマンスを得られない場合があります。XML形式のプロファイル設定ファイルを作成し、使用するネットワークインターフェース（NIC）の明示的な指定や、送信バッファサイズの拡張を行うことで、レイテンシとスループットを大幅に改善できます。

---

## QoS (Quality of Service) の高度な設計と実践

ROS 2の潜在能力を最大限に引き出すためには、QoS（Quality of Service）の適切な設計が極めて重要です。通信の目的に応じた緻密なポリシー設定は、システムの信頼性とパフォーマンスを直結させます。

### Reliability（信頼性）と History（履歴）

通信の確実性を担保する `Reliability` には、`Reliable` と `BestEffort` が存在します。
センサデータ（LiDARの点群やカメラ画像など）のように、高頻度で更新され、常に最新の値のみが価値を持つトピックにおいては、パケット再送のオーバーヘッドを避けるため `BestEffort` を選択します。この際、`History` は `KeepLast` とし、`Depth` を 1〜5 程度の小さな値に設定するのが定石です。
一方、ロボットへの動作指令や状態遷移の通知など、データの欠損が許されない場合は `Reliable` を設定します。

### Durability（永続性）とラッチ通信

ROS 1の `latch=True` に相当する機能は、QoSの `Durability` パラメータによって実現されます。
静的なマップ情報（`map`）や、ロボットの静的な座標変換（`/tf_static`）など、後から参加したサブスクライバに対しても過去のデータを確実に届ける必要がある場合、パブリッシャ側の `Durability` を `TransientLocal` に設定します。デフォルトの `Volatile` では、接続確立前に送信されたデータは受信できません。

### Liveliness と Deadline によるフェイルセーフ

システム全体の堅牢性を高める上で、障害検知のメカニズムは不可欠です。
`Liveliness` を設定することで、ノードの生存状態をDDSレイヤで監視し、プロセスがサイレントにダウンした際にも即座にコールバックを発火させることが可能となります。
また、`Deadline` を活用すると、「一定期間内に必ずデータが到着すること」を保証でき、指定期間を超過した場合にはイベントとして検知できます。これにより、ハードウェア障害やネットワーク断線をアプリケーション層で速やかに捉え、安全にロボットを停止させるフェイルセーフ機構を構築できます。

### QoSのミスマッチとデバッグ手法

パブリッシャとサブスクライバ間でQoSの設定に互換性がない場合（例：パブリッシャが `BestEffort` で、サブスクライバが `Reliable` を要求する場合など）、通信は静かに失敗し、データは一切届きません。
この問題を特定するためには、`ros2 topic info /topic_name --verbose` コマンドを利用し、各エンドポイントのQoSプロファイルを詳細に比較確認することが基本動作となります。

---

## ROS2・DDS・Zenohにおける通信基盤とQoSの深層

本稿では、ROS2におけるプロセス間通信の根幹をなすDDS（Data Distribution Service）と、次世代通信基盤として注目されるZenohの比較、および実践的な設定やトラブルシューティングについて詳述します。

### 1. DDSからZenohへのパラダイムシフト

ROS2の標準的なミドルウェアインターフェース（RMW）は長らくDDSに依存してきました。DDSはRTPS（Real-Time Publish-Subscribe）プロトコルを基盤としており、純粋なUDPのみならず、マルチキャストを用いた高度なディスカバリ機構を備えています。しかし、ネットワークを跨ぐ通信や、制約の大きいネットワーク環境下では、DDSのマルチキャストディスカバリがボトルネックになるケースが多発します。

これに対する解決策として、`rmw_zenoh`への移行が議論されています。Zenohは、各コンテキストを単一のZenohセッションにマッピングし、そのセッションを全てのPublisher、Subscription、Service、Clientで共有します。コンテキストはローカルのグラフキャッシュを保持し、作成時および破棄時に一意のliveliness tokenを用いてトポロジを管理します。

#### Zenohのルーティング設定と実行ログ

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

### 2. QoS設定と通信の最適化

ROS2のQoS（Quality of Service）は、MQTTのQoS（At most once, At least once, Exactly onceなど）の概念を踏襲しつつ、OOP（オブジェクト指向プログラミング）的なプロセスモデルへと落とし込まれています。C++で実装されるROS2のノードは、UNIXのプロセス的な感覚を抽象化したものと言えます。

しかし、ロボット内部の閉じたネットワークだけでなく、外部のPC（ブローカー）を介した遠隔制御やテレメトリの収集を行う場合、純粋なMQTTを仲介するアーキテクチャが有効です。

```text
STM32(micro-ROS) <----> Laptop(ROS2 MQTT Node) <----> Host PC(MQTT Broker)
```

この構成を採用することで、ROSのツールチェーンに縛られることなく、Webシステムとの連携が容易になります。

### 3. プロセス管理とトラブルシューティング

ROS2デーモンやノードがゾンビプロセス化し、通信がスタックする問題は頻発します。このような場合、通常の`Ctrl+C`ではプロセスが完全にキルされないことがあります。これを確実に対処するためのコマンドは以下の通りです。

```bash
pkill -9 -f ros && ros2 daemon stop
```

このコマンドにより、プロセス名に`ros`を含む全てのプロセスにSIGKILLを送信し、その後ROS2固有のデーモンプロセスを安全に停止させます。

### 4. 大容量データ（画像）の転送とトランスポート

プロセス間で画像を転送する場合、`sensor_msgs/Image`の生データでは帯域を圧迫します。そこで`image_transport`を用いた圧縮が必須となります。最近では`ffmpeg_image_transport`を用いたH.264/HEVCストリーミングが検証されています。

```bash
ros-jazzy-ffmpeg-image-transport: 1.0.1-2 → 1.0.2-1
ros-jazzy-compressed-image-transport: 4.0.3-1 → 4.0.4-1
```

しかし、HEVCコーデックは現状では不安定な挙動を示すことが多く、ROS2の標準（デフォルト）として採用するにはリスクが伴います。現状では`compressed_image_transport`によるJPEG圧縮が安定しています。

### 5. 外部GUIとのインテグレーション

FlutterやTauriを用いたモダンなGUIとROS2を連携させる際、`rosbridge_server`が極めて有用です。WebSocket経由でJSON形式のメッセージを送受信することで、C++やRustのネイティブ環境に依存しないUI開発が可能になります。

```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

画像データなどは、ROSノード側でBase64にエンコードし、JSONにペイロードとして格納して送信します。Flutter側ではそれを受信してデコードするだけで、リアルタイムなカメラ映像の描画が実現できます。このアプローチにより、複雑なRMWのセットアップをクライアント端末側で行う必要がなくなり、開発効率が飛躍的に向上します。


---

## ROS 2におけるZenohとDDSのパフォーマンス比較とRMW設定

ROS 2のミドルウェア層（RMW）として標準的に利用されるDDS（Data Distribution Service）は、RTPS（Real-Time Publish-Subscribe）プロトコルに基づいており、単なるUDP通信以上の複雑なQoS管理を提供します。しかし、ネットワーク環境によってはDDSのディスカバリプロセスや通信のオーバーヘッドが問題となる場合があります。

これに対する代替として、`rmw_zenoh`への関心が高まっています。Zenohは、特に分散環境や制約の厳しいネットワークにおいて、より効率的でスケーラブルな通信を実現します。ルーターを介したネットワークや、複数台のマシンが混在する環境下において、DDSのマルチキャストディスカバリが到達しない問題に対して、Zenohは非常に有効な解決策となります。

実運用においては、Dockerコンテナ内での運用やTailscaleを利用したVPN越しでのノード間通信を考慮する必要があります。DDSを利用し続ける場合でも、特定トピックのQoS設定の最適化や、FastDDS/CycloneDDSのXML設定ファイルを通じたネットワークインターフェースの明示的な指定が不可欠です。

---

## ROS2 Discovery Server

マルチキャストが通らない環境で ROS2 の通信を通すためのメモ.
学校 Wi-Fi や一部の閉じたネットワークで特に役に立つ.

### 背景

ROS2 の通常のノード発見はマルチキャストに依存する.
そのため、学内ネットワークのようにマルチキャストが遮断される環境では、ノード同士がうまく見つからない.

この問題を避ける方法の一つが Discovery Server で、ノード発見を中央サーバ経由にして、通信を主にユニキャストで流す.

参考:

- [ROS 2 Discovery Server](https://docs.ros.org/en/humble/Tutorials/Advanced/Discovery-Server/Discovery-Server.html)

### 何が嬉しいのか

- マルチキャストが通らないネットワークでも ROS2 を使いやすい
- ノード発見を中央に寄せられる
- Docker やリモート環境でも構成しやすい

### 使い方

まずサーバ側の PC で Discovery Server を起動する.

```bash
fastdds discovery --server-id 0
```

次に、サーバとクライアントの両方で同じ環境変数を設定する.

```bash
export ROS_DISCOVERY_SERVER=ip-address-of-server:11811
```

クライアント側はこの設定だけでよい.
ROS2 ノードを複数立てても問題ない.

### サーバの IP を確認する

```bash
hostname -I
ip a
```

IP アドレスはサーバ側のものを指定する.

### Docker を使う場合

Linux なら `network_mode: host` を使うと、コンテナをホストと同じネットワーク空間に置ける.
Discovery Server と環境変数を揃えれば、Docker 内の ROS2 でも通信しやすい.

例:

```yaml
services:
  ros2:
    build:
      context: .
      dockerfile: Dockerfile

    container_name: ros2_container
    tty: true
    privileged: true
    network_mode: host
    working_dir: /root/ros_ws

    environment:
      - ROS_DOMAIN_ID=0
      - DEBIAN_FRONTEND=noninteractive
      - ROS_DISCOVERY_SERVER=100.121.25.123:11811
    volumes:
      - ~/.ssh:/root/.ssh:ro
      - ./ros_ws:/root/ros_ws
      - ~/.ccache:/root/.ccache
    devices:
      - /dev:/dev
```

### 注意

- `ROS_DISCOVERY_SERVER` の設定はサーバ側とクライアント側で揃える
- `network_mode: host` が使えない OS では構成が少し面倒になる
- まずはホスト上で単体テストしてから Docker に載せると切り分けやすい

### おわりに

Discovery Server を使うと、マルチキャストが厳しい環境でも ROS2 をかなり扱いやすくできる.
学校 Wi-Fi みたいな環境で詰まったときの定番の逃げ道として覚えておくと便利.


---
