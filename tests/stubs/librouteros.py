"""RouterOS tiruan.

ROUTER['down']       jumlah pelanggan down
ROUTER['fail']       gagal saat connect: True/"timeout", "login", "refused", "host", "closed"
ROUTER['graphing']   True = Tools > Graphing berisi interface=all (ether1)
ROUTER['delay']      detik jeda saat connect (router lambat)
ROUTER['last']       argumen connect terakhir (host, port, ...)
ROUTER['query_fail'] connect berhasil tetapi perintah print terputus (router mati di tengah cek)
"""
import socket
import time

ROUTER = {"down": 1, "fail": False, "query_fail": False, "graphing": False, "last": {}, "delay": 0}


class TrapError(Exception):
    pass


class ConnectionClosed(Exception):
    pass


_FAILURES = {
    "login": lambda: TrapError("invalid user name or password (6)"),
    "refused": lambda: ConnectionRefusedError(10061, "No connection could be made because the target machine "
                                                     "actively refused it"),
    "host": lambda: socket.gaierror(11001, "getaddrinfo failed"),
    "closed": lambda: ConnectionClosed("Connection unexpectedly closed."),
}


class _Connection:
    def __call__(self, path):
        if ROUTER["query_fail"] and path.startswith("/ppp/"):
            raise socket.timeout("timed out")
        if path == "/ppp/secret/print":
            down = [{"name": f"pel_{i:04d}", "profile": "home"} for i in range(ROUTER["down"])]
            return down + [{"name": "online1", "profile": "home"}]
        if path == "/ppp/active/print":
            return [{"name": "online1", "uptime": "1h"}]
        if path == "/tool/graphing/interface/print":
            return [{"interface": "all", "disabled": False}] if ROUTER["graphing"] else []
        if path == "/interface/print":
            return [{"name": "ether1", "comment": "uplink"}]
        if path == "/system/identity/print":
            return [{"name": "R_1"}]
        return []


def connect(**kwargs):
    ROUTER["last"] = kwargs
    if ROUTER["delay"]:
        time.sleep(ROUTER["delay"])  # slow / far router
    fail = ROUTER["fail"]
    if fail:
        raise _FAILURES[fail]() if fail in _FAILURES else socket.timeout("timed out")
    return _Connection()
