# LORE.git

## このrepoについて

個人的なoutput, またbot管理やシミュレータの公開等するための試験的なリポジトリ。

若干教育用の資料も残していきたい。

追記, 改善PRは歓迎です.

sphinxを導入しており、mainにpushするとGitHub ActionsのCIが回って自動でデプロイされる仕組みになっています.

[公開中のドキュメント](https://rodep-soft.github.io/rodep-lore/)

## Docs作業時の注意

- ブランチは必ず切ってPRを出すこと
- 基本的に一人で勝手にMergeしないこと

**`./docs/source/*`に新しくディレクトリ/ファイルを作成して書いていく.**

## Docsの書式

myst-parser入れてるのでMarkdownで書ける.
reStructuredTextをわざわざ書く必要性はない.

一応どっちでも書ける.

## Localで作業する方法

### Option1. Dockerを使う

環境差異を潰せるので取り敢えず推奨.

Dockerさえ入っていれば依存を入れる必要は無い.  
composeで立ち上げてやれば`http://localhost:8080`でアクセスできる.

docsを上書きしたら自動でビルドされるはず.

もしコンテナ内でバイナリを追加で入れた場合は、Dockerfileに追記すること.

```bash
# Dockerの動作確認
$ docker version
$ docker compose version

# ビルドと立ち上げ(repoのrootディレクトリで実行)
$ docker compose build
$ docker compose up -d

# コンテナ落とす
$ docker compose down

# バグったときは
$ docker compose logs
# なるべくissueにバグは上げること
```
### Option2. uvを使う

uvが入っている必要がある. uv syncで依存が入る.  
Dockerを使う必要が無いためスムーズ. 基本的にビルドは`make`を使う.

自動化も可能ではある

```bash
$ uv sync
```

### Option3. apt/pipで入れる

可能だが非推奨

Dockerfileを参考に入れてみると多分うまくいく

## その他注意

Docker Composeは`docker compose up`で一気に立ち上げない.
Makefile経由で`make up-*`でコンテナを立ち上げることを推奨


#### Author

- Tatsuki Yano
