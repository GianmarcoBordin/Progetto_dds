import AuthenticatedLink
import socket
import struct
import json
import pika

SERVER_ID = "192.168.1.40"
SERVER_PORT = 5000

RCV_BUFFER_SIZE = 1024

class ByzantineProcessSilent:
    def __init__(self):
        self.ids = []
        self.ips = []
        self.selfip = 0
        self.selfid = 0
        self.AL = []

    def connection_to_server(self):
        # It starts a connection to the server to obtain a port number
        print("-----CONNECTING TO SERVER...-----")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.connect((SERVER_ID, SERVER_PORT))
            mess = bytes("Hello", "utf-8")
            s.sendall(mess)
            data = s.recv(RCV_BUFFER_SIZE).decode()
        port = 5000 + int(data)
        print("-----CONNECTION TO SERVER SUCCESSFULLY CREATED-----")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.connect((SERVER_ID, port))
            mess = bytes("Hello", "utf-8")
            sock.sendall(mess)
            while True:
                # receive the length prefix (4 bytes in network byte order)
                len_prefix = sock.recv(4)
                if not len_prefix:
                    break

                # unpack the length prefix into an integer
                msg_len = struct.unpack("!I", len_prefix)[0]
                # receive the JSON object data
                json_data = b""
                while len(json_data) < msg_len:
                    packet = sock.recv(msg_len - len(json_data))
                    if not packet:
                        break
                    json_data += packet

                # parse the JSON object
                obj = json.loads(json_data.decode("utf-8"))

                # Add IP and ID to list
                if isinstance(obj, dict):
                    self.ids.append(obj.get("ID", "Not found"))
                    self.ips.append(obj.get("IP", "Not found"))
                # END is str so isinstance of obj returns false
                else:
                    break

        print("-----GATHERED ALL THE PEERS IPS FROM THE BOOTSTRAP SERVER-----")
        print("-----STARTING SENDING OR RECEIVING MESSAGES-----")

    def creation_links(self):
        hostname = socket.gethostname()
        IPAddr = socket.gethostbyname(hostname)

        self.selfip = IPAddr

        # You should use this only if the underlying machine's ip address is not coherent with others' ip addresses
        # (like, for example, if there is a WSL on the machine)
        # self.selfip = "192.168.1.x"

        self.selfid = self.ids[self.ips.index(self.selfip)]
        for i in range(0, len(self.ids)):
            self.AL.append(
                AuthenticatedLink.AuthenticatedLink(
                    self.selfid, self.selfip, self.ids[i], self.ips[i], self
                )
            )
            self.AL[i].receiver()

    # Before starting broadcast, a process reads the ip addresses and ids of
    # the other processes from its queue
    def __update(self):
        with pika.BlockingConnection(
            pika.ConnectionParameters(host=SERVER_ID)
        ) as connection:
            channel = connection.channel()

            response = channel.queue_declare(queue=str(self.selfid))
            # Get the queue length (number of not consumed messages)
            num = response.method.message_count

            if num == 0:
                channel.close()
                return

            self.counter = 0

            def callback(ch, method, properties, body):
                queue_msg = body.decode("utf-8")
                temp = queue_msg.split("#")
                ip_from_queue = temp[0]
                id_from_queue = temp[1]
                if ip_from_queue not in self.ips:
                    self.ips.append(ip_from_queue)
                    self.ids.append(int(id_from_queue))
                    self.AL.append(
                        AuthenticatedLink.AuthenticatedLink(
                            self.selfid,
                            self.selfip,
                            self.ids[len(self.ids) - 1],
                            self.ips[len(self.ips) - 1],
                            self,
                        )
                    )
                    self.AL[len(self.AL) - 1].receiver()
                self.counter += 1
                if self.counter == num:
                    channel.stop_consuming()
                    channel.close()

            channel.basic_consume(
                queue=str(self.selfid), on_message_callback=callback, auto_ack=True
            )
            channel.start_consuming()

    # This byzantine process only listens to messages that other processes send
    # without actually replying to them
    def deliver_send(self, msg, flag, idn):
        # id == 1 checks that the delivery is computed with the sender s that by convention it's the first
        if flag == "SEND" and idn == 1:
            self.__update()
        print("From <%d> I received: <%s,%s>", idn, msg, flag)

    def deliver_echo(self, msg, flag, idn):
        print("From <%d> I received: <%s,%s>", idn, msg, flag)

    def deliver_ready(self, msg, flag, idn):
        print("From <%d> I received: <%s,%s>", idn, msg, flag)