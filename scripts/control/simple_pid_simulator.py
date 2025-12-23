import streamlit as st
import control
import numpy as np
import matplotlib.pyplot as plt

st.title("DC Motor PID Control Analysis")

# --- 1. サイドバー：PIDゲインの設定 ---
st.sidebar.header("PID Parameters")
kp = st.sidebar.slider("Kp (Proportional)", 0.0, 50.0, 20.0)
ki = st.sidebar.slider("Ki (Integral)", 0.0, 100.0, 35.0)
kd = st.sidebar.slider("Kd (Derivative)", 0.0, 10.0, 2.0)

# --- 2. 物理モデルの定義 (DCモーター) ---
# 分母の係数 [J*L, J*R+L*b, b*R+Kt*Ke]
# 典型的な小型モーターの特性をシミュレート
num = [0.1]               # 分子: Kt
den = [0.01, 0.2, 0.22]   # 分母: 2次遅れ系
P = control.TransferFunction(num, den)

# --- 3. コントローラの作成と結合 ---
# PIDコントローラ: C(s) = Kp + Ki/s + Kd*s
C = control.TransferFunction([kd, kp, ki], [1, 0])

# フィードバック結合 (単位フィードバック)
# System = (C*P) / (1 + C*P)
sys_closed = control.feedback(C * P, 1)

# --- 4. シミュレーション実行 ---
t = np.linspace(0, 5, 1000)
t, y = control.step_response(sys_closed, T=t)

# --- 5. グラフの描画 ---
st.subheader("Step Response (Velocity Control)")

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(t, y, label="Motor Speed (Output)", color="blue", linewidth=2)
ax.axhline(1.0, color='red', linestyle='--', label="Target Speed")

# グラフの装飾
ax.set_xlabel("Time [s]")
ax.set_ylabel("Angular Velocity [rad/s]")
ax.set_title(f"Response with Kp={kp}, Ki={ki}, Kd={kd}")
ax.grid(True, which='both', linestyle='--', alpha=0.7)
ax.legend()

# グラフをStreamlitに表示
st.pyplot(fig)

# --- 6. 解析指標の表示 ---
st.divider()
info = control.step_info(sys_closed)
c1, c2, c3 = st.columns(3)
c1.metric("Overshoot", f"{info['Overshoot']:.1f} %")
c2.metric("Rise Time", f"{info['RiseTime']:.3f} s")
c3.metric("Settling Time", f"{info['SettlingTime']:.3f} s")
