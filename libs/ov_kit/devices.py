"""OpenVINO device enumeration shared across apps."""

from __future__ import annotations


def populate_device_combo(combo, default: str = "GPU.1") -> None:
    """Fill a QComboBox with available OpenVINO devices.

    Each item's display text is ``"<id> - <full name>"`` and its userData
    is the bare device id (e.g. ``GPU.1``).  Falls back to a static list
    when OpenVINO is unavailable.
    """
    try:
        from openvino import Core

        core = Core()
        for dev in core.get_available_devices():
            try:
                full_name = core.get_property(dev, "FULL_DEVICE_NAME")
                display = f"{dev} - {full_name}"
            except Exception:
                display = dev
            combo.addItem(display, dev)
    except Exception:
        for d in ["CPU", "GPU.0", "GPU.1", "NPU"]:
            combo.addItem(d, d)

    idx = combo.findData(default)
    if idx >= 0:
        combo.setCurrentIndex(idx)
