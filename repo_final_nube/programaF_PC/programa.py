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


humedad2 = api.get_variable("5763b2c87625421f2f017764")
temperatura2 = api.get_variable("5763b35276254225fcaaa266")


class Raspberry(object):
	callbacks = []

	def obDistancia(self):            
                hume2 = random.randint(10,30)
                humedad2.save_value({"value":hume2})
                tempe2 = random.randint(10,20)                
                temperatura2.save_value({"value":tempe2})           
                print('humedad= ', hume2)
                print('temperatura= ', tempe2)


	def register(self, callback):
		self.callbacks.append(callback)

	def unregister(self, callback):
		self.callbacks.remove(callback)

	def ledON(self):
		self.notifyCallbacks(1, "Led Encendido")

	def ledOFF(self):
		self.notifyCallbacks(0, "Led Apagado")

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
