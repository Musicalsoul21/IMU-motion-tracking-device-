# analyze_validation.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

# ── CONFIG ─────────────────────────────────────
SERVO1_FILE = 'servo1_log.csv'
SERVO2_FILE = 'servo2_log.csv'
IMU1_FILE   = 'S1001.CSV'     # from STM32 #1 SD card
IMU2_FILE   = 'S2001.CSV'     # from STM32 #2 SD card
FULL_RANGE  = 180.0
LIMIT_PCT   = 2.5
LIMIT_DEG   = FULL_RANGE * (LIMIT_PCT / 100)  # = 4.5°
# ──────────────────────────────────────────────

def find_best_axis_and_offset(servo_df, imu_df):
    """
    Cross-correlate servo steps with each IMU axis.
    Returns (best_axis_name, time_offset_seconds, 
             is_inverted)
    """
    servo_t = servo_df['arduino_time_ms'].values / 1000.0
    servo_a = servo_df['commanded_deg'].values.astype(float)
    imu_t   = imu_df['time_ms'].values / 1000.0

    best_corr   = -999
    best_axis   = 'euler_x_deg'
    best_offset = 0.0

    for axis in ['euler_x_deg', 'euler_y_deg', 'euler_z_deg']:
        imu_a = imu_df[axis].values.copy()

        # Normalize both to 0-1
        s_norm = (servo_a - servo_a.min()) / \
                 (servo_a.max() - servo_a.min() + 1e-6)
        i_norm = (imu_a   - imu_a.min()) / \
                 (imu_a.max()   - imu_a.min()   + 1e-6)

        # Common time at 2Hz (servo rate)
        common_t = np.arange(
            0, 
            min(servo_t.max(), imu_t.max()), 
            0.5
        )
        if len(common_t) < 5:
            continue

        try:
            s_fn = interp1d(servo_t, s_norm,
                            bounds_error=False, 
                            fill_value='extrapolate')
            i_fn = interp1d(imu_t, i_norm,
                            bounds_error=False,
                            fill_value='extrapolate')

            s_res = s_fn(common_t)
            i_res = i_fn(common_t)

            corr = np.correlate(
                s_res - s_res.mean(),
                i_res - i_res.mean(),
                mode='full'
            )
            lags = np.arange(
                -(len(common_t)-1), 
                len(common_t)
            ) * 0.5

            idx    = np.argmax(np.abs(corr))
            lag    = lags[idx]
            peak   = corr[idx]

            print(f"    {axis}: corr={peak:.1f}  "
                  f"lag={lag:.2f}s")

            if abs(peak) > abs(best_corr):
                best_corr   = peak
                best_axis   = axis
                best_offset = lag

        except Exception as e:
            print(f"    {axis}: skipped ({e})")

    inverted = best_corr < 0
    return best_axis, best_offset, inverted


def compute_rmse(servo_df, imu_df, axis, 
                 offset, inverted):
    """
    Align IMU to servo timestamps and compute errors.
    Returns merged dataframe with error columns.
    """
    imu_t = imu_df['time_ms'].values / 1000.0
    imu_a = imu_df[axis].values.copy()
    if inverted:
        imu_a = -imu_a

    servo_t_adj = servo_df['arduino_time_ms'].values \
                  / 1000.0 + offset

    imu_fn = interp1d(imu_t, imu_a,
                      bounds_error=False,
                      fill_value=np.nan)
    imu_at_steps = imu_fn(servo_t_adj)

    # Remove offset at 0°
    zero_mask  = servo_df['commanded_deg'].values == 0
    imu_offset = np.nanmean(imu_at_steps[zero_mask])
    imu_corrected = imu_at_steps - imu_offset

    result = servo_df.copy()
    result['imu_raw']       = imu_at_steps
    result['imu_corrected'] = imu_corrected
    result['error_deg']     = (result['commanded_deg']
                                .astype(float) 
                                - imu_corrected)
    result['abs_error']     = result['error_deg'].abs()
    result['error_pct']     = (result['abs_error'] 
                                / FULL_RANGE * 100)
    result['imu_offset_removed'] = imu_offset

    return result


def print_results(name, df):
    valid   = df.dropna(subset=['error_deg'])
    err     = valid['error_deg'].values
    rmse    = np.sqrt(np.mean(err**2))
    rmse_p  = rmse / FULL_RANGE * 100
    passed  = rmse_p < LIMIT_PCT

    fwd = valid[valid['direction'] == 'FWD']['error_deg']
    bwd = valid[valid['direction'] == 'BWD']['error_deg']
    rmse_fwd = np.sqrt(np.mean(fwd**2)) if len(fwd) > 0 else 0
    rmse_bwd = np.sqrt(np.mean(bwd**2)) if len(bwd) > 0 else 0

    print(f"\n{'='*52}")
    print(f"  {name} RESULTS")
    print(f"{'='*52}")
    print(f"  RMSE (overall):    {rmse:.4f}° ({rmse_p:.4f}%)")
    print(f"  RMSE (forward):    {rmse_fwd:.4f}°")
    print(f"  RMSE (backward):   {rmse_bwd:.4f}°")
    print(f"  Hysteresis:        {abs(rmse_fwd-rmse_bwd):.4f}°")
    print(f"  Max error:         {valid['abs_error'].max():.4f}°")
    print(f"  Mean bias:         {err.mean():.4f}°")
    print(f"  Std deviation:     {err.std():.4f}°")
    print(f"  IMU offset removed:{valid['imu_offset_removed'].iloc[0]:.4f}°")
    print(f"  Limit:             ±{LIMIT_DEG:.2f}° ({LIMIT_PCT}%)")
    print(f"  RESULT:            {'✅ PASS' if passed else '❌ FAIL'}")
    print(f"{'='*52}")

    return {
        'rmse': rmse, 'rmse_pct': rmse_p,
        'rmse_fwd': rmse_fwd, 'rmse_bwd': rmse_bwd,
        'passed': passed, 'valid': valid
    }


