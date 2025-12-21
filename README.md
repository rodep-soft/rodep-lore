# Wiki

## このrepoについて

個人的なアウトプットと教育用資料を残すことを目的としたrepository.  
制御やその周辺ツール、プログラミング等について書くつもり.

追記は歓迎です.

sphinxを導入しており、mainにpushするとGitHub ActionsのCIが回って自動でデプロイされる仕組みになっています.

[page](https://rodep-soft.github.io/rodep-lore/)

## 作業時の注意

- ブランチは必ず切ってPRを出すこと
- 基本的に一人で勝手にMergeしないこと

## Docsの書式

myst-parser入れてるのでMarkdownで書ける.
reStrusturedTextをわざわざ書く必要性はない.

一応どっちでも書ける.

## Localで作業する方法

### Option1. Dockerを使う

Dockerさえ入っていれば依存を入れる必要は無い.  
composeで立ち上げてやれば`http://localhost:8080`でアクセスできる.

docsを上書きしたら自動でビルドされるはず.

```bash
$ docker compose build
$ docker compose up -d
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


#### Author

- Tatsuki Yano
