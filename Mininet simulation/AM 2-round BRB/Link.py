import logging
from threading import Thread
import Link_handler


class Link:
    def __init__(self, sid, sip, idn, ip, process):
        self.sid = sid  # id of this process
        self.id = idn  # id of other process
        self.sip = sip  # ip of this process
        self.ip = ip  # ip of the other process
        self.process = process  # process instance to callback for arrived messages
        self.thread_s = None  # ref to TCP/IP socket interface thread
        self.thread_r=None # ref to TCP/IP socket interface thread
        self.l=None


    def build_Link_r(self):
        # modelling the rx side of the link
        # It uses ternary operator
        logging.info("LINK:Creating link for receiving from <%s,%d>", self.ip, self.id)
        port = (
            int("51" + str(self.id) + str(self.sid))
            if self.sid < 10 and self.id < 10
            else int("6" + str(self.id) + str(self.sid))
        )
        self.td = Link_handler.tcp_rx(self, self.sip, port, self.id)
        self.thread_r = Thread(target=self.td.run, args=())
        self.thread_r.start()

    def build_Link_s(self):
        # modelling the rx side of the link
        # It uses ternary operator
        logging.info("LINK:Creating link for sending to <%s,%d>", self.ip, self.id)
        port = (
            int("51" + str(self.sid) + str(self.id))
            if self.sid < 10 and self.id < 10
            else int("6" + str(self.sid) + str(self.id))
        )
        self.ts = Link_handler.tcp_snd(self.ip, port, self.id)
        self.thread_s = Thread(target=self.ts.run, args=())
        self.thread_s.start()

    def link_receive(self, msg):  # to call the upper module
        logging.info("LINK:Forwarding message to process module from Link module")
        self.process.process_receive(msg)

    def link_send(self, msg):
        self.ts.sending_msg=msg
        self.ts.sending_flag=True
        logging.info("LINK:Sending message to Link_handler module from Link module")