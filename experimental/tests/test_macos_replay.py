"""CPU-only checks for captured queue compatibility and generated structures."""

import importlib.util
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import agx_iokit
import cap_decode
from cap2standalone import emit_dataclass_init
from cap_format import CapCall, load_events


class MacOSReplayControls(unittest.TestCase):
    def test_captured_queue_inputs_on_both_os_versions(self):
        helpers = [agx_iokit.prepare_call_struct]
        for workload in ("add", "mul", "tri"):
            name = f"standalone_{workload}_control"
            spec = importlib.util.spec_from_file_location(
                name, ROOT.parent / "examples" / f"{workload}.py"
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            try:
                spec.loader.exec_module(module)
                helpers.append(module.prepare_call_struct)
            finally:
                del sys.modules[name]

        for workload in ("add", "mul", "tri"):
            calls = [event for event in load_events(ROOT / f"{workload}.cap")
                     if isinstance(event, CapCall)]
            captured = next(event.struct_in for event in calls if event.selector == 7)
            queue = captured[:0x408] + struct.pack("<II", 0xffffffff, 1)
            current = captured[:0x408] + struct.pack("<II", 1, 0)
            for helper in helpers:
                with self.subTest(workload=workload, helper=helper.__module__):
                    with patch("platform.mac_ver", return_value=("26.6.2", (), "arm64")):
                        self.assertEqual(helper(7, queue), queue)
                    with patch("platform.mac_ver", return_value=("27.0.1", (), "arm64")):
                        self.assertEqual(helper(7, queue), current)
                        self.assertEqual(helper(7, current), current)
                        for call in calls:
                            if call.selector != 7:
                                self.assertEqual(helper(call.selector, call.struct_in), call.struct_in)

    def test_current_queue_zero_field_survives_generation(self):
        queue = next(event.struct_in for event in load_events(ROOT / "add.cap")
                     if isinstance(event, CapCall) and event.selector == 7)
        current = queue[:0x408] + struct.pack("<II", 1, 0)
        decoded = cap_decode.QueueCreateIn.from_bytes(current)
        generated = eval(emit_dataclass_init(decoded), vars(cap_decode))
        self.assertEqual(generated.pack()[0x400:], current[0x400:])
        self.assertEqual(generated.pack(), decoded.pack())

    def test_captured_fields_survive_generation(self):
        for workload in ("add", "mul", "tri"):
            for index, event in enumerate(load_events(ROOT / f"{workload}.cap")):
                if not isinstance(event, CapCall):
                    continue
                for label, data, decoder in (
                    ("input", event.struct_in, cap_decode.decode_call_struct),
                    ("output", event.cap_struct, cap_decode.decode_call_out),
                ):
                    if not data:
                        continue
                    decoded = decoder(event.selector, data)
                    if not hasattr(decoded, "pack"):
                        continue
                    with self.subTest(workload=workload, index=index, field=label):
                        generated = eval(emit_dataclass_init(decoded), vars(cap_decode))
                        # The queue codec drops unused path padding; preserve every
                        # decoded field rather than requiring that padding back.
                        self.assertEqual(generated.pack(), decoded.pack())


if __name__ == "__main__":
    unittest.main()
