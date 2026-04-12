<h1 align="center">

<b>rockchip-stats</b>

</h1>

**rockchip-stats** is a package for **monitoring** and **control** of Rockchip SoC devices [RK3588, RK3588S, RK3576, RK3568, RK3566, RK3399] series.

rockchip-stats is a powerful tool to analyze your board, you can use it as a stand alone application with `rtop` or import it in your python script. The main features are:

- Decode hardware, SoC model, board identification
- Monitor CPU, GPU (Mali), NPU, RGA, MPP, Memory, Temperature, Fan
- Control fan speed, CPU governor
- Importable in a python script
- Dockerizable in a container
- Auto-detects available hardware (graceful degradation)
- Works with multiple Rockchip SoC variants

## Supported Hardware

| SoC | CPU | GPU | NPU | Status |
|-----|-----|-----|-----|--------|
| RK3588 / RK3588S | 4x A76 + 4x A55 | Mali-G610 | 6 TOPS (3 cores) | ✅ Primary |
| RK3576 | 4x A72 + 4x A53 | Mali-G52 | 6 TOPS | ✅ Supported |
| RK3588M | 4x A76 + 4x A55 | Mali-G610 | 6 TOPS (3 cores) | ✅ Supported |
| RK3582 | 2x A76 + 4x A55 | Mali-G610 | - | ✅ Supported |
| RK3568 / RK3568J | 4x A55 | Mali-G52 | - | ✅ Supported |
| RK3566 | 4x A55 | Mali-G52 | - | ✅ Supported |
| RK3399 / RK3399Pro | 2x A72 + 4x A53 | Mali-T860 | 3 TOPS (Pro only) | ✅ Supported |

## Monitoring Sources

| Component | Source Path | Notes |
|-----------|-------------|-------|
| CPU Load | `/proc/stat` | Per-core and total |
| CPU Freq | `/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq` | Per-core |
| GPU Load | `/sys/class/devfreq/fb000000.gpu/load` | Format: `load@freq` |
| GPU Freq | `/sys/class/devfreq/fb000000.gpu/cur_freq` | |
| NPU Load | `/sys/kernel/debug/rknpu/load` | Per-core, requires root |
| NPU Freq | `/sys/class/devfreq/fdab0000.npu/cur_freq` | |
| RGA Load | `/sys/kernel/debug/rkrga/load` | Requires root |
| RGA Freq | `/sys/kernel/debug/clk/clk_summary` | Requires root |
| MPP Sessions | `/proc/mpp_service/sessions-summary` | Video enc/dec cores |
| Temperature | `/sys/class/thermal/thermal_zone*/temp` | Multiple zones |
| Fan | `/sys/class/thermal/cooling_device*/cur_state` | + PWM hwmon |
| Device ID | `/sys/firmware/devicetree/base/compatible` | SoC identification |

## Install

```console
sudo apt update
sudo apt install python3-pip python3-setuptools -y
```

### Option 1: Install with pip (requires superuser)
```console
sudo pip3 install -U rockchip-stats
```

### Option 2: Install from source
```console
git clone https://github.com/your-repo/rockchip_stats.git
cd rockchip_stats
sudo pip3 install .
```

### Option 3: Ubuntu 24.04+
```console
sudo pip3 install --break-system-packages -U rockchip-stats
```

---

## Run

Start rtop by simply typing `rtop`:

```console
rtop
```

An interactive curses-based interface will appear with 8 pages:

| Key | Page | Description |
|-----|------|-------------|
| `1` | ALL | Overview dashboard |
| `2` | CPU | Per-core CPU details |
| `3` | GPU | Mali GPU details |
| `4` | NPU | NPU per-core details |
| `5` | ENG | RGA, MPP engines |
| `6` | MEM | RAM, Swap, CMA |
| `7` | CTRL | Fan & governor control |
| `8` | INFO | Board & system info |

## Library

You can use rtop as a Python library to integrate into your software:

```python
from rtop import rtop

with rtop() as rockchip:
    while rockchip.ok():
        # Read stats
        print(rockchip.stats)
```

### Quick Read Example

```python
from rtop import rtop

with rtop() as rockchip:
    if rockchip.ok():
        # CPU
        cpu = rockchip.cpu
        print(f"CPU: {cpu.get('total', 0):.1f}%")

        # GPU
        gpu = rockchip.gpu
        if gpu:
            print(f"GPU: {gpu.get('load', 0)}%")

        # NPU
        npu = rockchip.npu
        if npu:
            for i, core in enumerate(npu.get('cores', [])):
                print(f"NPU Core{i}: {core.get('load', 0)}%")

        # Temperature
        for name, val in rockchip.temperature.items():
            if isinstance(val, (int, float)):
                print(f"{name}: {val / 1000:.1f}°C")
```

## Docker

You can run rtop directly in Docker:

1. Install rockchip-stats on your **host**
2. Install rockchip-stats in your container
3. Pass `/run/rtop.sock:/run/rtop.sock` to your container

```console
docker run --rm -it -v /run/rtop.sock:/run/rtop.sock rockchip-stats:latest
```

## Architecture

rockchip-stats uses a client-server model:

```
┌─────────────────┐     Unix Socket      ┌─────────────────┐
│   rtop (client)  │◄──────────────────►│  rtop (service)  │
│   curses GUI     │    /run/rtop.sock   │  data collector  │
└─────────────────┘                      └─────────────────┘
                                                  │
                                          ┌───────┴───────┐
                                          │  sysfs/procfs  │
                                          │  debugfs       │
                                          └───────────────┘
```

The background service (`rtop.service`) runs as root to access debugfs paths (NPU load, RGA load) and serves data via a Unix domain socket. The client connects and displays the data.

## Documentation

More documentation available at the project repository.

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

Inspired by jetson_stats by rbonghi
https://github.com/rbonghi/jetson_stats
