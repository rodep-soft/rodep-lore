import streamlit as st
import control
import numpy as np
import matplotlib.pyplot as plt

st.title("🚜 クローラーロボット・2D軌跡シミュレーター")

# --- サイドバー：設定 ---
st.sidebar.header("1. モーター設定 (左右共通)")
kp = st.sidebar.slider("Kp", 0.0, 50.0, 20.0)
ki = st.sidebar.slider("Ki", 0.0, 100.0, 35.0)
kd = st.sidebar.slider("Kd", 0.0, 10.0, 2.0)

st.sidebar.header("2. ロボット形状")
track_width = st.sidebar.slider("トレッド（左右の間隔） [m]", 0.1, 1.0, 0.5)

st.sidebar.header("3. 走行コマンド")
v_target = st.sidebar.slider("目標直進速度 [m/s]", 0.0, 2.0, 1.0)
omega_target = st.sidebar.slider("目標旋回速度 [rad/s]", -2.0, 2.0, 0.5)

# --- 物理モデルの構築 ---
# モーターモデル (前回定義したものを使用)
num = [0.1] # Kt
den = [0.01, 0.2, 0.22] # 簡易化したDCモーター特性
P = control.TransferFunction(num, den)
C = control.TransferFunction([kd, kp, ki], [1, 0])
system = control.feedback(C * P, 1)

# --- シミュレーション実行 ---
dt = 0.05
t = np.arange(0, 10, dt)

# 左右の目標速度を計算 (運動学の逆変換)
# v = (vr + vl)/2,  omega = (vr - vl)/W
v_l_ref = v_target - (track_width * omega_target) / 2
v_r_ref = v_target + (track_width * omega_target) / 2

# モーターの応答を計算
_, y_l = control.forced_response(system, T=t, U=v_l_ref)
_, y_r = control.forced_response(system, T=t, U=v_r_ref)

# --- 2D軌跡の計算 (オドメトリ) ---
x, y, theta = [0.0], [0.0], [0.0]

for i in range(len(t)-1):
    vl = y_l[i]
    vr = y_r[i]
    
    # 現在の速度と旋回速度
    v = (vr + vl) / 2.0
    omega = (vr - vl) / track_width
    
    # 状態更新 (簡易オイラー積分)
    new_theta = theta[-1] + omega * dt
    new_x = x[-1] + v * np.cos(new_theta) * dt
    new_y = y[-1] + v * np.sin(new_theta) * dt
    
    x.append(new_x)
    y.append(new_y)
    theta.append(new_theta)

# --- 可視化 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📍 走行軌跡 (X-Y Plane)")
    fig_map, ax_map = plt.subplots(figsize=(5, 5))
    ax_map.plot(x, y, label="Robot Path")
    ax_map.quiver(x[::20], y[::20], np.cos(theta[::20]), np.sin(theta[::20]), scale=20, color='r')
    ax_map.set_xlabel("X [m]"); ax_map.set_ylabel("Y [m]")
    ax_map.axis("equal")
    ax_map.grid(True)
    st.pyplot(fig_map)

with col2:
    st.subheader("📈 モーター速度応答")
    fig_v, ax_v = plt.subplots()
    ax_v.plot(t, y_l, label="Left Track")
    ax_v.plot(t, y_r, label="Right Track")
    ax_v.set_xlabel("Time [s]"); ax_v.set_ylabel("Velocity [m/s]")
    ax_v.legend(); ax_v.grid(True)
    st.pyplot(fig_v)

st.write("### 💡 解説")
st.write(f"左右のモーターに **Ki={ki}** を設定しているため、定常偏差なく目標速度に追従しています。")
st.write("もし旋回時に大きく外側に膨らむ（アンダーステア）場合は、モーターの立ち上がり時間（Rise Time）を短くするために Kp を調整してください。")
