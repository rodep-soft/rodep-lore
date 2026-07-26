# Robotics

ロボットシステム全体を俯瞰した記事。制御・センシング・ナビゲーションを組み合わせて実機を動かすための設計思想。

| 記事 | 概要 |
|---|---|
| [ROS2 高度な制御理論と実装](ros2_advanced_control_theory.md) | `ros2_control`を使ったアクチュエータ制御の設計パターンと、リアルタイム性・安全性を両立する実装の考え方。 |
| [センサフュージョン戦略](sensor_fusion_strategy.md) | EKF・UKFを使った自己位置推定の実装選択肢と、センサ周期・遅延・信頼度の扱い方。 |

```{toctree}
:maxdepth: 1
:glob:
:hidden:

*
```
