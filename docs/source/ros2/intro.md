# ROS2

ロボットソフトウェアのデファクトスタンダード。通信ミドルウェアのDDS、リアルタイム制御のExecutor、環境構築の罠まで、実際にハマって得た知見を中心にまとめている。

| 記事 | 概要 |
|---|---|
| [開発環境構築の比較](build_environments.md) | Pixi、Source Build、Nix、Dockerそれぞれの設計思想と運用上の落とし穴。環境選定の判断基準を整理する。 |
| [DDSとZenoh](dds_and_zenoh.md) | ROS 2の通信基盤であるDDSの実装差異（FastDDS・CycloneDDS）と、次世代の選択肢Zenohを比較。QoSチューニングの具体例も含む。 |
| [プロセス内通信（IPC）とComponent設計](intra_process_comms.md) | 高帯域センサデータのノード間受け渡しでDDSのコピーコストを回避する方法。Composable Nodeの設計指針。 |
| [micro-ROS](microros.md) | STM32上でのmicro-ROS実装と`ros2_control`によるハードウェア連携。マイコン-PC間のトランスポート選択やデバッグ手法。 |
| [ロボットシステム運用とデバッグ](operation_and_debugging.md) | `ros2 topic`, `rqt`, `ros2 bag`の実践的な使い方と、ノードが死ぬ・通信が詰まる等のよくある障害対応。 |
| [リアルタイム制御とExecutor](realtime_and_executor.md) | SingleThreaded/MultiThreadedExecutorの違いと、リアルタイムスレッドへの移行。CallbackGroupの設計方針。 |
| [ros2_controlにおける軌道制御とジョイント状態管理](ros2_control_trajectory_and_joint_states.md) | `joint_state_broadcaster`とカスタムハードウェアインターフェース間の連携。よくある設定ミスと対処法。 |
| [ROS2とRustの統合](rust_integration_challenges.md) | `ros2_rust` / `rclrs` でノードを書く際のアーキテクチャ上の制約とビルドシステムの問題点。 |

```{toctree}
:maxdepth: 1
:glob:
:hidden:

*
```
