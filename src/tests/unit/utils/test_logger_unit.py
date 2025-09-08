import io
import logging
from contextlib import redirect_stdout

from src.utils.logger import AppLogger


def test_logger_setup_levels_and_output(tmp_path):
    buf = io.StringIO()
    with redirect_stdout(buf):
        lg = AppLogger()
        # Переконфигурируем на DEBUG и файл
        log_file = tmp_path / "log.txt"
        lg.setup_logging("DEBUG", str(log_file))
        lg.debug("dbg", x=1)
        lg.info("info", a=2)
        lg.warning("warn", b=3)
        lg.error("err", c=4)

    out = buf.getvalue()
    assert "dbg | x: 1" in out
    assert "info | a: 2" in out
    assert "warn | b: 3" in out
    assert "err | c: 4" in out
    # файл создан
    assert log_file.exists()


