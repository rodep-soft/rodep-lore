# Embedded Overview

このセクションに含まれる記事の一覧です。

| 記事 | 概要 |
|---|---|
| [IMUのドリフト現象とMEMSセンサーのノイズ特性](imu_drift_and_sensor_noise.md) | 慣性計測装置（IMU）を用いた姿勢推定やオドメトリの算出において、センサードリフトは避けて通れない課題です。特に角速度（ジャイロセンサー）の出力を積分して角度を求める際、センサー自体が持つ微小なバイア... |
| [Stm32 Hal Vs Ll Integration](stm32_hal_vs_ll_integration.md) | 組み込み開発、特にSTM32マイクロコントローラを使用する際のライブラリ選定と、外部PC（ROS2環境）との通信手法について考察します。 |

```{toctree}
:maxdepth: 1
:glob:
:hidden:

*
```
