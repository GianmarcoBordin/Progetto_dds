from threading import Thread
import logging
import Process
import sys
import time
import utils


TIME_BEFORE_BROADCAST = 8


if __name__ == "__main__":
    if len(sys.argv) > 5:
        
        print(
            "Usage: python ProcessMain.py <broadcast message> <payload_size> <round> <sim number>"
        )
        exit(-1)

    # Since all the processes share the same code it's required to distinguish
    # sender from receiver
    # Simulation number is used to initialize correctly simulation folders
    elif len(sys.argv) == 5:
        message = sys.argv[1]
        payload_size = sys.argv[2]
        round = sys.argv[3]
        sim_num = sys.argv[4]
        utils.set_process_logging(payload_size, round, sim_num)

        p = Process.Process()
        p.init_process()
        p.creation_links()
        # Timer is used to allow other processes to start and initialize connections between them
        time.sleep(TIME_BEFORE_BROADCAST)

        # Start broadcast
        p.broadcast(message)

    else:
        payload_size = sys.argv[1]
        round = sys.argv[2]
        sim_num = sys.argv[3]

        utils.set_process_logging(payload_size, round, sim_num)

        p = Process.Process()
        p.init_process()
        p.creation_links()

    exit(0)