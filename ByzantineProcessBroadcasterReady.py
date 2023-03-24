import Process
import AuthenticatedLink
import time
import random

BREAK_TIME = 0.1


class ByzantineProcessBroadcasterReady (Process.Process):
    # This byzantine process does not terminate because it does not keep track of received messages,
    # but it sends a specific message to a random process

    def __update(self):
        super().update()

    def __thread(self):
        selected = random.randint(0, len(self.ids) // 2 - 1)
        while True:
            if self.echos[selected] != 0:
                # Send a byzantine ready message to only one process
                self.AL[selected].send("Byzantine", flag="READY")

            # Not to destroy performance
            time.sleep(BREAK_TIME)

    def broadcast(self, message):
        self.__update()
        for j in range(len(self.AL), len(self.ids)):
            self.AL.append(
                AuthenticatedLink.AuthenticatedLink(
                    self.selfid, self.selfip, self.ids[j], self.ips[j], self
                )
            )
            self.AL[j].receiver()
        # Half of the processes will receive a SEND message
        # while the other half will receive the "Byzantine" SEND message
        for i in range(len(self.ids) // 2):
            self.AL[i].send(message, flag="SEND")

        for i in range(len(self.ids) // 2, len(self.ids)):
            self.AL[i].send("Byzantine", flag="SEND")
        self.barrier.wait()

    def deliver_send(self, msg, flag, idn):
        # id == 1 checks that the delivery is computed with the sender s that by convention it's the first
        if flag == "SEND" and idn == 1 and self.sentecho is False:
            # Add the message if it's not yet received
            if msg not in self.currentMSG:
                self.currentMSG.append(msg)
            self.sentecho = True
            # In this case, the check done in order to update is not done
            # because the byzantine process is the one that broadcasts
            self.barrier.wait()

            # Half of the processes will receive an ECHO message
            # while the other half will receive the "Byzantine" ECHO message
            for i in range(len(self.ids) // 2):
                self.AL[i].send(msg, flag="ECHO")

            for i in range(len(self.ids) // 2, len(self.ids) - 1):
                self.AL[i].send("OtherByzantine", flag="ECHO")   # TODO check if this message is not too long

            # Only one process receives Byzantine message
            # while the others will receive another Byzantine message
            self.AL[len(self.AL) - 1].send("Byzantine", flag="ECHO")
