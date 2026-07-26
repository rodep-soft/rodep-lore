# Control_theory Overview

このセクションに含まれる記事の一覧です。

| 記事 | 概要 |
|---|---|
| [センサフュージョンと自己位置推定の理論・実践](01_sensor_fusion_and_odometry.md) | ロボティクスにおいて、自己位置推定（オドメトリ）は全ての自律移動の基盤となります。本稿では、IMU（慣性計測装置）、エンコーダ、Lidarを用いたセンサフュージョンの設計思想から、クォータニオンを用い... |
| [ROS2におけるSLAMパイプライン構築とハードウェア統合の深淵](03_ros2_slam_and_hardware_integration.md) | シミュレーション環境で完璧に動作するSLAM（Simultaneous Localization and Mapping）システムが、実機にデプロイした途端に破綻するのはロボティクスにおける日常茶飯事... |
| [Pid Vs Mpc](pid_vs_mpc.md) | ロボットの挙動を意図した通りに操作するためには、物理現象のモデル化と適切な制御アルゴリズムの選定が不可欠です。本稿では、モータレベルの低位制御から、システム全体の経路追従を行う上位制御までの階層的アプ... |

```{toctree}
:maxdepth: 1
:glob:
:hidden:

*
```
