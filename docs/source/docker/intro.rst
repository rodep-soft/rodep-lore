Intro to Docker
================

ロボット製作において、ROSなどの複雑な環境を統一する
試みとして、Dockerを使用している。

なぜDockerを使うのか
----------------------

* **環境の共通化** 「あの人のPCでは動くけど、私のPCでは動かない」を防ぐ.
* **環境汚染防止** ホストPCの環境を汚さずにlibを試すことができる.
* **セットアップが楽** コマンド一発で環境が整う

インストール方法
------------------

各OSごとにDocsを参照してインストール

Ubuntu/WSL2の場合は以下リンクの手順でインストール可能.

他のOSも似たような手順で入る

* `DockerDocs`_

.. DockerDocs: https://docs.docker.com/engine/install/ubuntu/

動作確認
~~~~~~~~~~~

.. code-block:: bash

   # Docker/DockerComposeが入っていることを確認
   $ docker version
   $ docker compose version

   # Hello from Dockerと出力されれば問題無し
   $ docker run hello-world


やっておくべき設定
------------------

デフォルトでは``sudo docker ...``と打つ必要があるが、面倒を避けるため、またスクリプトから扱うことが難しくなるため、以下の設定をすることを推奨する.

.. code-block:: bash

   # dockerグループの作成(必要ないことも多い)
   $ sudo groupadd docker

   # ユーザをdockerグループに追加
   $ sudo usermod -aG docker $USER

   # 設定後、再起動か一度ログアウトする必要がある



