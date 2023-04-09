import socket
import hashlib
import hmac
import json
import logging
from threading import Thread

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

RCV_BUFFER_SIZE = 1024
KEY_SIZE = 32


class AuthenticatedLink:
    def __init__(self, self_id, self_ip, idn, ip, proc):
        self.proc = proc
        self.self_id = self_id  # id of the process that is creating this instance
        self.id = idn  # id of the other process
        self.self_ip = self_ip  # ip of the process that is creating this instance
        self.ip = ip  # ip of the other process
        self.key = {}  # key exchanged between the two processes

    def get_id(self):
        return self.self_id

    def receiver(self):
        print("Start thread to receive messages...")
        t = Thread(target=self.__receive)
        t.start()

    # This handles the message receive
    # Now the listening port is the concatenation 50/5 - 'receiving process' - 'sending process'
    def __receive(self):
        ready = False
        host = ""  # Symbolic name meaning all available interfaces
        # It uses ternary operator
        port = (
            int("50" + str(self.id) + str(self.self_id))
            if self.self_id < 10 and self.id < 10
            else int("5" + str(self.id) + str(self.self_id))
        )

        print(port)  # useful to check which connection is being created

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.s:
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s.bind((host, port))
            self.s.listen(0)
            while True:
                try:
                    conn, addr = self.s.accept()

                    with conn:
                        while True:
                            data = conn.recv(RCV_BUFFER_SIZE)
                            if not data:
                                break

                            parsed_data = json.loads(data.decode())

                            print("Message received by ", self.ip, ":", parsed_data)

                            if "FLAG" not in parsed_data.keys():
                                self.__add_key(parsed_data)
                                conn.sendall(b"synACK")
                            else:
                                t = Thread(
                                    target=self.__receiving,
                                    args=(parsed_data,),
                                )
                                t.start()
                                # The last part must be changed because the closing factor for the socket is different
                                # for every protocol

                                # if you receive an ACC for some message M from some other process,
                                # it means that it received at least n-f ECHOs for that message M,
                                # so it is safe to close the socket with it
                                # (it received at least f+1 ECHOs from correct processes,
                                # so it is impossible that it will send a REQ message;
                                # in fact, even if it receives the same message from all the faulty processes
                                # it will not send it because they are at most f)
                                # Otherwise, if you don't receive an ACC from someone,
                                # it may mean that it did not receive the message at all,
                                # so it may ask you about the message associated to the ACC that it received
                                # (indeed, you will send / sent an ACC message to it too)

                    if ready:
                        break
                except socket.error as e:
                    logging.info("AUTH:Socket error: %s"%e)
                    if e.winerror==10038:
                        logging.info("AUTH:Closing receiving auth interface")
                        exit(0)

    def __add_key(self, key_dict):
        self.key[self.id] = key_dict["KEY"].encode("latin1")

        logging.info(
            "AUTH: <%s, %d> is the one with this key: %s", self.ip, self.id, self.key
        )

    def __check(self, idn):
        if idn not in self.key:
            self.key[idn] = ChaCha20Poly1305.generate_key()

            key_to_send = {"KEY": self.key[idn].decode("latin1")}
            logging.info("AUTH: Key generated")

            data = json.dumps(key_to_send)
            self.sock.sendall(data.encode())
            self.temp = self.sock.recv(RCV_BUFFER_SIZE, 0).decode()

            if self.temp != "synACK":  # Ack used for synchronization with other process
                return 1

    # Compute the hmac of the message with the key exchanged
    # The message is returned as a dictionary: {"FLAG": flag, "MSG": message, ... "HMAC": hmac}
    # The hmac is computed starting from the concatenation of all the fields in the message
    def __auth(self, message):
        self.__check(self.id)
        # This creates the string that will be authenticated
        hmac_input = ""
        for value in message.values():
            hmac_input += str(value)
        # This creates the message that will be sent
        mess = {}
        dict_hmac = {"HMAC": hmac.new(
            self.key.get(self.id, "Key not found"), hmac_input.encode("utf-8"), hashlib.sha256, ).hexdigest(),
                     }
        for key in message.keys():
            dict_temp = {key: message[key]}  # Adding to the dictionary all the field that
            mess.update(dict_temp)  # were inside the original message
        mess.update(dict_hmac)  # Adding to it the HMAC just computed
        return mess

    # The SEND opens a new socket, the port is the concatenation of 50/5-
    # id of sending process - id of receiving process
    # Example: sending_id = 1, receiving_id = 2 ---> port = 5012
    def send(self, message):
        # It uses ternary operator
        port = (
            int("50" + str(self.self_id) + str(self.id))
            if self.self_id < 10 and self.id < 10
            else int("5" + str(self.self_id) + str(self.id))
        )

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.sock:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            while True:
                # Try Except used to repeat the connection until the other socket is opened again
                try:
                    self.sock.connect((self.ip, port))

                    # mess is a dictionary that contains the original packet plus the HMAC
                    mess = self.__auth(message)

                    print(mess, "sent to <", self.ip, self.id, ">")

                    parsed_data = json.dumps(mess)
                    self.sock.sendall(bytes(parsed_data, encoding="utf-8"))
                    break
                except ConnectionRefusedError:
                    continue

    # It checks message authenticity comparing the hmac
    def __check_auth(self, message):
        # This creates the string that should match with the HMAC
        hmac_input = ""
        for value in message.values():
            if value!=message["HMAC"]:
                hmac_input += str(value)

        temp_hash = hmac.new(self.key.get(self.id, "Key not found"), hmac_input.encode("utf-8"), hashlib.sha256, ) \
            .hexdigest()

        # The HMAC field is always present in the Authenticated Link implementation
        return temp_hash == message["HMAC"]

    def __receiving(self, message):

        if not self.__check_auth(message):
            logging.info("--- Authenticity check failed for %s", message)
        else:
            # This is the only part of the function that must be changed when using different algorithms

            # this is done in order to pass to the upper layer only the part that it requires
            # indeed, the HMAC is removed because it is useful only for this level
            message.pop("HMAC", None)

            self.proc.process_receive(message)
