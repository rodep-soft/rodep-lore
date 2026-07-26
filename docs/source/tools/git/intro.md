# Git

単なるバックアップツールではなく、チームのコミュニケーション基盤としてのGit。コミット設計からチーム運用まで。

| 記事 | 概要 |
|---|---|
| [clone](clone.md) | SSH鍵の設定とリポジトリ取得。`--recurse-submodules`など知っておくと便利なオプション。 |
| [コミットとPR運用](commit_and_pr.md) | 良いコミットメッセージの書き方、PRの粒度とレビュー文化の設計。 |
| [Git Hooks](hooks.md) | `pre-commit`でフォーマット・リントを自動化し、CI前に問題を潰す仕組みの作り方。 |
| [rebase と履歴整理](rebase.md) | `git rebase -i`で汚いコミット履歴を整理する方法と、`--force-with-lease`の使い方。 |
| [サブモジュール](submodules.md) | 外部リポジトリを依存として扱うsubmoduleの罠と、`git subtree`との使い分け。 |
| [チーム開発プラクティス](team_practices.md) | 環境のコード化、暗黙知の文書化、属人化を防ぐための具体的な取り組み。 |

```{toctree}
:maxdepth: 1
:glob:
:hidden:

*
```
