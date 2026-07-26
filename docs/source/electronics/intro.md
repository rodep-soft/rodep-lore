# Electronics

STM32を中心にした組み込み・回路設計の知見。CAN、I2C、IMUノイズ対策、ハードウェアデバッグの泥臭い話を書いている。

| 記事 | 概要 |
|---|---|
| [CAN バス設計](can_bus_design.md) | CAN FD対応マイコンの設定、終端抵抗・フィルタリング・ノイズ対策。ロボットの基幹通信として使う際の実装ポイント。 |
| [ハードウェアデバッグ](hardware_troubleshooting.md) | STM32のI2CやIMUのノイズ問題を中心に、SWO/SWD、ロジックアナライザ、オシロスコープを使った実践的なデバッグ手法。 |
| [STM32 内部アーキテクチャ](stm32_internals.md) | HALとLLドライバの選択基準、DMA・割り込み・タイマの正しい使い方。パフォーマンスを引き出すための内部理解。 |

```{toctree}
:maxdepth: 1
:glob:
:hidden:

*
```
