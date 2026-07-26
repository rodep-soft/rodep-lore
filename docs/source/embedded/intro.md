# Embedded Overview

このセクションに含まれる記事の一覧です。

| 記事 | 概要 |
|---|---|
| [IMUのドリフト現象とMEMSセンサーのノイズ特性](imu_drift_and_sensor_noise.md) | 慣性計測装置（IMU）を用いた姿勢推定やオドメトリの算出において、センサードリフトは避けて通れない課題です。特に角速度（ジャイロセンサー）の出力を積分して角度を求める際、センサー自体が持つ微小なバイア... |
| [STM32CubeMXを利用したHALとI2C通信の実装](stm32_hal_and_i2c_communication.md) | STM32マイクロコントローラを用いた組み込み開発において、STM32CubeMXはピンアサインやクロックツリーの初期設定を大幅に効率化します。生成されたMakefileとVSCodeを組み合わせるこ... |
| [STM32開発におけるHALとLL、および通信アーキテクチャ](stm32_hal_vs_ll.md) | 組み込み開発、特にSTM32マイクロコントローラを使用する際のライブラリ選定と、外部PC（ROS2環境）との通信手法について考察します。 |
| [組み込み開発におけるSTM32 HAL/LLAPIの比較およびRustの活用](stm32_hal_vs_ll_and_rust.md) | 組み込み開発におけるパフォーマンスチューニングでは、STMicroelectronics社の提供するHAL（Hardware Abstraction Layer）とLL（Low-Layer）APIの選... |

```{toctree}
:maxdepth: 1
:glob:
:hidden:

*
```
