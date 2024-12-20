import os
import glob
import http.server
import jinja2
import urllib3
import urllib.parse as urlparse
import json
from cairosvg import svg2png
from PIL import Image
from io import BytesIO


def main():
	global env
	env = jinja2.Environment(
		loader=jinja2.FileSystemLoader('./Taktische-Zeichen'),
		autoescape=True,
		trim_blocks=True,
	)

	host = os.environ.get('SERVER_HOST', 'localhost')
	port = int(os.environ.get('SERVER_PORT', 9000))

	global symbols
	symbols = []
	symbols_dir = './Taktische-Zeichen/symbols/'
	for path, subdirs, files in os.walk(symbols_dir):
		dir_name = os.path.relpath(path, symbols_dir)
		if not dir_name == '.test':
			for name in files:
				if name.endswith('.j2'):
					symbols.append(os.path.join(dir_name, name))
	symbols.sort()
	
	global symbol_themes
	symbol_themes = {}
	for theme in glob.glob('./Taktische-Zeichen/themes/*.json'):
		with open(theme, 'r') as f:
			symbol_themes[os.path.basename(theme)[:-5]] = json.load(f)
	
	global metadata
	metadata = {}
	with open('metadata.json', 'r') as f:
		metadata = json.load(f)

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
		query = urlparse.parse_qs(url.query)

		print(query)

		if url.path == '/build':
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
					case 'hazard':
						template = env.get_template('templates/gefahr.j2t')
					case 'device':
						template = env.get_template('templates/gerät.j2t')
					case 'person':
						template = env.get_template('templates/person.j2t')
					case 'post':
						template = env.get_template('templates/stelle.j2t')
					case 'communications_condition':
						template = env.get_template('templates/fernmeldewesen_bedingung.j2t')
				del query['template']
			
			if template is None:
				self.send_response(400)
				self.end_headers()
				return

			try:
				variables = { key: parseValue(value[0]) for key, value in query.items() }
				body = template.render(variables).encode('utf-8')

				self.send_symbol(body, renderOptions(query))
			except jinja2.exceptions.TemplateRuntimeError as e:
				self.send_response(400)
				self.send_header('Content-Type', 'text/plain')
				self._cors_headers()
				self.end_headers()
				if isinstance(e, jinja2.exceptions.UndefinedError) and '[ERROR]' in e.message:
					self.wfile.write(e.message[33:-2].encode('utf-8'))
				else:
					self.wfile.write(str(e).encode('utf-8'))
			
			return
		elif url.path == '/library':
			if 'symbol' in query:
				symbol = query['symbol'][0]
				if symbol in symbols:
					try:
						symbol_theme = query['theme'][0] if 'theme' in query else 'default'
						if symbol_theme not in symbol_themes:
							symbol_theme = 'default'
						symbol_theme = symbol_themes[symbol_theme]

						body = env.get_template(f'symbols/{symbol}').render(symbol_theme).encode('utf-8')

						self.send_symbol(body, renderOptions(query))
					except jinja2.exceptions.TemplateRuntimeError as e:
						self.send_response(400)
						self.send_header('Content-Type', 'text/plain')
						self._cors_headers()
						self.end_headers()
						if isinstance(e, jinja2.exceptions.UndefinedError) and '[ERROR]' in e.message:
							self.wfile.write(e.message[33:-2].encode('utf-8'))
						else:
							self.wfile.write(str(e).encode('utf-8'))
			else:
				self.send_response(200)
				self._cors_headers()
				self.send_header('Content-Type', 'application/json')
				self.end_headers()
				self.wfile.write(json.dumps({
					'themes': list(symbol_themes.keys()),
					'symbols': symbols,
				}).encode('utf-8'))
			
			return
		elif url.path == '/keywords':
			self.send_response(200)
			self._cors_headers()
			self.send_header('Content-Type', 'application/json')
			self.end_headers()
			self.wfile.write(json.dumps(list({
				keyword
				for m in metadata.values()
				for keyword in m['keywords']
			})).encode('utf-8'))
			return
		elif url.path == '/identify':
			filtered_symbols = symbols
			if 'filter' in query and len(query['filter']) > 0:
				filtered_symbols = list(filter(
					lambda sym: all([
						keyword in metadata[sym[:-3]]['keywords']
						for keyword in query['filter']
					]),
					filtered_symbols
				))

			self.send_response(200)
			self._cors_headers()
			self.send_header('Content-Type', 'application/json')
			self.end_headers()
			self.wfile.write(json.dumps(filtered_symbols).encode('utf-8'))
			return

		self.send_response(400)
		self.end_headers()
	
	def do_POST(self):
		url = urllib3.util.parse_url(self.path)
		query = urlparse.parse_qs(url.query)

		print(query)

		if url.path == '/convert':
			if self.headers.get_content_type() != 'image/svg+xml':
				self.send_response(400)
				self.send_header('Content-Type', 'text/plain')
				self._cors_headers()
				self.end_headers()
				self.wfile.write('Content type must equal to image/svg+xml'.encode('utf-8'))
				return

			self.send_symbol(self.rfile.read(int(self.headers.get('Content-Length'))), renderOptions(query))
			return

		self.send_response(400)
		self.end_headers()
	
	def send_symbol(self, symbol, options):
		if options['type'] == 'svg':
			content_type = 'image/svg+xml'
			body = symbol
		elif options['type'] == 'png':
			content_type = 'image/png'
			body = svg2png(
				symbol,
				output_width=options['size'],
				output_height=options['size'],
			)
		elif options['type'] == 'jpeg':
			content_type = 'image/jpeg'
			img_png = Image.open(BytesIO(svg2png(
				symbol,
				output_width=options['size'],
				output_height=options['size'],
			)))
			img = Image.new('RGBA', img_png.size, 'WHITE')
			img.paste(img_png, mask=img_png)
			body_jpeg = BytesIO()
			img.convert('RGB').save(body_jpeg, 'JPEG')
			body = body_jpeg.getvalue()
		else:
			self.send_response(400)
			self.send_header('Content-Type', 'text/plain')
			self._cors_headers()
			self.end_headers()
			self.wfile.write(f"Invalid render type: {options['type']}".encode('utf-8'))
			return

		self.send_response(200)
		self._cors_headers()
		self.send_header('Content-Type', content_type)
		self.end_headers()
		self.wfile.write(body)

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

def renderOptions(query):
	options = {
		'type': 'svg',
		'size': 512,
	}
	
	for opt in options.keys():
		if f'render_{opt}' in query:
			options[opt] = parseValue(query[f'render_{opt}'][0])

	return options

if __name__ == '__main__':
	main()
