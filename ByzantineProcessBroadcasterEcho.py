import Process
import AuthenticatedLink

class ByzantineProcessBroadcasterEcho (Process):
    pass

    def broadcast(self, message):
        self.__update()
        for j in range(len(self.AL), len(self.ids)):
            self.AL.append(
                AuthenticatedLink.AuthenticatedLink(
                    self.selfid, self.selfip, self.ids[j], self.ips[j], self
                )
            )
            self.AL[j].receiver()
        for i in range(len(self.ids) // 2):
            # All these IF statements can be removed due to the fact that the byzantine process
            # is not supposed to deliver or terminate
            if message not in self.currentMSG:
                self.currentMSG.append(message)
            self.AL[i].send(message, flag="SEND")

        for i in range(len(self.ids) // 2, len(self.ids)):
            # IF statement that can be removed according to previous sentence
            if "Byzantine" not in self.currentMSG:
                self.currentMSG.append("Byzantine")
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

            for i in range(len(self.ids) // 2):
                # IF statement that can be removed according to previous sentence
                if msg not in self.currentMSG:
                    self.currentMSG.append(msg)
                self.AL[i].send(msg, flag="ECHO")

            for i in range(len(self.ids) // 2, len(self.ids)):
                # IF statement that can be removed according to previous sentence
                if "Byzantine" not in self.currentMSG:
                    self.currentMSG.append("Byzantine")
                self.AL[i].send("Byzantine", flag="ECHO")