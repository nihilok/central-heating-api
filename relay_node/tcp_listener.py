import socket
import time


def is_local_address(remote_addr):
    if remote_addr[0] == "::1":
        return True

    # Define local network range - 192.168.1.0/24 in manual comparison
    local_network_start = 3232235776  # Integer representation of 192.168.1.0
    local_network_end = 3232236031  # Integer representation of 192.168.1.255

    # Define loopback addresses - 127.0.0.0/8 and ::1/128 in manual comparison
    loopback_start = 2130706432  # Integer representation of 127.0.0.0
    loopback_end = 2147483647  # Integer representation of 127.255.255.255
    ipv6_loopback = 1  # Integer representation of ::1

    # Convert remote address to integer representation for comparison
    remote_ip_parts = remote_addr[0].split(".")
    remote_ip = 0
    for part in remote_ip_parts:
        remote_ip = (remote_ip << 8) + int(part)

    # Check if the remote address is in the local network or loopback addresses
    return (
        (local_network_start <= remote_ip <= local_network_end)
        or (loopback_start <= remote_ip <= loopback_end)
        or (remote_ip == ipv6_loopback)
    )


class HTTPServer:
    def __init__(self, host, port, connections=5, feedback=None):
        addr_info = socket.getaddrinfo(
            host, port, 0, socket.SOCK_STREAM, socket.SOL_TCP
        )
        addr = None
        for info in addr_info:
            if info[0] == socket.AF_INET or info[0] == socket.AF_INET6:
                addr = info[-1]
                break
        if addr is None:
            raise RuntimeError("No valid address information found")

        self.socket = socket.socket(info[0], socket.SOCK_STREAM)

        if addr[0] == "::1":
            addr = ("localhost", addr[1], 0, 0)

        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(addr)
        print("listening on", addr)
        self.socket.listen(connections)
        self.cl = None
        self.paths = {}
        self.feedback = feedback

    def success(self, content, content_type="text/plain", status_code=200):
        content = str(content).encode("utf-8")
        http = (
            "HTTP/1.1 {} OK\r\nContent-Type: {}\r\nContent-Length: {}\r\n\r\n".format(
                status_code, content_type, len(content)
            )
        )
        http = http.encode("utf-8")

        if self.cl.fileno() != -1:  # Check if the file descriptor is valid
            self.cl.send(http)
            self.cl.send(content)
            self.cl.close()
        else:
            print("Socket is closed, cannot send data.")

    def error(self, status_code: int, content=""):
        content = str(content).encode("utf-8")
        self.cl.send(
            "HTTP/1.1 {} ERROR\r\nContent-Length: {}\r\n\r\n".format(
                status_code, len(content)
            ).encode("utf-8")
        )
        self.cl.send(content)
        self.cl.close()

    def listen(self):
        while True:
            self.cl, addr = self.socket.accept()
            if not is_local_address(addr):
                print("Remote address is not on the local network")
                self.error(401, "Remote address is not on the local network")
                continue
            if self.feedback is not None:
                self.feedback()
            request = self.cl.recv(1024)
            request = request.decode("utf-8")
            request_lines = request.split("\r\n")
            request_line_1 = request_lines[0]
            method, path, version = request_line_1.split(" ")
            print(time.time(), addr[0], method, path, version, end=" ")
            path, args, kwargs = self.parse_kwargs(path)
            route = self.paths.get(path)
            if route is None:
                self.error(404, "NOT FOUND")
                print(404)
                continue
            self.success(route(*args, **kwargs))
            print(200)

    @staticmethod
    def _request(request):
        line = request.readline()
        if not line or line == b"\r\n":
            raise StopIteration
        yield line.decode("utf-8")

    @staticmethod
    def parse_kwargs(path):
        path = path.split("?")
        kwarg_dict = {}
        if len(path) > 1:
            args = path[-1].split("&")
            for arg in args:
                k, v = arg.split("=")
                kwarg_dict[k] = v
        path = path[0].split("/")[1:]
        return path[0], path[1:], kwarg_dict

    def register_route(self, path, func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.error(500, "Internal server error: %s" % e)

        self.paths[path] = wrapper


if __name__ == "__main__":
    server = HTTPServer("localhost", 8989, 5)
    server.register_route("hello", lambda request: print("hello!"))
    server.listen()
