#!/system/bin/sh
# pipa performance profile (runtime): aggressive but safe.
# NOTE: thermal mitigation is deliberately left untouched - it protects the SoC.
# Every write is guarded, so this is a no-op for knobs a given kernel lacks.

sleep 25   # let the system settle after boot

w() { [ -e "$1" ] && echo "$2" > "$1" 2>/dev/null; }

# --- CPU: schedutil (WALT-friendly) + keep a floor so wake-ups don't crawl
for pol in /sys/devices/system/cpu/cpufreq/policy*; do
    w "$pol/scaling_governor" schedutil
done
# raise the min frequency floor a little on the big cluster (cuts microstutter)
BIG=/sys/devices/system/cpu/cpufreq/policy4
if [ -r "$BIG/cpuinfo_min_freq" ] && [ -r "$BIG/cpuinfo_max_freq" ]; then
    MIN=$(cat "$BIG/cpuinfo_min_freq"); MAX=$(cat "$BIG/cpuinfo_max_freq")
    FLOOR=$((MIN + (MAX - MIN) / 4))
    w "$BIG/scaling_min_freq" "$FLOOR"
fi

# --- Qualcomm input boost: long, aggressive boost on touch
w /sys/module/cpu_boost/parameters/input_boost_enabled 1
w /sys/module/cpu_boost/parameters/sched_boost_on_input 1
w /sys/module/cpu_boost/parameters/input_boost_ms 1500
w /sys/module/msm_performance/parameters/touchboost 1

# --- scheduler tunables (WALT): migrate up eagerly, down lazily
w /proc/sys/kernel/sched_upmigrate 95
w /proc/sys/kernel/sched_downmigrate 85
w /proc/sys/kernel/sched_group_upmigrate 95
w /proc/sys/kernel/sched_group_downmigrate 85
w /dev/stune/top-app/schedtune.boost 10

# --- I/O: low-latency multiqueue scheduler for UFS + sane readahead
for q in /sys/block/sd*/queue /sys/block/mmcblk*/queue; do
    w "$q/scheduler" kyber
    w "$q/read_ahead_kb" 1024
    w "$q/iostats" 0
    w "$q/rq_affinity" 2
    w "$q/nr_requests" 512
done

# --- GPU: sustained, latency-friendly governor
w /sys/class/kgsl/kgsl-3d0/devfreq/governor msm-adreno-tz
w /sys/class/kgsl/kgsl-3d0/default_pwrlevel 1

# --- VM: prefer keeping caches, delay writeback (less stutter under I/O)
w /proc/sys/vm/swappiness 60
w /proc/sys/vm/vfs_cache_pressure 100
w /proc/sys/vm/dirty_background_ratio 5
w /proc/sys/vm/dirty_ratio 15
w /proc/sys/vm/extra_free_kbytes 32768

# --- keep KSM off (it costs CPU and adds latency)
w /sys/kernel/mm/ksm/run 0
