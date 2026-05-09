# analyze_validation.py
# Run AFTER copying S1001.CSV from SD card to same folder

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
import sys
import os

# ─────────────────────────────────────────────
# CONFIG — edit these if needed
# ─────────────────────────────────────────────
SERVO_FILE = 'servo_log.csv'
IMU_FILE   = 'S1001.CSV'
FULL_RANGE = 180.0    # degrees (your servo range)
LIMIT_PCT  = 2.5      # pass criteria %

# ─────────────────────────────────────────────
# STEP 1: CHECK FILES EXIST
# ─────────────────────────────────────────────
print("="*52)
print("   BNO055 IMU VALIDATION ANALYSIS")
print("="*52)

for f in [SERVO_FILE, IMU_FILE]:
    if not os.path.exists(f):
        print(f"\n❌ ERROR: File not found: {f}")
        print(f"   Make sure {f} is in the same folder as this script")
        sys.exit(1)
    print(f"✅ Found: {f}")

# ─────────────────────────────────────────────
# STEP 2: LOAD DATA
# ─────────────────────────────────────────────
print("\nLoading data...")

# Load servo log (captured by serial_logger.py)
# Expected columns: pc_time_ms, arduino_time_ms, cycle, direction, commanded_deg
servo = pd.read_csv(SERVO_FILE, comment='#')
servo.columns = servo.columns.str.strip()  # remove accidental spaces

# Load IMU log (from SD card)
# Skip any comment lines starting with #
imu = pd.read_csv(IMU_FILE, comment='#')
imu.columns = imu.columns.str.strip()

print(f"  Servo rows:    {len(servo)}")
print(f"  IMU rows:      {len(imu)}")
print(f"  Servo columns: {list(servo.columns)}")
print(f"  IMU columns:   {list(imu.columns)}")

# ── Validate required columns ──────────────────
required_servo = ['arduino_time_ms', 'cycle', 'direction', 'commanded_deg']
required_imu   = ['time_ms', 'euler_x_deg', 'euler_y_deg', 'euler_z_deg']

for col in required_servo:
    if col not in servo.columns:
        print(f"\n❌ ERROR: servo_log.csv missing column: '{col}'")
        print(f"   Found columns: {list(servo.columns)}")
        sys.exit(1)

for col in required_imu:
    if col not in imu.columns:
        print(f"\n❌ ERROR: S1001.CSV missing column: '{col}'")
        print(f"   Found columns: {list(imu.columns)}")
        sys.exit(1)

print("\n✅ All required columns found")

# ─────────────────────────────────────────────
# STEP 3: BASIC STATS
# ─────────────────────────────────────────────
servo_duration = (servo['arduino_time_ms'].max() - 
                  servo['arduino_time_ms'].min()) / 1000.0
imu_duration   = imu['time_ms'].max() / 1000.0

print(f"\nServo test duration: {servo_duration:.1f} seconds")
print(f"IMU log duration:    {imu_duration:.1f} seconds")
print(f"Servo steps logged:  {len(servo)}")
print(f"IMU samples:         {len(imu)} ({len(imu)/imu_duration:.0f} Hz)")

# ─────────────────────────────────────────────
# STEP 4: PREPARE SIGNALS
# ─────────────────────────────────────────────

# Arduino time in seconds (starts near 0 after HOLDING_AT_ZERO)
servo_t = (servo['arduino_time_ms'].values - 
           servo['arduino_time_ms'].values[0]) / 1000.0
servo_a = servo['commanded_deg'].values.astype(float)

# IMU time in seconds (starts at STM32 power-on)
imu_t   = imu['time_ms'].values / 1000.0

# ─────────────────────────────────────────────
# STEP 5: FIX BNO055 EULER AXIS ISSUE
# ─────────────────────────────────────────────
# BNO055 Euler X = heading = 0 to 360° (wraps!)
# BNO055 Euler Y = pitch   = -180 to +180°  
# BNO055 Euler Z = roll    = -90 to +90°
#
# The servo moves 0→180°. We need the axis that
# changes linearly with servo position.
# Unwrap Euler X from 0-360 to continuous range.

imu_euler_x = imu['euler_x_deg'].values.copy()
imu_euler_y = imu['euler_y_deg'].values.copy()
imu_euler_z = imu['euler_z_deg'].values.copy()

# Unwrap euler_x (heading) — handles 359→1 wraparound
imu_euler_x_unwrapped = np.unwrap(np.deg2rad(imu_euler_x))
imu_euler_x_unwrapped = np.rad2deg(imu_euler_x_unwrapped)

