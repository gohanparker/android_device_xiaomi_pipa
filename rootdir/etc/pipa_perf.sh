#!/system/bin/sh
# pipa performance profile (runtime). Thermal mitigation is deliberately never
# touched - it protects the SoC.
#
# Switch profile live (no reboot needed):
#     setprop persist.pipa.perf.mode balanced
#     setprop persist.pipa.perf.mode aggressive   # default
#     setprop persist.pipa.perf.mode max
# Check what is active:
#     getprop persist.pipa.perf.mode ; logcat -d -s pipa_perf

MODE="$(getprop persist.pipa.perf.mode)"
[ -z "$MODE" ] && MODE=aggressive
log -t pipa_perf "applying profile: $MODE"

# guarded write helper
w() { [ -e "$1" ] && echo "$2" > "$1" 2>/dev/null; }

# ---------------------------------------------------------------- common bits
for q in /sys/block/sd*/queue /sys/block/mmcblk*/queue; do
    w "$q/read_ahead_kb" 1024
    w "$q/iostats" 0
    w "$q/rq_affinity" 2
    w "$q/nr_requests" 512
done
w /sys/kernel/mm/ksm/run 0
w /proc/sys/vm/swappiness 60
w /proc/sys/vm/vfs_cache_pressure 100
w /proc/sys/vm/dirty_background_ratio 5
w /proc/sys/vm/dirty_ratio 15
w /proc/sys/vm/extra_free_kbytes 32768

# raise a cluster's min frequency to a fraction of its max (scaling_min_freq)
floor_pct() { # $1 policy, $2 percent
    p="$1"; pct="$2"
    [ -r "$p/cpuinfo_min_freq" ] || return 0
    min=$(cat "$p/cpuinfo_min_freq"); max=$(cat "$p/cpuinfo_max_freq")
    tgt=$((min + (max - min) * pct / 100))
    w "$p/scaling_min_freq" "$tgt"
}

case "$MODE" in
  balanced)
    for pol in /sys/devices/system/cpu/cpufreq/policy*; do
        w "$pol/scaling_governor" schedutil
        w "$pol/scaling_min_freq" "$(cat "$pol/cpuinfo_min_freq" 2>/dev/null)"
    done
    w /sys/module/cpu_boost/parameters/input_boost_ms 800
    w /sys/class/kgsl/kgsl-3d0/devfreq/governor msm-adreno-tz
    ;;

  max)
    # pin high clocks: performance governor + most of the cluster range
    for pol in /sys/devices/system/cpu/cpufreq/policy*; do
        w "$pol/scaling_governor" performance
        floor_pct "$pol" 75
    done
    w /sys/module/cpu_boost/parameters/input_boost_enabled 1
    w /sys/module/cpu_boost/parameters/sched_boost_on_input 1
    w /sys/module/cpu_boost/parameters/input_boost_ms 2500
    w /sys/module/msm_performance/parameters/touchboost 1
    w /proc/sys/kernel/sched_upmigrate 99
    w /proc/sys/kernel/sched_downmigrate 95
    w /proc/sys/kernel/sched_group_upmigrate 99
    w /proc/sys/kernel/sched_group_downmigrate 95
    w /dev/stune/top-app/schedtune.boost 20
    for q in /sys/block/sd*/queue /sys/block/mmcblk*/queue; do
        w "$q/scheduler" kyber
    done
    w /sys/class/kgsl/kgsl-3d0/devfreq/governor performance
    w /sys/class/kgsl/kgsl-3d0/default_pwrlevel 0
    w /sys/class/kgsl/kgsl-3d0/max_pwrlevel 0
    ;;

  *)  # aggressive (default)
    for pol in /sys/devices/system/cpu/cpufreq/policy*; do
        w "$pol/scaling_governor" schedutil
    done
    floor_pct /sys/devices/system/cpu/cpufreq/policy4 25   # big cluster floor
    w /sys/module/cpu_boost/parameters/input_boost_enabled 1
    w /sys/module/cpu_boost/parameters/sched_boost_on_input 1
    w /sys/module/cpu_boost/parameters/input_boost_ms 1500
    w /sys/module/msm_performance/parameters/touchboost 1
    w /proc/sys/kernel/sched_upmigrate 95
    w /proc/sys/kernel/sched_downmigrate 85
    w /proc/sys/kernel/sched_group_upmigrate 95
    w /proc/sys/kernel/sched_group_downmigrate 85
    w /dev/stune/top-app/schedtune.boost 10
    for q in /sys/block/sd*/queue /sys/block/mmcblk*/queue; do
        w "$q/scheduler" kyber
    done
    w /sys/class/kgsl/kgsl-3d0/devfreq/governor msm-adreno-tz
    w /sys/class/kgsl/kgsl-3d0/default_pwrlevel 1
    ;;
esac

# light settle delay was handled by the init trigger; nothing else to do
log -t pipa_perf "profile $MODE applied"
