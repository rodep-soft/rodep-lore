# ROS2

このセクションに含まれる記事の一覧です。

| 記事 | 概要 |
|---|---|
| [ROS 2におけるDDSの実装差異とチューニング戦略](dds_tuning.md) | ROS 2の最大の革新の一つは、通信ミドルウェアとしてDDS（Data Distribution Service）を採用した点にあります。しかし、DDSの実装（ベンダ）によってその特性は大きく異なり、... |
| [ROS2 Discovery Server](discovery_server.md) | マルチキャストが通らない環境で ROS2 の通信を通すためのメモ. |
| [ROS2環境構築アプローチの比較と考察](environment_comparisons.md) | ROS2の開発環境を構築する際のアプローチについて、Pixi、Source Build、Nix、Dockerそれぞれの利点と欠点について深い考察をまとめます。 |
| [ExecutorとCallback Groupの高度なスレッド管理](executor.md) | ROS 2におけるメッセージの受信やタイマー処理の実行は、Executorと呼ばれるコンポーネントによって管理されます。ロボットの応答性を高め、リアルタイム性を担保するためには、この実行制御モデルを深... |
| [プロセス内通信（IPC）とComponent設計](intra_process_comms.md) | 大容量のセンサデータ（高解像度カメラ画像や3D LiDARの点群データなど）をノード間で頻繁に受け渡す場合、DDSを介したシリアライズとデシリアライズの処理がCPUリソースを著しく消費し、通信レイテン... |
| [ロボットシステム運用とデバッグの実践的作法](operation_and_debugging.md) | ROS 2を用いたロボットソフトウェア開発において、システムが複雑化するほど、標準ツールと定石（ベストプラクティス）の活用がプロジェクトの成否を分けます。 |
| [QoS (Quality of Service) の高度な設計と実践](qos.md) | ROS 2の潜在能力を最大限に引き出すためには、QoS（Quality of Service）の適切な設計が極めて重要です。通信の目的に応じた緻密なポリシー設定は、システムの信頼性とパフォーマンスを直... |
| [リアルタイム制御とシステムアーキテクチャ設計](realtime_architecture.md) | ロボットの多関節制御や高速な自律走行など、厳密な時間制約とマイクロ秒単位のジッタ低減が求められるシステムにおいて、ROS 2をリアルタイムOS（RTOS）や PREEMPT_RT パッチを適用した L... |
| [ROS2開発環境の構築：Nix、Docker、Pixi、Source Buildの徹底比較](ros2_build_environments.md) | ROS2の開発環境構築は、依存パッケージ（rosdep）の解決、環境の汚染防止、CI/CDとの統合など、多岐にわたる課題を孕んでいます。本稿では、我々が直面した数々のビルド環境の検証結果と、各ツールの... |
| [ROS 2 Controlにおける軌道制御とジョイント状態の管理](ros2_control_trajectory_and_joint_states.md) | ROS 2 Controlフレームワークを利用する際、ハードウェアインターフェースとコントローラマネージャ間の連携は非常に重要です。特に、`joint_state_broadcaster`とカスタムハ... |
| [ROS2・DDS・Zenohにおける通信基盤とQoSの深層](ros2_dds_zenoh_qos.md) | 本稿では、ROS2におけるプロセス間通信の根幹をなすDDS（Data Distribution Service）と、次世代通信基盤として注目されるZenohの比較、および実践的な設定やトラブルシューテ... |
| [micro-ROSとハードウェア制御の泥臭い実践記録](ros2_embedded_microros.md) | 本稿では、STM32などのマイクロコントローラ上で稼働するmicro-ROSの実装、および`ros2_control`を用いたアーム制御やハードウェア連携について、過去の検証とトラブルシューティングの... |
| [ROS2とRustの統合に関する課題](rust_integration_challenges.md) | ROS2のノードをRustで記述する（`ros2_rust` / `rclrs`）際のアーキテクチャ上の課題と、ビルドプロセスにおける問題点について整理します。 |
| [ROS 2におけるZenohとmicro-ROSの統合およびトランスポート層の評価](zenoh_micro_ros_integration.md) | ROS 2の最新動向において、Zenohの統合はネットワークトポロジーの管理に革新をもたらしています。Zenohのインテグレーションでは、各コンテキストが単一のZenohセッションにマッピングされ、こ... |
| [ROS 2におけるZenohとDDSのパフォーマンス比較とRMW設定](zenoh_vs_dds_performance.md) | ROS 2のミドルウェア層（RMW）として標準的に利用されるDDS（Data Distribution Service）は、RTPS（Real-Time Publish-Subscribe）プロトコル... |

```{toctree}
:maxdepth: 1
:glob:
:hidden:

*
```