axes_to_try = {
    'euler_x (heading, unwrapped)': imu_euler_x_unwrapped,
    'euler_y (pitch)':              imu_euler_y,
    'euler_z (roll)':               imu_euler_z,
}

# ─────────────────────────────────────────────
# STEP 6: TIME ALIGNMENT via cross-correlation
# ─────────────────────────────────────────────
# The servo (Arduino) and IMU (STM32) have independent clocks.
# We find the time shift between them using cross-correlation.
#
# Key insight: servo_t starts at 0 (after Arduino reset)
#              imu_t starts at 0 (after STM32 power-on)
#              STM32 was powered on BEFORE Arduino
#              So imu_t = servo_t + offset  (offset > 0)

print("\nAligning timestamps via cross-correlation...")
print("(This finds the time difference between the two clocks)\n")

# Use a fine common time grid covering SERVO duration
# (we know where the staircase signal is in servo time)
dt         = 0.1   # 10Hz interpolation grid
common_t   = np.arange(0, servo_duration, dt)

best_corr   = 0
best_axis   = 'euler_z (roll)'
best_offset = 0.0
best_invert = False

for axis_name, axis_data in axes_to_try.items():

    # Interpolate servo signal onto common grid
    s_interp_fn = interp1d(servo_t, servo_a,
                           kind='linear',
                           bounds_error=False, 
                           fill_value=(servo_a[0], servo_a[-1]))
    s_on_grid = s_interp_fn(common_t)

    # Try all possible time offsets for IMU
    # Offset = how many seconds STM32 was on before Arduino started
    # Search from 0 to imu_duration - servo_duration seconds
    max_offset = max(0, imu_duration - servo_duration)
    offsets    = np.arange(0, max_offset + dt, dt)

    if len(offsets) == 0:
        offsets = np.array([0.0])

    best_local_corr   = 0
    best_local_offset = 0.0

    for offset in offsets:
        # At this offset, IMU time that aligns with servo_t=0
        # is imu_t = servo_t + offset
        imu_t_shifted = common_t + offset

        i_interp_fn = interp1d(imu_t, axis_data,
                               kind='linear',
                               bounds_error=False,
                               fill_value=np.nan)
        i_on_grid = i_interp_fn(imu_t_shifted)

        # Skip if too many NaNs
        valid = ~np.isnan(i_on_grid)
        if valid.sum() < len(common_t) * 0.5:
            continue

        # Normalize both to zero mean, unit variance
        s_v = s_on_grid[valid]
        i_v = i_on_grid[valid]

        s_norm = (s_v - s_v.mean()) / (s_v.std() + 1e-9)
        i_norm = (i_v - i_v.mean()) / (i_v.std() + 1e-9)

        # Pearson correlation at this offset
        corr = np.dot(s_norm, i_norm) / len(s_norm)

        if abs(corr) > abs(best_local_corr):
            best_local_corr   = corr
            best_local_offset = offset

    print(f"  {axis_name}:")
    print(f"    peak correlation = {best_local_corr:.4f}")
    print(f"    best offset      = {best_local_offset:.2f} s")

    if abs(best_local_corr) > abs(best_corr):
        best_corr   = best_local_corr
        best_axis   = axis_name
        best_offset = best_local_offset
        best_invert = (best_local_corr < 0)

print(f"\n✅ Best axis:   {best_axis}")
print(f"   Time offset: {best_offset:.2f} s "
      f"(STM32 was on {best_offset:.1f}s before Arduino)")
print(f"   Correlation: {best_corr:.4f}")
print(f"   IMU mounted inverted: {best_invert}")

if abs(best_corr) < 0.7:
    print("\n⚠️  WARNING: Low correlation! Possible causes:")
    print("   - IMU axis not aligned with servo rotation")
    print("   - IMU was moving before servo started")
    print("   - BNO055 not calibrated")
    print("   Check your physical mounting!")

# ─────────────────────────────────────────────
# STEP 7: EXTRACT IMU ANGLE AT EACH SERVO STEP
# ─────────────────────────────────────────────

# Get the best axis data
best_axis_data = axes_to_try[best_axis].copy()
if best_invert:
    best_axis_data = -best_axis_data

# For each servo step timestamp, find corresponding IMU time
# servo_t is in Arduino time → STM32 time = servo_t + best_offset
servo_t_in_imu_clock = servo_t + best_offset

imu_interp_fn = interp1d(imu_t, best_axis_data,
                          kind='linear',
                          bounds_error=False,
                          fill_value=np.nan)

