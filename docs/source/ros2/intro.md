# ROS2

このセクションに含まれる記事の一覧です。

| 記事 | 概要 |
|---|---|
| [Build Environments](build_environments.md) | ROS2の開発環境を構築する際のアプローチについて、Pixi、Source Build、Nix、Dockerそれぞれの利点と欠点について深い考察をまとめます。 |
| [Dds And Zenoh](dds_and_zenoh.md) | ROS 2の最大の革新の一つは、通信ミドルウェアとしてDDS（Data Distribution Service）を採用した点にあります。しかし、DDSの実装（ベンダ）によってその特性は大きく異なり、... |
| [プロセス内通信（IPC）とComponent設計](intra_process_comms.md) | 大容量のセンサデータ（高解像度カメラ画像や3D LiDARの点群データなど）をノード間で頻繁に受け渡す場合、DDSを介したシリアライズとデシリアライズの処理がCPUリソースを著しく消費し、通信レイテン... |
| [Microros](microros.md) | 本稿では、STM32などのマイクロコントローラ上で稼働するmicro-ROSの実装、および`ros2_control`を用いたアーム制御やハードウェア連携について、過去の検証とトラブルシューティングの... |
| [ロボットシステム運用とデバッグの実践的作法](operation_and_debugging.md) | ROS 2を用いたロボットソフトウェア開発において、システムが複雑化するほど、標準ツールと定石（ベストプラクティス）の活用がプロジェクトの成否を分けます。 |
| [Realtime And Executor](realtime_and_executor.md) | ROS 2におけるメッセージの受信やタイマー処理の実行は、Executorと呼ばれるコンポーネントによって管理されます。ロボットの応答性を高め、リアルタイム性を担保するためには、この実行制御モデルを深... |
| [ROS 2 Controlにおける軌道制御とジョイント状態の管理](ros2_control_trajectory_and_joint_states.md) | ROS 2 Controlフレームワークを利用する際、ハードウェアインターフェースとコントローラマネージャ間の連携は非常に重要です。特に、`joint_state_broadcaster`とカスタムハ... |
| [ROS2とRustの統合に関する課題](rust_integration_challenges.md) | ROS2のノードをRustで記述する（`ros2_rust` / `rclrs`）際のアーキテクチャ上の課題と、ビルドプロセスにおける問題点について整理します。 |

```{toctree}
:maxdepth: 1
:glob:
:hidden:

*
```
