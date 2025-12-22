# Intro to Docker

## Dockerとは何なのか

- コンテナ型の仮想環境
  OSをまるごと仮想環境として立ち上げるのではなく、必要な環境だけを切り出す

- ホストOSに依存しない

## 主要概念

とりあえずイメージとコンテナを押さえれば大丈夫.

- イメージ(Image)
  コンテナの設計図. DockerHubから取ってくる. 実用的には、Dockerfileから作る.

- コンテナ(Container)
  イメージから生成された実行中の環境

- ボリューム(Volume)
  データの永続化に使う

- ネットワーク(Network)
  コンテナ同士、また外部と通信するための仮想ネットワーク

## なぜ、Dockerを使うのか

「あの人のPCでは動くけど、私のPCでは動かない」を起こさないため.

全員が同じDockerfileから環境を作るため、ソフトウェアのバージョンを揃えたり、
依存の不足を防げる. 要するに、環境の再現性が良いから.

## インストール方法

WSL2またはUbuntuを使っている場合は、以下ページの手順でインストールできる.

[Dockerインストール](https://docs.docker.com/engine/install/ubuntu/)

### 動作確認

```bash
# dockerコマンドが使えるか確認
$ docker version

# これでHello from Dockerと表示されればOK
$ docker run hello-world
```

### やっておくべき設定

デフォルト設定だとdockerコマンドを使う際に毎回`sudo`が必要となり、面倒なので以下の設定をする.

```bash
# 基本的に不要だが、一応
# dockerグループを作成する
$ sudo groupadd docker

# dockerグループにユーザを追加
$ sudo usermod -aG docker $USER

# 反映 (logout/rebootでもよい)
$ newgrp docker
```

## 基本操作

今覚える必要はない. ざっと目を通せばOk

```bash
# イメージを取得してコンテナを起動する
$ docker run -it --rm python:3.11 bash

# コンテナ一覧
$ docker ps # 起動中コンテナ
$ docker ps -a # 停止も含めた全コンテナ(ls -a的な？イメージ)

# イメージ取得
$ docker pull <image>

# Dockerfileからイメージ作成
$ docker build -t <file_name> .

# イメージ一覧
$ docker images


# コンテナの停止、削除
$ docker stop <container_name>
$ docker rm <container_name>

# 起動中のコンテナにbashで入る
$ docker exec -it <container_name> bash
```

