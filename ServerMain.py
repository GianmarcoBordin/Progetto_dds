from threading import Thread
import logging
import Server


def run_server_thread():
    server = Server.TCP_SERVER()
    server.do_get()


if __name__ == "__main__":
    logging.basicConfig(filename='debug.log', filemode='w', level=logging.DEBUG)
    t = Thread(target=run_server_thread, )
    t.start()
    exit(0)