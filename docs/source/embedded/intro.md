# Embedded

STM32のHAL/LLドライバ、センサノイズ対策、マイコンとPCの通信設計。実機を動かす上で避けられない組み込みの泥臭い話。

| 記事 | 概要 |
|---|---|
| [IMUドリフトとセンサノイズ](imu_drift_and_sensor_noise.md) | MEMSジャイロのバイアスドリフト、振動ノイズのLPFによる除去、EKFでの補正設計。 |
| [STM32 HALとLL統合](stm32_hal_vs_ll_integration.md) | HALとLLドライバの使い分け基準と、STM32からROS2ホスト機へのシリアル・micro-ROS通信設計。 |

```{toctree}
:maxdepth: 1
:glob:
:hidden:

*
```
