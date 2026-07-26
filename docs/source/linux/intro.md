# Linux

Linuxの基礎から、カーネル・ネットワーク・シェル自動化まで。開発環境として日常的に使いこなすための実践的な知識を集めている。

| 記事 | 概要 |
|---|---|
| [Linux 基礎](00_linux_basics.md) | OSとカーネルの関係、ディストリビューションの選び方、Linuxを使い始める上での心構え。 |
| [カメラの扱い](camera.md) | `Everything is a file` の原則に基づいたV4L2・デバイスファイルの操作、カメラのセットアップ手順。 |
| [CgroupsとDocker](cgroups_and_docker.md) | コンテナ技術を支えるNamespaceとCgroup、Docker Engineの内部構造と変遷。 |
| [eBPF](ebpf.md) | カーネル空間で動くプログラムをユーザ空間から安全に注入できるeBPFの仕組みと、`bpftrace`・`perf`を使ったパフォーマンス解析。 |
| [ネットワーク深掘り](networking_deep_dive.md) | NetworkManager、`ip`コマンド、WiFi設定の実践。ロボット実機のネットワーク構成で詰まりがちな箇所を整理する。 |
| [シェルスクリプトと自動化](shell_automation.md) | `set -euo pipefail` から始まる堅牢なシェルスクリプトの書き方と、自動化の設計判断。 |
| [システム管理](system_administration.md) | ROS2開発環境の構築手法（NixOS・Docker・Pixi・Source Build）の徹底比較と運用ノウハウ。 |

```{toctree}
:maxdepth: 1
:glob:
:hidden:

*
```
