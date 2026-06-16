# ros2でのDockerの基本の使い方

基本ですがそれなりにDockerを使ったことがある人を想定しています.  

## Prerequisites

読者に求める前提

- Docker/Composeが何か説明できる
- Image, Container, Volume, Network, Registryがある程度わかっている

以下のGuideの内容はざっくり理解している程度.

[Guide](https://docs.docker.com/get-started/)

## WORKFLOW

1. `DockerHub`でベースイメージを探す

使いたいros2 distribution(Humbleとか)を決め、`DockerHub`で探す.

[DockerHub](https://hub.docker.com/)

ホストがamd64ならよく使われるのは`osrf/ros`(公式)  
Dockerはkernelをホストと共有するのでアーキテクチャ(amd64/arm64)に注意.

[Ros2 Image](https://hub.docker.com/r/osrf/ros)

自分でイメージを作成し、`docker push`しておいたり、githubの`packages`に上げておき使うこともできる.

2. `Dockerfile`を書く

勿論step1で見つけたイメージを`docker pull`するだけでは使い物にならないので、
自分でカスタマイズする必要性がある.

わからない場合は公式のリファレンスをみること.

[Dockerfile Reference](https://docs.docker.com/reference/dockerfile/)

テキトーに並べれば良いというものではなく、少なくとも

- `RUN`をまとめる
- ライブラリ等のバージョンを固定する
- ros2ならaptよりなるべく`rosdep`を使う

くらいは気を付けるべき.

様子を見て

- マルチステージビルド
- ENTRYPOINTを使う
- USERを作る

しても良いかもしれない.

3. `compose.yaml`を書く

`docker`コマンドに沢山のオプションをつけて毎回実行するのは非常に面倒であり、
基本的に`docker compose`コマンドを使って作業をすることを推奨する.

[Compose File Ref](https://docs.docker.com/reference/compose-file/)

`volume(bind mount)`や`docker network`, `GUI設定`などに若干コツがいるので後で紹介.

権限やネットワークで沼りたくないなら`network_mode: host`と`privileged: true`は書いておくべき.

ros2やるなら`stdin_open: true tty: true`も欲しい. Referenceを読むこと.

4. ビルド

ネットワークの速度が遅いところだと非常に時間がかかるので注意.

```bash
# build
$ docker compose build
```

5. コンテナに入って作業

```bash
# バックグラウンドで起動(detached)
$ docker compose up -d

# bashでコンテナ内に入る
$ docker compose exec <ServiceName> bash

# 出る時
$ exit
```

6. 回す

コンテナ内で作業をしていて、依存追加が必要になった時などは`Dockerfile`を書き換え、
またビルドをする. 

ただし、毎回Dockerfileを書き換えるたびにビルドしていると時間が勿体無いので、コンテナの中で
ある程度作業して動作確認してからファイルを書き換えて再びビルドをすると良い.

## CLI Usage

yanoがよく使うコマンド一覧(上記で紹介したものは除く)

```bash
# 普通にビルド
$ docker compose build
# cache使わないとき
$ docker compose build --no-cache

# ログ確認(debugでよく使う)
$ docker compose logs
# tailする
$ docker compose logs -f

# volumeとかnetworkも含めてdown
# stopもあるが、個人的にあまり使わない
$ docker compose down

# イメージがどれくらい容量食ってるか見る
# 特にraspiなど容量が少ない環境だと注意
$ docker system df

# イメージ一覧
$ docker compose images

# コンテナ一覧
$ docker compose ps

# 掃除
$ docker system prune
```

`docker`自体の生存確認等

```bash
# activeなら生きてる
$ sudo systemctl status docker

# dockerdのログ
$ sudo journalctl -u docker
```

## Linux以外でのDockerの運用

Dockerは`cgroupsv2`や`namespace`といった現代のLinux Kernelの機能を用いてプロセスを隔離, 制限することで
コンテナを実現している. そのため、Dockerを用いる際には必ず何処かにLinuxが必要である.

以下メジャーなOSでのDockerの構造について.

1. Native Linuxの場合

普通のDistributionであればDockerがネイティブに動く. 
overheadも少なく、理想的な環境である.

2. Windowsの場合

基本的に`WSL2`を用いることでLinux Kernelを用意し、そのカーネルを用いてDockerを使う. 
`Docker Desktop`を使う際でも同じ構造.

3. macOSの場合

VMでLinuxを用意し、それを用いてDockerを使う. 勿論Linuxホストより重い.

使う際は`colima`などを使えばあまり使い心地は変わらないが、GUI周りやGPUは殆ど使えないのでそこは注意.

## Docker Networkの設定

Dockerは専用のネットワークインターフェースを作る(docker0). 
デフォルトでは`bridge`モードであり、コンテナ同士は通信することができる.

`bridge`モードの時、例えばコンテナ内の172.17.0.2が外に出る時に192.168.1.100に変換される. 
要するにNATが動く(家庭用ルータなどと仕組みは同じ).

Webサーバなどでは、PortForwardだけで十分なことが多い.

```bash
# host側の8080番ポートをcontainer側の80番ポートに繋ぐ
$ docker run -p 8080:80 nginx
```

一方ros2のDDSではかなり厳しい点があり、特に以下

- UDP
- 複数ポート
- マルチキャスト(Discovery)

設定が複雑になりがちであり、接続が不安定になることも多い.

そこで推奨されるのが、ホストと完全にネットワークを共有する`network_mode: host`. 
compose.yamlに記述する. この設定は危険な側面もあるためセキュリティには注意.

```yaml
services:
  ros:
    build: .
    network_mode: host # ホストとネットワーク共有
```

## Dockerとデバイス

コンテナの中からのデバイスアクセスはかなり制限されているが(主にcgoupの影響)、`device:`を使うことでコンテナに渡すことができる.

```yaml
services:
  ros:
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0

# dockerコマンドでも--deviceで渡せる
```

実際のところは多数のデバイスを管理したり、開発時の利便性のために`privileged: true`を使うことも多い
(私は殆ど使っている). これはコンテナの隔離を弱める危険な操作であることは理解しなければならない.

```yaml
services:
  ros:
    privileged: true
```

## Docker Volume

`Volume`という名前の紛らわしいものが2つ存在し、`Docker Volume`と`Bind Mount`という名前がついているが、
ホストとコンテナでファイル共有する際は`Bind Mount`を使う. 前者はDockerが管理する専用ストレージのようなもので、
ros2での開発であれば十中八九VolumeといえばBind Mountのことを指している.

```yaml
services:
  ros:
    volumes:
      - ./src:/workspace/src
# volumes: に書いてあるが、これはbind mount
```

DB等を使わない限りあまり出番はないが、権限問題やパフォーマンス、パスの環境依存性を減らせるなどの理由で`Docker Volume`
が有利な点も一応ある. それでもros2開発では殆ど見ない.


## GUI

Docker内で通常はGUIを表示することはできないが、設定や工夫次第で実現できる.

1. X11/Waylandでソケット通信する

HostがLinuxであれば一番よくある方法. 

よくある構成としては,

Wayland Desktop -> XWayland -> Docker

Waylandを直接使うことはあまりないと思われる(面倒だったり、そもそもアプリ側が割と対応してない時もある)

X11を使う最小設定は以下参考

```yaml
services:
  ros:
    environment:
      - DISPLAY

    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix # Unix Domain Socketの共有
```

ここで`DISPLAY`環境変数は重要で、どのXサーバに描画するか決める重要な変数である.　
これは本質的にはただXClientとXServerでクライアントサーバ通信しているだけ.

GUIをこの方法で使うためには、以下のコマンドでアクセス許可をホスト側から出す必要がある.

```bash
# ホスト側で実行
$ xhost +local:
```

2. noVNC等を使う

ブラウザから見れて便利

詳しくは紹介しない. macosなどを使う際は1.の方法が使えないため別の方法をとる必要性がある.

## GPU

以下nvidiaのgpu想定. ただデバイスファイルを渡すだけでは無理なので注意.(intelのgpuなどならいけるかも. /dev/driなどで...)

```bash
# まずホスト側で確認
$ nvidia-smi
```

`compose.yaml`に書くならこんな感じでコンテナで使える.(環境によって割と変わるので自分で確認すること)

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

macosなどではvm噛ませてるのでそもそもGPUアクセラレーション自体が難しい.

gpuがないPCだとコメントアウトするのが面倒であるので、`compose.yaml compose.gpu.yaml`に分けてしまうか、
`profiles:`を使っても良いかもしれない.

### コマンド長い時など

`Makefile`や`Justfile`をタスクランナーとして使うと便利.


