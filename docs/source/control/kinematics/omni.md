# Omni Wheel Mobile Robot Kinematics

## Omni Wheel Intro

普通の車輪は前後には転がるが、横には滑りにくい. それに比べて、オムニホイールは外周に小さなローラがついており、
車輪の回転方向へ力を出しつつ、ローラ方向への自由な横滑りが可能になっている.

## 何故全方向移動ができるのか

例えば３輪オムニを120degずつ配置すると、各車輪が違う方向の力を出すことができ、それらを合成すると平面内で平行移動と旋回を同時に実現することができる.

平面上のロボットの運動は通常

- v_x <-- 前後速度
- v_y <-- 左右速度
- w_z <-- 旋回速度

の3つのパラメータで表される. よって状態は

$$
\vec{v} = \begin{pmatrix} v_x \\ v_y \\ w_z \end{pmatrix}
$$

の3自由度.

3輪オムニの場合、

$$
\begin{pmatrix} W1 \\ W2 \\ W3 \end{pmatrix}
= A
\begin{pmatrix} v_x \\ v_y \\ w_z \end{pmatrix}
$$






