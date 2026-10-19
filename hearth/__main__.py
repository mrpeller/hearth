"""Run Hearth:  python -m hearth"""
import sys

from . import network
from .app import App
from .web import serve


def main():
    if sys.version_info < (3, 9):
        sys.exit("Hearth needs Python 3.9 or newer.")
    import ssl
    if not ssl.HAS_TLSv1_3:
        sys.exit("This Python's SSL library has no TLS 1.3, which the TV requires. See the README (use start.sh).")
    app = App()
    server = serve(app)
    ip = network.local_ip()
    print(f"Hearth is running.\n  Phone remote:  http://{ip}:{app.port}\n  TV home:       http://{ip}:{app.port}/tv/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
