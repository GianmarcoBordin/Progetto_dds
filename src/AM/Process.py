import math
import AM.utils as utils
import socket
import json
import time
import logging


from hashlib import sha512
from AM.AuthenticatedLink import AuthenticatedLink
from AM.Evaluation import Evaluation
from AM.NormalLink import Link

KDS_PORT = 8081
RCV_BUFFER_SIZE = 32768
BREAK_TIME = 0.1
BROADCASTER_ID = 1


class Process:
    def __init__(self, kds_ip):
        self.ids = []
        self.ips = []
        self.checked = {}
        self.signed_vote_messages = []
        self.sip = 0
        self.sid = 0
        self.L = []
        self.AL = []
        self.start = 0
        self.key_gen = False
        self.keyPair = {}
        self.public_keys = {}
        self.delivered = False
        self.counter_signed_mess = {}
        self.faulty = 0  # f<N/3 condition to protocol correctness
        self.eval = Evaluation()
        self.KDS_ip = kds_ip

    def init_process(self):
        self.eval.tracing_start()
        self.init_process_ids()
        self.get_key_pair()
        self.faulty = math.floor((len(self.ids) - 1) / 3)
        logging.debug("PROCESS: id list: %s,ip list %s", self.ids, self.ips)
        print("-----GATHERED ALL THE PEERS IPS AND IDS-----")
        print("-----STARTING SENDING OR RECEIVING MESSAGES-----")

    def init_process_ids(self):
        processes = utils.read_process_identifier()
        for pair in processes:
            self.ids.append(int(pair[0]))  # pair[0] --> ID
            self.ips.append(pair[1])  # pair[1] --> IPS

        # set id and ip
        self.sip = utils.get_ip_of_interface()
        self.sid = self.ids[self.ips.index(self.sip)]

    def creation_links(self):
        # creating links
        for i in range(0, len(self.ids)):
            # init links
            self.L.append(
                Link(
                    self.sid,
                    self.sip,
                    self.ids[i],
                    self.ips[i],
                    self,
                )
            )

            self.L[i].receiver()

        if self.sid == BROADCASTER_ID:
            for i in range(0, len(self.ids)):
                self.AL.append(
                    AuthenticatedLink(
                        self.sid, self.sip, self.ids[i], self.ips[i], self
                    )
                )

        else:
            self.AL.append(
                AuthenticatedLink(self.sid, self.sip, self.ids[0], self.ips[0], self)
            )
        self.AL[0].receiver()

    def get_process_keys(self):
        try:
            for id in self.ids:
                temp_key = self.connection_to_KDS(id, 0)
                self.public_keys.setdefault(str(id), {})
                self.public_keys[str(id)].setdefault("N", {})
                self.public_keys[str(id)].setdefault("E", {})
                self.public_keys[str(id)]["N"] = temp_key["N"]
                self.public_keys[str(id)]["E"] = temp_key["E"]

            logging.info("PUBLIC KEYS: %s", self.public_keys)
        except Exception as e:
            logging.info(e)

    def get_key_pair(self):
        # connect to kds to get keyPair
        if not self.key_gen:
            logging.info("PROCESS:Calling KDS to get key pair")
            self.key_gen = True
            self.keyPair = self.connection_to_KDS(self.sid, 1)

    def broadcast(self, *args):
        message = ""
        size = 0
        if len(args) > 0:
            # Enter message you want to broadcast
            size = args[0]
            message = utils.generate_payload(size)
        else:
            message = str(input("Enter message: "))

        msg = {}
        msg["TYPE"] = 0
        msg["FLAG"] = "PROPOSE"
        msg["MSG"] = message
        msg["FROM"] = BROADCASTER_ID

        for j in range(0, len(self.ids)):
            self.AL[j].send(msg)

        logging.info("PROCESS:Message:%s,broadcasted successfully", message)

    def process_receive(self, message):
        # receive messages from the underlying pppl
        match message.get("TYPE"):
            case 0:
                if len(self.public_keys) == 0:
                    self.get_process_keys()

                if (
                    message.get("FROM") == BROADCASTER_ID
                    and message.get("FLAG") == "PROPOSE"
                ):
                    msg = {}
                    msg["FLAG"] = "VOTE"
                    msg["MSG"] = message.get("MSG")
                    msg["SIGN"] = self.make_signature(msg.get("FLAG") + msg.get("MSG"))
                    msg["TYPE"] = 1
                    msg["FROM"] = self.sid

                    for j in range(0, len(self.ids)):
                        self.L[j].send(msg)
                    logging.info(
                        "PROCESS:Vote message:%s,broadcasted successfully", msg
                    )

            case 1:
                # key used to reduce redundancy
                key_to_check = (
                    message.get("FLAG"),
                    message.get("MSG"),
                    message.get("SIGN"),
                    message.get("FROM"),
                )

                # we check whether a message sign has already been checked
                if message.get("FLAG") == "VOTE":
                    if key_to_check not in self.checked.keys():
                        # set for that specific key the check signature result so that it's not
                        # required to check twice the same message
                        self.checked[key_to_check] = self.check_signature(
                            message.get("FLAG") + message.get("MSG"),
                            message.get("SIGN"),
                            message.get("FROM"),
                        )

                    if self.checked[key_to_check]:
                        # if signature is valid then check whether you have n - f signed VOTE messages
                        self.check(message)

            case 2:
                # used to count verified message, if n - f then deliver
                counter = 0

                # store into a temp variable list of forwarded signed messages
                temp_l = message["SIGNED_VOTE_MSGS"]

                if (
                    len(temp_l) == (len(self.ids) - self.faulty)
                ) and not self.delivered:
                    # used to take trace for how many signs for a message
                    messages = {}

                    for elem in temp_l:
                        # temp key to reduce redundancy
                        key_to_check = (
                            elem["FLAG"],
                            elem["MSG"],
                            elem["SIGN"],
                            elem["FROM"],
                        )

                        # check whether the message signature has already been checked
                        if key_to_check not in self.checked.keys():
                            # if no then check and store it
                            self.checked[key_to_check] = self.check_signature(
                                elem["FLAG"] + elem["MSG"],
                                elem["SIGN"],
                                elem["FROM"],
                            )

                        # if signature is valid and the current message is really a VOTE increase the counter
                        if self.checked[key_to_check] and "VOTE" == elem["FLAG"]:
                            counter += 1
                            messages[elem["MSG"]] = counter

                            # check whether there is a signed vote message with at least n - f signs
                            # it is used to avoid to deliver a last message which is forged by the byzantine process
                            msg_to_deliver = self.there_is_message(messages)

                            # when you have n-f valid message commit and close link
                            if counter == len(self.ids) - self.faulty:
                                for i in range(len(self.ids)):
                                    self.L[i].send(message)
                                    self.deliver(msg_to_deliver)

                                    logging.info(
                                        "BYTES SENT: %d",
                                        self.__get_bytes_sent() / 1024,
                                    )

                else:
                    logging.info(
                        "PROCESS:Already delivered not re-broadcast all the signed vote messages"
                    )
            case _:
                logging.info("PROCESS:ERROR:Received a message of type undefined")

    def close_link(self):
        for j in range(0, len(self.ids)):
            self.L[j].ts.terminating_flag = True
            self.L[j].td.terminating_flag = True
        exit(0)

    def there_is_message(self, messages):
        for mess, value in messages.items():
            if value >= len(self.ids) - self.faulty:
                return mess

    # if you have n-f then forward this signed messages to all processes
    def check(self, message):
        temp_dict = {
            "FLAG": message["FLAG"],
            "MSG": message["MSG"],
            "SIGN": message["SIGN"],
            "FROM": message["FROM"],
        }

        # add vote message to signed
        self.signed_vote_messages.append(temp_dict)

        # count signed messages
        if message["MSG"] not in self.counter_signed_mess.keys():
            self.counter_signed_mess[message["MSG"]] = 0

        self.counter_signed_mess[message["MSG"]] += 1
        # when there are at least n - f signed message add them to list
        if self.counter_signed_mess[message["MSG"]] >= len(self.ids) - self.faulty:
            list_of_signed_msg = []
            for elem in self.signed_vote_messages:
                if elem["MSG"] == message["MSG"]:
                    list_of_signed_msg.append(elem)

            vote_messages = {
                "SIGNED_VOTE_MSGS": list_of_signed_msg,
                "TYPE": 2,
                "FROM": self.sid,
            }
            for i in range(len(self.ids)):
                # wrap into a list to avoid JSONDecodeError
                self.L[i].send(vote_messages)

    def check_signature(self, message, signature, idn):
        # checking signature for received signed vote messages
        try:
            # wait until the key of the process who I need to check signature is added
            while str(idn) not in self.public_keys.keys():
                pass

            msg = bytes(message, "utf-8")
            hash = int.from_bytes(sha512(msg).digest(), byteorder="big")

            hashFromSignature = pow(
                signature,
                self.public_keys[str(idn)]["E"],
                self.public_keys[str(idn)]["N"],
            )
            logging.info("PROCESS:Signature check exit:<%r>", hash == hashFromSignature)
            check = hash == hashFromSignature

            return check
        except KeyError as e:
            print(f"Error: {e}\nKey set: {self.public_keys}")

    def make_signature(self, message):
        # sign
        msg = bytes(message, "utf-8")
        hash = int.from_bytes(sha512(msg).digest(), byteorder="big")
        signature = pow(hash, self.keyPair["D"], self.keyPair["N"])
        logging.info("PROCESS:Signature:<%s>", hex(signature))
        return signature

    def connection_to_KDS(self, idn, typ):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            sock.connect((self.KDS_ip, KDS_PORT))
            logging.info("PROCESS:Connecting to KDS")
            # getting key pair from KDS
            pack = {}
            pack["FROM"] = idn
            pack["TYPE"] = typ
            send_pack = json.dumps(pack)
            sock.sendall(send_pack.encode())
            data = sock.recv(RCV_BUFFER_SIZE)
            parsed_data = json.loads(data.decode())
            # return a dict containing
            return parsed_data

    def deliver(self, message):
        if not self.delivered:
            # delivering the final message
            print("-----MESSAGE DELIVERED:", message, "-----")

            # End execution time
            end_time = time.time() * 1000

            # Memory used
            peak = self.eval.tracing_mem()

            logging.info(
                "----- MESSAGE DELIVERED, time: %s, size: %s",
                end_time,
                peak,
            )
            self.delivered = True

    def __get_bytes_sent(self):
        sent = 0
        for item in self.AL + self.L:
            sent += item.bytes_sent
        return sent
