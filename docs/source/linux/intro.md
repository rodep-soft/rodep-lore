# Linux

このセクションに含まれる記事の一覧です。

| 記事 | 概要 |
|---|---|
| [Linuxネットワークスタックの深層：systemd-networkdとiwdによるモダンな無線LAN管理](01_linux_network_stack_troubleshooting.md) | Linuxにおけるネットワーク管理は、古くは `ifconfig` や `wpa_supplicant` から始まり、現在では `NetworkManager` がデファクトスタンダードとして広く普及... |
| [ROS2環境構築のパラダイムシフト：NixOS, Docker, Pixi, Source Buildの徹底比較](02_linux_environment_reproducibility.md) | ロボティクスソフトウェア開発、とりわけROS2（Robot Operating System 2）の環境構築は、長きにわたり開発者を悩ませてきました。依存関係の複雑さ、OSバージョンとの密結合、そして... |
| [カーネルとデバイス管理の深淵：udevルールとシステムプログラミング](03_kernel_udev_device_handling.md) | ロボティクスや組み込みシステム開発において、USBシリアル変換ケーブル、カメラ、LiDARなどの周辺機器を正しく認識し、適切な権限でアクセスすることは、ソフトウェアを安定稼働させるための第一歩です。 |
| [カメラの扱い](camera.md) | Linuxは`Everything is a file`の原理に基づき、カメラもデバイスファイルとして扱う. |
| [cgroupsによるリソース分離とリアルタイム性確保](cgroups.md) | ロボットシステム上では、画像処理、経路計画、センサー制御など、計算負荷や要求されるリアルタイム性が異なる多数のプロセスが同時に稼働します。これらが限られたCPUやメモリリソースを奪い合い、ミッションク... |
| [Dockerの内部構造とLinuxカーネルの機能](docker_architecture_and_cgroups.md) | コンテナ技術を支える基盤技術であるNamespaceとCgroup、そしてDocker Engineの変遷について解説します。 |
| [DockerのLinuxカーネル依存性とcgroupsの役割](docker_cgroups_and_hypervisor.md) | Dockerコンテナは、仮想マシン（VM）とは異なり、ホストマシンのカーネルを共有する技術です。この仕組みの根幹には、Linuxカーネルが提供する「cgroups（コントロールグループ）」や「名前空間... |
| [eBPFによる革新的なオブザーバビリティ](ebpf.md) | 近年のLinuxシステムにおけるパフォーマンス解析とトラブルシューティングの領域で、最も強力なパラダイムシフトをもたらしているのが eBPF (Extended Berkeley Packet Fil... |
| [ファイルシステムとストレージの最適化](filesystem.md) | Linuxのファイルシステムにおいて、データ本体とメタデータを分離して管理するVFS（Virtual File System）とInodeの構造を理解することは、システム運用の第一歩です。 |
| [ネットワークアーキテクチャとトラフィック制御](network_tuning.md) | Linuxのネットワークスタックは高機能である反面、その複雑さゆえにトラブルシューティングが困難になりがちです。 |
| [プロセス管理と高度なデバッグ手法](process_debug.md) | システムで発生する不具合の根本原因を追究するためには、OSが提供するツール群を正しく活用し、プロセスの状態を詳細に観察する能力が求められます。 |
| [シェルスクリプトの実践的運用と自動化の境界](shell_automation.md) | 日々のシステム運用や環境構築において、シェルスクリプトは不可欠なツールですが、その脆さを補うための記述作法を守ることが運用の安定性に直結します。 |
| [systemd-networkdとdhcpcdによるネットワーク管理の比較](systemd_networkd_vs_dhcpcd.md) | Linux環境において、IPアドレスが正常に割り当てられない場合、場当たり的に`dhcpcd`コマンドを再実行して解決を図ることがあります。しかし、現代のUbuntuなどのディストリビューションでは、... |
| [WSL2環境下でのUSBデバイスパススルーとDockerネットワークの課題](wsl2_usb_and_docker_networking.md) | Windows Subsystem for Linux 2 (WSL2) を用いた開発環境では、ハードウェアとの連携やネットワーク周りで特有の課題が生じます。USBデバイスの認識については、`usbi... |

```{toctree}
:maxdepth: 1
:glob:
:hidden:

*
```
