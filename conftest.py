collect_ignore_glob = []


def pytest_configure(config):
    # mock_serial falla en Windows porque importa termios (Unix-only).
    # Lo desregistramos antes de que intente cargar.
    try:
        config.pluginmanager.unregister(name="mock_serial")
    except Exception:
        pass
