import socket
import time


class HTTPServer:
    def __init__(self, host, port, connections=5, feedback=None):
        addr = socket.getaddrinfo(host, port)[0][-1]
        self.socket = socket.socket()
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
        self.cl.send(http)
        self.cl.send(content)
        self.cl.close()

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
