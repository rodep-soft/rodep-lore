# Docker & ROS2 開発ガイド

yanoが書いたROS2におけるDockerの基礎、ネットワーク、デバイスマウント、GUI表示、GPU連携についての解説まとめ。

---

## 基礎知識と環境構築

### 1. Dockerfileを書く
`Ubuntu`のベースイメージにROS2などを入れていく。

### 2. コンテナを起動する仕組みの理解
`Dockerfile`からイメージを作成（`build`）し、そのイメージを元にコンテナを実行（`run`）する。

### 3. compose.yamlを書く
`docker`コマンドに沢山のオプションをつけて毎回実行するのは非常に面倒であり、基本的には `docker compose` コマンドを使って作業することを推奨する。

* [Compose File Reference](https://docs.docker.com/reference/compose-file/)

`volume (bind mount)` や `docker network`, `GUI設定` などに若干コツがいる。
権限やネットワークで沼りたくないなら `network_mode: host` と `privileged: true` は書いておくべき。
ROS2をやるなら `stdin_open: true` / `tty: true` も指定する。

### 4. ビルド
ネットワークの速度が遅い場所だと時間がかかるので注意。

```bash
# build
$ docker compose build
```

### 5. コンテナに入って作業

```bash
# バックグラウンドで起動 (detached)
$ docker compose up -d

# bashでコンテナ内に入る
$ docker compose exec <ServiceName> bash

# 出る時
$ exit
```

### 6. 開発運用
コンテナ内で作業をしていて、依存追加が必要になった時などは `Dockerfile` を書き換えて再ビルドする。
ただし、毎回 `Dockerfile` を書き換えるたびにビルドしていると時間が勿体無いため、コンテナの中である程度作業して動作確認してからファイルを書き換えて再びビルドすると良い。

---

## CLI Usage

よく使うコマンド一覧（上記で紹介したものを除く）

```bash
# 普通にビルド
$ docker compose build
# キャッシュを使わない時
$ docker compose build --no-cache

# ログ確認 (デバッグでよく使う)
$ docker compose logs
# ログをリアルタイム追跡
$ docker compose logs -f

# volumeやnetworkも含めてコンテナを停止・削除
$ docker compose down

# イメージがどれくらい容量を食っているか確認
# 特にRaspberry Piなど容量が少ない環境では注意
$ docker system df

# イメージ一覧
$ docker compose images

# コンテナ一覧
$ docker compose ps

# 未使用リソースの掃除
$ docker system prune
```

`docker` 自体の生存確認等

```bash
# activeなら生きてる
$ sudo systemctl status docker

# dockerdのログ確認
$ sudo journalctl -u docker
```

---

## Linux以外でのDockerの運用

Dockerは `cgroupsv2` や `namespace` といった現代のLinux Kernelの機能を用いてプロセスを隔離・制限することでコンテナを実現している。そのため、Dockerを用いる際には必ず何処かにLinuxが必要である。

1. **Native Linuxの場合**
   普通のDistributionであればDockerがネイティブに動く。オーバーヘッドも少なく、最も理想的な環境。
2. **Windowsの場合**
   基本的に `WSL2` を用いることでLinux Kernelを用意し、そのカーネルを用いてDockerを使う。 `Docker Desktop` を使う際でも同じ構造。
3. **macOSの場合**
   VMでLinuxを用意し、それを用いてDockerを使う。勿論Linuxホストより重い。
   使う際は `colima` などを使えば使い心地はあまり変わらないが、GUI周りやGPUは殆ど使えないので注意。

---

## Docker Networkの設定（ROS2 DDS対策）

Dockerは専用のネットワークインターフェースを作る（`docker0`）。デフォルトでは `bridge` モードであり、コンテナ同士は通信することができる。

`bridge` モードの時、例えばコンテナ内の `172.17.0.2` が外に出る時に `192.168.1.100` に変換される。要するにNATが動く（家庭用ルータなどと仕組みは同じ）。
Webサーバなどであれば Port Forwarding だけで十分なことが多い。

```bash
# ホスト側の8080番ポートをコンテナ側の80番ポートに繋ぐ
$ docker run -p 8080:80 nginx
```

一方、**ROS2のDDS通信では以下の特性があるため `bridge` モードの設定はかなり厳しい**。
* UDP通信
* 複数ポートの使用
* マルチキャストによるノード自動発見（Discovery）

設定が複雑になりがちであり、接続が不安定になることも多い。
そこで推奨されるのが、**ホストと完全にネットワークを共有する `network_mode: host`**。

```yaml
services:
  ros:
    build: .
    network_mode: host # ホストとネットワーク共有
```

---

## Dockerとデバイスマウント

コンテナの中からのデバイスアクセスはかなり制限されているが（主にcgroupsの影響）、`devices:` を使うことでコンテナに渡すことができる。

```yaml
services:
  ros:
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
```

実際のところ、多数のデバイスを管理したり開発時の利利便性を確保するために `privileged: true` を使うことも多い（私自身も殆ど使っている）。コンテナの隔離を弱めるリスクはあるが、ロボティクス開発では重宝する。

```yaml
services:
  ros:
    privileged: true
```

---

## Docker Volume と Bind Mount

`Volume` という名前の紛らわしいものが2つ存在し、`Docker Volume` と `Bind Mount` という名前がついているが、**ホストとコンテナでファイル共有する際は Bind Mount を使う**。
前者はDockerが管理する専用ストレージのようなもので、ROS2での開発であれば十中八九 Volume といえば Bind Mount のことを指す。

```yaml
services:
  ros:
    volumes:
      - ./src:/workspace/src # Bind Mount
```

---

## GUI（Rviz2 / Gazeboなど）の表示

Docker内で通常はGUIを表示することはできないが、設定や工夫次第で実現できる。

### 1. X11 / Waylandのソケット通信
ホストがLinuxであれば最も一般的な方法。
構成例: `Wayland Desktop -> XWayland -> Docker`

X11を使う最小設定:
```yaml
services:
  ros:
    environment:
      - DISPLAY
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix # Unix Domain Socketの共有
```

`DISPLAY` 環境変数はどのXサーバに描画するかを決める重要変数。本質的にはXClientとXServerのクライアント・サーバ通信。
GUIを使うためには、以下のコマンドでアクセス許可をホスト側から出す必要がある。

```bash
# ホスト側で実行
$ xhost +local:
```

### 2. noVNCなどの利用
ブラウザから描画を確認できるため、macOSなどでX11フォワーディングが難しい場合に有効。

---

## GPU設定 (NVIDIA)

NVIDIA GPUをコンテナ内で使う場合は、単にデバイスファイルを渡すだけでは動かない。

```bash
# ホスト側での確認
$ nvidia-smi
```

`compose.yaml` の記述例:
```yaml
services:
  ros:
    image: ros:jazzy
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

GPUが無いPCで実行する際のバッティングを防ぐため、`compose.yaml` と `compose.gpu.yaml` に分けるか、`profiles:` 機能を活用すると便利。

### タスクランナーの活用
コマンドが長くなる場合は、`Makefile` や `Justfile` をタスクランナーとして使うと開発が快適になる。
