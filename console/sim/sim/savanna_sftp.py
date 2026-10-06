"""The customer's SFTP drop: core banking writes its nightly export here at 2am. Read-only for you."""

import asyncio
import threading

import asyncssh

from . import config


class ReadOnlySFTP(asyncssh.SFTPServer):
    def __init__(self, chan):
        root = config.SAVANNA_DIR / "sftp"
        root.mkdir(parents=True, exist_ok=True)
        super().__init__(chan, chroot=str(root).encode())

    def open(self, path, pflags, attrs):
        if pflags & (asyncssh.FXF_WRITE | asyncssh.FXF_APPEND | asyncssh.FXF_CREAT | asyncssh.FXF_TRUNC):
            raise asyncssh.SFTPError(asyncssh.FX_PERMISSION_DENIED, "this drop is read-only")
        return super().open(path, pflags, attrs)

    def _deny(self, *a, **k):
        raise asyncssh.SFTPError(asyncssh.FX_PERMISSION_DENIED, "this drop is read-only")

    remove = rename = mkdir = rmdir = setstat = fsetstat = symlink = link = posix_rename = _deny


class Server(asyncssh.SSHServer):
    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        return username == config.SAVANNA_SFTP["user"] and password == config.SAVANNA_SFTP["password"]


def _host_key():
    path = config.SAVANNA_DIR / "ssh_host_key"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        asyncssh.generate_private_key("ssh-ed25519").write_private_key(str(path))
    return asyncssh.read_private_key(str(path))


def start(port: int = 2222, host: str = "0.0.0.0") -> threading.Thread:
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(asyncssh.create_server(Server, host, port, server_host_keys=[_host_key()],
                                                           sftp_factory=ReadOnlySFTP, allow_scp=False))
            loop.run_forever()
        except OSError as e:
            print(f"[savanna] SFTP server not started: {e}", flush=True)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t