imu_at_steps = imu_interp_fn(servo_t_in_imu_clock)

# ─────────────────────────────────────────────
# STEP 8: OFFSET CORRECTION
# ─────────────────────────────────────────────
# At commanded 0°, IMU may not read exactly 0
# Remove this constant offset

zero_mask = servo['commanded_deg'].values == 0
if zero_mask.sum() == 0:
    print("\n⚠️  No 0° steps found — skipping offset correction")
    imu_offset = 0.0
else:
    imu_offset = np.nanmean(imu_at_steps[zero_mask])

imu_corrected = imu_at_steps - imu_offset
print(f"\nIMU reading at 0° (before correction): {imu_offset:.4f}°")
print(f"Offset removed: {imu_offset:.4f}°")

# ─────────────────────────────────────────────
# STEP 9: ERROR METRICS
# ─────────────────────────────────────────────
commanded = servo['commanded_deg'].values.astype(float)
error     = commanded - imu_corrected

# Remove NaN (happens at edges where IMU time doesn't overlap)
valid      = ~np.isnan(error)
error_v    = error[valid]
cmd_v      = commanded[valid]
dir_v      = servo['direction'].values[valid]
imu_v      = imu_corrected[valid]

if len(error_v) == 0:
    print("\n❌ ERROR: No valid overlapping data found!")
    print("   Time alignment may have failed.")
    print(f"   Servo time range: {servo_t[0]:.1f} to {servo_t[-1]:.1f} s")
    print(f"   IMU time range:   {imu_t[0]:.1f} to {imu_t[-1]:.1f} s")
    sys.exit(1)

rmse_deg   = np.sqrt(np.mean(error_v**2))
rmse_pct   = (rmse_deg / FULL_RANGE) * 100
max_err    = np.max(np.abs(error_v))
mean_bias  = np.mean(error_v)
std_err    = np.std(error_v)

fwd_mask   = dir_v == 'FWD'
bwd_mask   = dir_v == 'BWD'
rmse_fwd   = np.sqrt(np.mean(error_v[fwd_mask]**2)) if fwd_mask.any() else 0
rmse_bwd   = np.sqrt(np.mean(error_v[bwd_mask]**2)) if bwd_mask.any() else 0
hysteresis = abs(rmse_fwd - rmse_bwd)

LIMIT_DEG  = FULL_RANGE * (LIMIT_PCT / 100)
passed     = rmse_pct < LIMIT_PCT

# Per-cycle RMSE
cycle_rmse = {}
for c in servo['cycle'].unique():
    mask = servo['cycle'].values[valid] == c
    if mask.sum() > 0:
        cycle_rmse[c] = np.sqrt(np.mean(error_v[mask]**2))

# ─────────────────────────────────────────────
# STEP 10: PRINT REPORT
# ─────────────────────────────────────────────
print("\n" + "="*52)
print("        BNO055 VALIDATION REPORT")
print("="*52)
print(f"  Best IMU axis:       {best_axis}")
print(f"  Time offset:         {best_offset:.2f} s")
print(f"  Correlation:         {best_corr:.4f}")
print(f"  IMU offset removed:  {imu_offset:.4f}°")
print(f"  Valid samples:       {valid.sum()} / {len(error)}")
print("-"*52)
print(f"  RMSE (overall):      {rmse_deg:.4f}°  ({rmse_pct:.4f}%)")
print(f"  RMSE (forward):      {rmse_fwd:.4f}°")
print(f"  RMSE (backward):     {rmse_bwd:.4f}°")
print(f"  Hysteresis:          {hysteresis:.4f}°")
print(f"  Max single error:    {max_err:.4f}°")
print(f"  Mean bias:           {mean_bias:.4f}°  (systematic offset)")
print(f"  Std deviation:       {std_err:.4f}°  (random noise)")
print("-"*52)
print(f"  Pass threshold:      {LIMIT_DEG:.2f}° ({LIMIT_PCT}%)")
print(f"  RESULT:              {'✅ PASS' if passed else '❌ FAIL'}")
print("="*52)

print(f"\nPer-cycle RMSE:")
for c, r in cycle_rmse.items():
    status = '✅' if (r/FULL_RANGE*100) < LIMIT_PCT else '❌'
    print(f"  Cycle {c}: {r:.4f}°  {status}")

calib_cols = ['calib_sys','calib_gyro','calib_accel','calib_mag']
print(f"\nCalibration quality (average during test):")
for col in calib_cols:
    if col in imu.columns:
        avg = imu[col].mean()
        bar = '█' * int(avg * 3 / 3 * 10)
        print(f"  {col:15s}: {avg:.2f}/3  {bar}")

