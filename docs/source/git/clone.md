# Git CLONE

## ssh鍵の設定

SSH鍵を設定していると全自動で同期できるのでするべき.

暗号化方式はrsaでもいいけど、現代標準はed25519.
コメントはemailが慣習になっているが正直何でもいい.

### ghを使った方法

```bash
$ ssh-keygen -t ed25519 -C "Comment" 
$ gh auth login
```

### browser経由

```bash
$ ssh-keygen -t ed25519 -C "Comment"
$ cat ~/.ssh/id_ed25519.pub
# 出力をすべてgithub.comのsettings->ssh-keyに貼り付け
```

### 確認方法

```bash
$ ssh -T git@github.com
# ここでHello,$USERならOk
```

## How to Clone

```bash
# githubでsshのURLを確認しておく
# カレントディレクトリに落とす
$ git clone <URL>
```

### 一部だけCloneする

```bash
# SSHで空の器を作っておく
$ git clone --filter=blob:none --no-checkout <URL>

# 移動
$ cd <repo>

# ほしいディレクトリを登録する
$ git sparse-checkout set <dirs you want to clone>

# 実体を取り出す
$ git checkout

# 以後`git pull`しても指定したフォルダだけがダウンロードされる
```

### ファイル1枚ほしいとき

```bash
# curlで殴る
# publicでないといけない
$ curl -L -O <Raw URL>
```
