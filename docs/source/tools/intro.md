# Tools

開発を効率化するツール群の実践的な使い方。Docker・Git・WSL2・CI/CDなど、日常的に触るものの「ちゃんとした使い方」をまとめている。

| 記事 | 概要 |
|---|---|
| [CI/CD パイプライン](cicd_workflows.md) | GitHub ActionsによるCI構成、colconビルドのキャッシュ戦略、ROS2のDockerイメージの扱い方。 |
| [DevContainer](devcontainer_advanced.md) | VS CodeのDevContainerでチーム開発環境を完全に標準化する方法。`.devcontainer/`の設計とGPU・USBデバイス対応。 |
| [Docker ベストプラクティス](docker_best_practices.md) | マルチステージビルド、レイヤーキャッシュ、privileged不要なデバイスアクセス、ロボット開発特有の設定。 |
| [Git ワークフロー](git_workflows_and_troubleshooting.md) | チーム開発でのブランチ戦略、PR運用、コンフリクト解消、よくやらかすミスとその対処法。 |
| [Proxmox](proxmox.md) | ベアメタルに近い仮想化サーバの構築。LXCとKVMの使い分け、ネットワーク設計。 |
| [WSL2](wsl2_best_practices.md) | WSL2でLinux開発環境を構築する際の設定最適化、USBデバイス連携、ファイルシステムのパフォーマンス。 |

```{toctree}
:maxdepth: 1
:glob:
:hidden:

*
```
