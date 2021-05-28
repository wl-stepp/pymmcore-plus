import atexit
import os
from pathlib import Path

import numpy as np
import pytest
from useq import MDAEvent, MDASequence

import pymmcore_remote
from pymmcore_remote._client import RemoteMMCore, new_server_process
from pymmcore_remote._server import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_URI
from pymmcore_remote.qcallbacks import QCoreCallback

# if not os.getenv("MICROMANAGER_PATH"):
#     try:
#         root = Path(pymmcore_remote.__file__).parent.parent
#         mm_path = list(root.glob("Micro-Manager-*"))[0]
#         os.environ["MICROMANAGER_PATH"] = str(mm_path)
#     except IndexError:
#         raise AssertionError(
#             "MICROMANAGER_PATH env var was not set, and Micro-Manager "
#             "installation was not found in this package.  Please run "
#             "`python micromanager_gui/install_mm.py"
#         )


@pytest.fixture(scope="session")
def server():
    proc = new_server_process(DEFAULT_HOST, DEFAULT_PORT)
    atexit.register(proc.kill)


@pytest.fixture
def proxy(server):
    with RemoteMMCore() as mmcore:
        mmcore.loadSystemConfiguration()
        yield mmcore


def test_client(proxy):
    assert str(proxy._pyroUri) == DEFAULT_URI


def test_mda(qtbot, proxy):
    mda = MDASequence(time_plan={"interval": 0.1, "loops": 2})
    cb = QCoreCallback()
    proxy.register_callback(cb)

    def _test_signal(img, event):
        return (
            isinstance(img, np.ndarray)
            and isinstance(event, MDAEvent)
            and event.sequence == mda
            and event.sequence is not mda
        )

    def _check_finished(obj):
        return obj.uid == mda.uid

    signals = [cb.MDAFrameReady, cb.MDAFrameReady, cb.MDAFinished]
    checks = [_test_signal, _test_signal, _check_finished]

    with qtbot.waitSignals(signals, check_params_cbs=checks, order="strict"):
        proxy.run_mda(mda)