# ─────────────────────────────────────────────
# STEP 11: PLOTS
# ─────────────────────────────────────────────
fig, axes_plt = plt.subplots(4, 1, figsize=(14, 16))
fig.suptitle(f'BNO055 IMU Validation  |  '
             f'RMSE={rmse_deg:.4f}°  |  '
             f'{"✅ PASS" if passed else "❌ FAIL"}',
             fontsize=13, fontweight='bold')

step_idx = np.arange(len(cmd_v))

# ── Plot 1: Overlay ───────────────────────────
axes_plt[0].plot(step_idx, cmd_v,
                 'b-o', ms=3, lw=2, label='Servo (Ground Truth)')
axes_plt[0].plot(step_idx, imu_v,
                 'r--s', ms=3, lw=1.5,
                 label=f'BNO055 ({best_axis})')
axes_plt[0].set_ylabel('Angle (°)')
axes_plt[0].set_title('Ground Truth vs BNO055 Measurement')
axes_plt[0].legend()
axes_plt[0].grid(True, alpha=0.4)
axes_plt[0].set_ylim(-10, 195)

# ── Plot 2: Error over steps ──────────────────
axes_plt[1].plot(step_idx, error_v, 'g-', lw=1.5, label='Error')
axes_plt[1].fill_between(step_idx,  LIMIT_DEG, -LIMIT_DEG,
                          alpha=0.15, color='green', label='Pass zone')
axes_plt[1].axhline( LIMIT_DEG, color='r', ls='--', lw=1.5,
                     label=f'+{LIMIT_PCT}% = +{LIMIT_DEG:.1f}°')
axes_plt[1].axhline(-LIMIT_DEG, color='r', ls='--', lw=1.5,
                     label=f'-{LIMIT_PCT}% = -{LIMIT_DEG:.1f}°')
axes_plt[1].axhline(0, color='k', lw=0.8)
axes_plt[1].axhline(mean_bias, color='purple', ls=':', lw=1.5,
                     label=f'Mean bias={mean_bias:.3f}°')
axes_plt[1].set_ylabel('Error (°)')
axes_plt[1].set_title(f'Error per Step  |  '
                       f'RMSE={rmse_deg:.4f}°  ({rmse_pct:.2f}%)')
axes_plt[1].legend(fontsize=8)
axes_plt[1].grid(True, alpha=0.4)

# ── Plot 3: Hysteresis ────────────────────────
axes_plt[2].scatter(cmd_v[fwd_mask], error_v[fwd_mask],
                    c='blue', alpha=0.6, s=25,
                    label=f'Forward  RMSE={rmse_fwd:.3f}°')
axes_plt[2].scatter(cmd_v[bwd_mask], error_v[bwd_mask],
                    c='red', alpha=0.6, s=25,
                    label=f'Backward RMSE={rmse_bwd:.3f}°')
axes_plt[2].axhline(0, color='k', lw=0.8)
axes_plt[2].axhline( LIMIT_DEG, color='orange', ls='--', lw=1,
                     label=f'±{LIMIT_PCT}% limit')
axes_plt[2].axhline(-LIMIT_DEG, color='orange', ls='--', lw=1)
axes_plt[2].set_xlabel('Commanded Angle (°)')
axes_plt[2].set_ylabel('Error (°)')
axes_plt[2].set_title(f'Hysteresis: Forward vs Backward  '
                       f'|  Δ={hysteresis:.4f}°')
axes_plt[2].legend()
axes_plt[2].grid(True, alpha=0.4)

# ── Plot 4: Full IMU raw log ──────────────────
axes_plt[3].plot(imu['time_ms']/1000,
                 axes_to_try[best_axis],
                 color='gray', lw=0.8, alpha=0.8,
                 label=f'IMU raw ({best_axis}) @100Hz')
# Mark where test overlapped
test_start_imu = best_offset
test_end_imu   = best_offset + servo_duration
axes_plt[3].axvspan(test_start_imu, test_end_imu,
                     alpha=0.15, color='blue',
                     label='Test window')
axes_plt[3].set_xlabel('STM32 Time (s)')
axes_plt[3].set_ylabel('Angle (°)')
axes_plt[3].set_title('Full IMU Log — Blue = Test Window')
axes_plt[3].legend()
axes_plt[3].grid(True, alpha=0.4)

plt.tight_layout()
plt.savefig('validation_report.png', dpi=150, bbox_inches='tight')
plt.show()
print("\n✅ Saved: validation_report.png")