<h1 align="center">rockchip-stats</h1>

<p align="center">
  System monitor and control tool for Rockchip SoC devices
</p>

<p align="center">
  <img width="1920" alt="rockchip-stats screenshot" src="https://github.com/user-attachments/assets/8d5e6163-13a2-4344-bd01-473009f2fbcb" />
</p>

---

**rockchip-stats** is a monitoring and control package for Rockchip SoC boards. It can be used as a standalone terminal UI (`rtop`) or imported as a Python library.

**Features:**
- Real-time monitoring of CPU, GPU, NPU, RGA, MPP, Memory, Temperature, Fan
- Fan speed and CPU governor control
- Board and SoC auto-detection
- Importable Python library
- Docker-compatible via Unix socket
- Graceful degradation — works even when some hardware is absent

---

## Supported Hardware

| SoC | CPU | GPU | NPU |
|-----|-----|-----|-----|
| RK3588 / RK3588S / RK3588M | 4× A76 + 4× A55 | Mali-G610 | 6 TOPS (3 cores) |
| RK3582 | 2× A76 + 4× A55 | Mali-G610 | — |
| RK3576 | 4× A72 + 4× A53 | Mali-G52 | 6 TOPS |
| RK3568 / RK3568J | 4× A55 | Mali-G52 | — |
| RK3566 | 4× A55 | Mali-G52 | — |
| RK3399 / RK3399Pro | 2× A72 + 4× A53 | Mali-T860 | 3 TOPS (Pro only) |

---

## Install

```bash
sudo apt update && sudo apt install python3-pip -y
sudo pip3 install -U rockchip-stats          # standard
sudo pip3 install --break-system-packages -U rockchip-stats  # Ubuntu 24.04+
```

**From source:**
```bash
git clone https://github.com/batuhanberkayaydin/rockchip_stats.git
cd rockchip_stats
sudo pip3 install .
```

After install, reboot once so your user is added to the `rtop` group.

---

## Usage

```bash
rtop
```

| Key | Page | Description |
|-----|------|-------------|
| `1` | ALL  | Overview dashboard |
| `2` | CPU  | Per-core load & frequency |
| `3` | GPU  | Mali GPU load & frequency |
| `4` | NPU  | NPU per-core utilization |
| `5` | ENG  | RGA & MPP hardware engines |
| `6` | MEM  | RAM, Swap, CMA |
| `7` | CTRL | Temperature, Fan, Power |
| `8` | INFO | Board & system information |

---

## Python Library

```python
from rtop import rtop

with rtop() as r:
    while r.ok():
        cpu = r.cpu
        gpu = r.gpu
        print(f"CPU: {cpu.get('total', 0):.1f}%  GPU: {gpu.get('load', 0)}%")
```

**Read all sensors once:**
```python
from rtop import rtop

with rtop() as r:
    if r.ok():
        for name, val in r.temperature.items():
            if isinstance(val, (int, float)):
                print(f"{name}: {val / 1000:.1f}°C")

        for i, core in enumerate(r.npu.get('cores', [])):
            print(f"NPU Core{i}: {core.get('load', 0)}%")
```

More examples in [`examples/`](https://github.com/batuhanberkayaydin/rockchip_stats/tree/master/examples).

---

## Docker

Install rockchip-stats on the host, then pass the socket into your container:

```bash
docker run --rm -it \
  -v /run/rtop.sock:/run/rtop.sock \
  ghcr.io/batuhanberkayaydin/rockchip_stats:latest
```

---

## Architecture

rockchip-stats runs as a background service (root) that reads sysfs/procfs/debugfs and exposes data over a Unix socket. The `rtop` client connects to the socket and renders the TUI.

```
┌──────────────────┐    /run/rtop.sock    ┌──────────────────┐
│  rtop (client)   │ ◄─────────────────► │  rtop (service)  │
│  curses TUI      │                      │  data collector  │
└──────────────────┘                      └────────┬─────────┘
                                                   │
                                          sysfs · procfs · debugfs
```

---

## Development

Run directly from the repo without installing:

```bash
sudo python3 -m rtop                        # normal
sudo python3 -m rtop --debug 2>debug.log    # with debug output
sudo python3 -m rtop --no-service           # without socket
sudo python3 -m rtop --force                # start as service
```

To use repo changes immediately (editable install):

```bash
sudo pip3 install -e . --break-system-packages
sudo systemctl restart rtop
```

---

## License

GNU Affero General Public License v3.0 — see [LICENSE](LICENSE).

---

## Acknowledgements

Inspired by [jetson_stats](https://github.com/rbonghi/jetson_stats) by rbonghi.  
Adapted and extended for Rockchip SoC platforms.
