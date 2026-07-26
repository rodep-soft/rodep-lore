# ROS2 Discovery Server

マルチキャストが通らない環境で ROS2 の通信を通すためのメモ.
学校 Wi-Fi や一部の閉じたネットワークで特に役に立つ.

## 背景

ROS2 の通常のノード発見はマルチキャストに依存する.
そのため、学内ネットワークのようにマルチキャストが遮断される環境では、ノード同士がうまく見つからない.

この問題を避ける方法の一つが Discovery Server で、ノード発見を中央サーバ経由にして、通信を主にユニキャストで流す.

参考:

- [ROS 2 Discovery Server](https://docs.ros.org/en/humble/Tutorials/Advanced/Discovery-Server/Discovery-Server.html)

## 何が嬉しいのか

- マルチキャストが通らないネットワークでも ROS2 を使いやすい
- ノード発見を中央に寄せられる
- Docker やリモート環境でも構成しやすい

## 使い方

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

## サーバの IP を確認する

```bash
hostname -I
ip a
```

IP アドレスはサーバ側のものを指定する.

## Docker を使う場合

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

## 注意

- `ROS_DISCOVERY_SERVER` の設定はサーバ側とクライアント側で揃える
- `network_mode: host` が使えない OS では構成が少し面倒になる
- まずはホスト上で単体テストしてから Docker に載せると切り分けやすい

## おわりに

Discovery Server を使うと、マルチキャストが厳しい環境でも ROS2 をかなり扱いやすくできる.
学校 Wi-Fi みたいな環境で詰まったときの定番の逃げ道として覚えておくと便利.