# ─────────────────────────────────────────────
# LOAD ALL FILES
# ─────────────────────────────────────────────
print("Loading files...")
servo1 = pd.read_csv(SERVO1_FILE)
servo2 = pd.read_csv(SERVO2_FILE)
imu1   = pd.read_csv(IMU1_FILE)
imu2   = pd.read_csv(IMU2_FILE)

print(f"  Servo1 steps: {len(servo1)}")
print(f"  Servo2 steps: {len(servo2)}")
print(f"  IMU1 samples: {len(imu1)}")
print(f"  IMU2 samples: {len(imu2)}")

# ─────────────────────────────────────────────
# FIND AXIS + OFFSET FOR EACH PAIR
# ─────────────────────────────────────────────
print("\n--- Servo 1 + IMU 1 axis detection ---")
axis1, offset1, inv1 = find_best_axis_and_offset(
    servo1, imu1)
print(f"  → axis={axis1}  offset={offset1:.2f}s  "
      f"inverted={inv1}")

print("\n--- Servo 2 + IMU 2 axis detection ---")
axis2, offset2, inv2 = find_best_axis_and_offset(
    servo2, imu2)
print(f"  → axis={axis2}  offset={offset2:.2f}s  "
      f"inverted={inv2}")

# ─────────────────────────────────────────────
# COMPUTE ERRORS
# ─────────────────────────────────────────────
df1 = compute_rmse(servo1, imu1, axis1, offset1, inv1)
df2 = compute_rmse(servo2, imu2, axis2, offset2, inv2)

# ─────────────────────────────────────────────
# PRINT RESULTS
# ─────────────────────────────────────────────
r1 = print_results("SERVO 1 (Pin 9)  + IMU 1 (S1)", df1)
r2 = print_results("SERVO 2 (Pin 10) + IMU 2 (S2)", df2)

# ─────────────────────────────────────────────
# PLOTS — Side by Side
# ─────────────────────────────────────────────
fig, axes = plt.subplots(3, 2, figsize=(18, 14))
fig.suptitle('Two-Servo IMU Validation Report', 
             fontsize=14, fontweight='bold')

# ── Column labels ─────────────────────────────
axes[0][0].set_title(f'SERVO 1 (Pin 9) — IMU 1\n'
                     f'RMSE={r1["rmse"]:.4f}°  '
                     f'{"✅ PASS" if r1["passed"] else "❌ FAIL"}',
                     fontsize=11)
axes[0][1].set_title(f'SERVO 2 (Pin 10) — IMU 2\n'
                     f'RMSE={r2["rmse"]:.4f}°  '
                     f'{"✅ PASS" if r2["passed"] else "❌ FAIL"}',
                     fontsize=11)

for col, df, r in [(0, df1, r1), (1, df2, r2)]:
    valid = r['valid']
    step  = np.arange(len(valid))
    cmd   = valid['commanded_deg'].values.astype(float)
    imu_c = valid['imu_corrected'].values
    err   = valid['error_deg'].values
    fwd   = valid[valid['direction'] == 'FWD']
    bwd   = valid[valid['direction'] == 'BWD']

    # Row 0: Overlay
    axes[0][col].plot(step, cmd,
                      'b-o', ms=3, lw=2,
                      label='Servo (Ground Truth)')
    axes[0][col].plot(step, imu_c,
                      'r--s', ms=3, lw=1.5,
                      label='BNO055 (Measured)')
    axes[0][col].set_ylabel('Angle (°)')
    axes[0][col].legend(fontsize=8)
    axes[0][col].grid(True, alpha=0.4)

    # Row 1: Error over steps
    axes[1][col].plot(step, err, 'g-', lw=1.5)
    axes[1][col].axhline( LIMIT_DEG, color='r',
                           ls='--', lw=1.5,
                           label=f'+{LIMIT_PCT}% limit')
    axes[1][col].axhline(-LIMIT_DEG, color='r',
                           ls='--', lw=1.5,
                           label=f'-{LIMIT_PCT}% limit')
    axes[1][col].axhline(0, color='k', lw=0.5)
    axes[1][col].fill_between(
        step, LIMIT_DEG, -LIMIT_DEG,
        alpha=0.1, color='green', label='Pass zone')
    axes[1][col].set_ylabel('Error (°)')
    axes[1][col].legend(fontsize=8)
    axes[1][col].grid(True, alpha=0.4)

    # Row 2: Hysteresis
    axes[2][col].scatter(
        fwd['commanded_deg'], fwd['error_deg'],
        c='blue', alpha=0.6, s=20,
        label='Forward (0→180°)')
    axes[2][col].scatter(
        bwd['commanded_deg'], bwd['error_deg'],
        c='red',  alpha=0.6, s=20,
        label='Backward (180→0°)')
    axes[2][col].axhline( LIMIT_DEG, color='orange',
                           ls='--', lw=1)
    axes[2][col].axhline(-LIMIT_DEG, color='orange',
                           ls='--', lw=1)
    axes[2][col].axhline(0, color='k', lw=0.5)
    axes[2][col].set_xlabel('Commanded Angle (°)')
    axes[2][col].set_ylabel('Error (°)')
    axes[2][col].legend(fontsize=8)
    axes[2][col].grid(True, alpha=0.4)

plt.tight_layout()
plt.savefig('validation_report_both.png', dpi=150)
plt.show()
print("\nSaved: validation_report_both.png")