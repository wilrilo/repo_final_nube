import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.ioloop
import tornado.options
import json
from uuid import uuid4
import time
import threading
import random
from ubidots import ApiClient

# crear api

api = ApiClient(token= 'SCJeJGv3tVyyiR9RjzBQXL9XgzCCxt')

#creamos las api y los id

humedad = api.get_variable("5763b2ab7625421ca1a7d82a")
temperatura = api.get_variable("5763ac2376254249a1fa9eba")


#libreria para usar el puerto GPIO
import RPi.GPIO as GPIO

#configurando GPIO
#pines por el numero impreso en la tarjeta,numeracion distribucion fisica 
#GPIO.setmode(GPIO.BOARD)    
#pines por el numero canal de las etiquetas.
GPIO.setmode(GPIO.BCM)    	

#Configurando el pin de salida
GPIO.setup(11, GPIO.OUT)
GPIO.output(11, False)

#Configurando el pin de entrada
swichtPin = 10

GPIO.setup(swichtPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#Interrupcion por hardware
def pinkCall(channel):
    pulsador = Raspberry()
    inputValue = GPIO.input(11)
    
    if(inputValue == True):
        GPIO.output(11, False)
        
        pulsador.notifyCallbacks(0, 'La valvula fue apagado por Hardware')

    if(inputValue == False):
        GPIO.output(11, True)
        
        pulsador.notifyCallbacks(1, 'La valvula fue encendido por Hardware')

    print('Interrupcion por hardware')


GPIO.add_event_detect(swichtPin, GPIO.RISING, callback=pinkCall, bouncetime=500)

class Raspberry(object):
	callbacks = []

	def obDistancia(self):            
                hume = random.randint(20,50)
                humedad.save_value({"value":hume})
                time.sleep(1)
                tempe = random.randint(7,16)                
                temperatura.save_value({"value":tempe})                
                print('humedad= ', hume)
                print('temperatura= ', tempe)
	

	def register(self, callback):
		self.callbacks.append(callback)

	def unregister(self, callback):
		self.callbacks.remove(callback)

	def ledON(self):
            #Encendemos el Led conectado en el pin 11
            GPIO.output(11, True)
            self.notifyCallbacks(1, "Valvula Encendido")

	def ledOFF(self):
            #Apagamos el Led conectado en el pin 11
            GPIO.output(11, False)
            self.notifyCallbacks(0, "Valvula Apagado")

	def notifyCallbacks(self, ledStdo, estado):
		for callback in self.callbacks:
			callback(ledStdo, estado)

class CuentaDistancia(threading.Thread):
	def run(self):
		d = Raspberry()
		n = 50
		while True:
			d.obDistancia()
			time.sleep(1)

th = CuentaDistancia()
th.daemon = True
th.start()


class RenderHandler(tornado.web.RequestHandler):

	def get(self):
		session = uuid4()
		estado = "...Iniciando"
		self.render("index.html", session=session, estado=estado)


class LedHandler(tornado.web.RequestHandler):
	def post(self):
		action = self.get_argument('action')
		session = self.get_argument('session')
		
		if not session:
			self.set_status(400)
			return

		if action == 'ledon':
			self.application.raspberry.ledON()
		elif action == 'ledoff':
			self.application.raspberry.ledOFF()
		else:
			self.set_status(400)

class RaspberryHandler(tornado.websocket.WebSocketHandler):
	def open(self):
		self.write_message('{"estado":"Conexion abierta"}')
		self.application.raspberry.register(self.callback)	
		print("Conexion abierta ")
	
	def on_close(self): 
		self.application.raspberry.unregister(self.callback)
		print("Conexion Cerrada")

	def on_message(self, message):
		self.write_message('{"estado":"Mensaje Recibido"}')
		print("Mensaje Recibido: {}" .format(message)) 	

	def callback(self, ledStdo, estado):

		self.write_message(json.dumps({
			"ledStdo": ledStdo,
			"estado": estado
			}))

class Application(tornado.web.Application):
	try:
		def __init__(self):
			self.raspberry = Raspberry()
		
			handlers = [
				(r'/', RenderHandler),
				(r'/led', LedHandler),
				(r'/status', RaspberryHandler)
			]
		
			settings = {
				'template_path': 'templates',
				'static_path': 'static'
			}

			tornado.web.Application.__init__(self, handlers, **settings)
	
	except keyboardInterrupt:
		print("No se pudo realizar la Conexion")


if __name__ == '__main__':
	tornado.options.parse_command_line()	
	
	app = Application()
	server = tornado.httpserver.HTTPServer(app)
	server.listen(5000)
	tornado.ioloop.IOLoop.instance().start()
