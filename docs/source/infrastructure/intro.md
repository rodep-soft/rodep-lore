# Infrastructure

コンテナ・仮想化・パッケージ管理の比較と内部構造。複数台のマシンやコンテナを扱うインフラ設計の知見。

| 記事 | 概要 |
|---|---|
| [コンテナオーケストレーション比較](container_orchestration_comparison.md) | Docker Compose・Nix・Pixi・ソースビルドそれぞれのトレードオフ。再現性・学習コスト・ハードウェアアクセスの観点で整理。 |
| [DockerとWSL2の内部アーキテクチャ](docker_wsl_architecture.md) | Docker Desktop・WSL2バックエンド・ネイティブLinuxでの挙動差異と、USBパススルーやGPU連携の仕組み。 |

```{toctree}
:maxdepth: 1
:glob:
:hidden:

*
```
