1)Install python 3.7 on linux

	sudo add-apt-repository ppa:deadsnakes/ppa
	sudo apt-get update
	sudo apt install python3.7-distutils

2)Install pip if it doesn't exist yet

	sudo apt install python3-pip

3)Install distutils package for python3.7

	sudo apt install python3.7-distutils


4)Install pyDistAlgo library for python3.7
 
	python3.7 -m pip install pyDistAlgo

Docker RabbitMQ

1)Start the Docker with RabbitMQ

	docker run -d -p <ip_address>:5672:5672 -p 15672:15672 rabbitmq:3.8.15-rc.2-management
Ngrok tunnel

1)Start the tunnel on localhost port XXXX on the ngrok command prompt

	ngrok tcp XXXX

Nel commit del 24/03/2023 riguardante l'implementazione dei processi bizantini sono stati cambiati anche il main, per renderlo più comodo da eseguire, e il process, poichè la funzione __update, privata, non poteva essere chiamata dalle classi figlie.
