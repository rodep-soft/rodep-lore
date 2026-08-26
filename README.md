# LORE.git

## このrepoについて

bot管理やシミュレータの公開等のためのリポジトリ。

※ ドキュメント（Wiki/知見）は [rodep-soft/docs](https://github.com/rodep-soft/docs) に移行しました。

## メンテナンス

- maintain/ prefixをつけてbranchを切り作業する

## Localで作業する方法

### Option1. Dockerを使う

推奨.

Dockerさえ入っていれば依存を入れる必要は無い.  
もしコンテナ内でバイナリを追加で入れた場合は、Dockerfileに追記すること.

```bash
# Dockerの動作確認
$ docker version
$ docker compose version

# 各種コンテナ立ち上げ (Makefile推奨)
$ make up-sim
$ make up-pio

# コンテナ落とす
$ docker compose down

# バグったときは
$ docker compose logs
```

### Option2. uvを使う

uvが入っている必要がある. `uv sync` で依存が入る.

```bash
$ uv sync
```

## その他注意

Docker Composeは`docker compose up`で一気に立ち上げない.  
Makefile経由で`make up-*`でコンテナを立ち上げることを推奨

#### Author

- Tatsuki Yano
