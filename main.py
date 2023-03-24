import time
import logging

import ByzantineProcessSilent
import Process
import ByzantineProcessBroadcasterEcho
import ByzantineProcessBroadcasterReady

#Role = "Broadcaster"
#Role = "Receiver"
#Role = "ByzantineBroadcasterEcho"
#Role = "ByzantineBroadcasterReady"
Role = "ByzantineSilent"

TIME_SLEEP = 10

if __name__ == "__main__":
        logging.basicConfig(filename="debug.log", filemode="w", level=logging.INFO)
        logging.info("MAIN:STARTING PROTOCOL--> BYZANTINE RELIABLE BROADCAST")
        if Role == "Receiver":
                p = Process.Process()
                p.connection_to_server()
                p.creation_links()
        elif Role == "Broadcaster":
                p = Process.Process()
                p.connection_to_server()
                p.creation_links()
                time.sleep(TIME_SLEEP)
                p.broadcast("Hellooo")
        elif Role == "ByzantineBroadcasterEcho":
                p = ByzantineProcessBroadcasterEcho.ByzantineProcessBroadcasterEcho()
                p.connection_to_server()
                p.creation_links()
                time.sleep(TIME_SLEEP)
                p.broadcast("BYNZATINEEE")
        elif Role == "ByzantineBroadcasterReady":
                p = ByzantineProcessBroadcasterReady.ByzantineProcessBroadcasterReady()
                p.connection_to_server()
                p.creation_links()
                time.sleep(TIME_SLEEP)
                p.broadcast("BYNZATINEEE")
        elif Role == "ByzantineSilent":
                p = ByzantineProcessSilent.ByzantineProcessSilent()
                p.connection_to_server()
                p.creation_links()
        logging.info("MAIN:ENDING PROTOCOL--> BYZANTINE RELIABLE BROADCAST")
        logging.info("MAIN:SUCCESSFUL EXIT")
        exit(0)
