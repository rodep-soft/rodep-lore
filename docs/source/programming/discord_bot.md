# Discord bot tips

## Introduction

Discord Botをself-hostするときの運用の仕方についてのtips.

## How to code Bots?

取り敢えず書いて動かすだけなら`discord.py`を使うのがおすすめ. それなりに本格的にやるなら, TypeScriptで`discord.js`を使うと良いかと思う.  

個人的にRustの`serenity`は書きやすく感じたが, 書くコストは依然として高いため推奨はしない.

[Discord.py](https://discordpy.readthedocs.io/en/stable/)

## Working with Python

Pythonでプロジェクトを作る時は`pip`ではなく`uv`を使うと良い. 速度が速く、lockfileも存在し、メリットが多い. 

プロジェクトを`uv`で管理し、`git`で履歴保存しておくのが安定.

```bash
# initialize a project
$ uv init
# add discord.py
$ uv add discord.py
```

[uv](https://docs.astral.sh/uv/)

## How to deploy?

discordのbotはコードを書いた後、サーバでプログラムを起動しておく必要性がある.
ここでは、VPS等を使わず自分でサーバを立てて管理する(self-host)方法について解説する.











