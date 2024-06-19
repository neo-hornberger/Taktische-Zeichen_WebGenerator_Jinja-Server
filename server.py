import os
import http.server
import jinja2
import urllib3
import urllib.parse as urlparse
import json

def main():
	global env
	env = jinja2.Environment(
		loader=jinja2.FileSystemLoader('./Taktische-Zeichen'),
		autoescape=True,
		trim_blocks=True,
	)

	host = os.environ.get('SERVER_HOST', 'localhost')
	port = int(os.environ.get('SERVER_PORT', 9000))

	print(f'Starting server on {host}:{port}')
	print()

	server = http.server.HTTPServer((host, port), JinjaRequestHandler)
	server.serve_forever()

class JinjaRequestHandler(http.server.BaseHTTPRequestHandler):
	def _cors_headers(self):
		self.send_header('Access-Control-Allow-Origin', '*')
		self.send_header('Access-Control-Allow-Methods', 'GET, HEAD')
		#self.send_header('Access-Control-Allow-Headers', 'Content-Type')

	def do_HEAD(self):
		url = urllib3.util.parse_url(self.path)

		if url.path == '/status':
			self.send_response(200)
			self._cors_headers()
			self.end_headers()
			return

		self.send_response(400)
		self.end_headers()

	def do_GET(self):
		url = urllib3.util.parse_url(self.path)

		if url.path == '/build':
			query = urlparse.parse_qs(url.query)

			template = None
			if 'template' in query:
				match query['template'][0]:
					case 'unit':
						template = env.get_template('templates/einheit.j2t')
					case 'boat':
						template = env.get_template('templates/boot.j2t')
					case 'vehicle':
						template = env.get_template('templates/fahrzeug.j2t')
					case 'command_post':
						template = env.get_template('templates/führungsstelle.j2t')
					case 'building':
						template = env.get_template('templates/gebäude.j2t')
					case 'person':
						template = env.get_template('templates/person.j2t')
					case 'post':
						template = env.get_template('templates/stelle.j2t')
				del query['template']
			
			if template is None:
				self.send_response(400)
				self.end_headers()
				return

			try:
				variables = { key: parseValue(value[0]) for key, value in query.items() }
				print(variables)
				body = template.render(variables).encode('utf-8')

				self.send_response(200)
				self._cors_headers()
				self.send_header('Content-type', 'image/svg+xml')
				self.end_headers()
				self.wfile.write(body)
			except jinja2.exceptions.TemplateRuntimeError as e:
				self.send_response(400)
				self.send_header('Content-type', 'text/plain')
				self._cors_headers()
				self.end_headers()
				if isinstance(e, jinja2.exceptions.UndefinedError) and '[ERROR]' in e.message:
					self.wfile.write(e.message[33:-2].encode('utf-8'))
				else:
					self.wfile.write(str(e).encode('utf-8'))
			return

		self.send_response(400)
		self.end_headers()
	
def parseValue(value):
	if value == 'true':
		return True
	elif value == 'false':
		return False
	
	try:
		return json.loads(value)
	except:
		pass
	
	return value

if __name__ == '__main__':
	main()
