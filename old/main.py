import sys

def tokenize(producer):
	mode = 0
	current = None
	layers, active = None, None
	for line in producer:
		while line:
			c, line = line[0], line[1:]
			if mode == 0:
				if c.isalnum() or c in "_$~":
					mode = 1
					current = c
				elif c in ";,.!()":
					yield (c, c)
				elif c == "`":
					mode = 2
					layers = 1
				elif c in " \t\r\n":
					pass
				else:
					raise Exception("Unexpected: " + c)
			elif mode == 1:
				if c.isalnum() or c in "_$~":
					current += c
				else:
					if current.isdigit() or (current[0] == "-" and current[1:].isdigit()):
						yield ("integer", int(current))
					elif current == "import":
						yield ("import", current)
					else:
						yield ("symbol", current)
					current = None
					mode = 0
					line = c + line
			elif mode == 2:
				if c == "`":
					layers += 1
				elif c == "'" and layers == 1:
					yield ("string", '')
					layers = None
					mode = 0
				else:
					current = c
					active = 0
					mode = 3
			elif mode == 3:
				if c == "'":
					active += 1
					if active >= layers:
						yield ("string", current)
						layers, current, active = None, None, None
						mode = 0
				else:
					if active:
						current += "'" * active
						active = 0
					current += c
			else:
				raise Exception("Bad state: %d" % mode)
class Parser:
	next_token = None
	last_value = None
	last_token = None
	def __init__(self, tokens):
		self.tokensource = tokens
	def consume(self):
		self.last_token, self.last_value = self.next_token
		self.next_token = None
	def token(self):
		if self.next_token == None:
			try:
				self.next_token = next(self.tokensource)
			except StopIteration:
				self.next_token = ("eof", None)
		return self.next_token[0]
	def accept(self, token):
		if token == self.token():
			self.consume()
			return True
		return False
	def accept_any(self, tokens):
		if self.token() in tokens:
			self.consume()
			return True
		return False
	def expect(self, token):
		assert self.accept(token), "Expected token %s but got %s" % (token, self.token())
		return self.last_value
	operators = {1: ".", 2: "("}
	def produce_operator(self, a, operator, prec):
		if operator == ".":
			#b = self.parse_expression(prec - 1)
			b = self.expect("symbol")
			return ("deref", a, b)
		elif operator == "(":
			args = []
			if not self.accept(")"):
				while True:
					args.append(self.parse_expression())
					if not self.accept(","):
						break
				self.expect(")")
			return ("call", a) + tuple(args)
		else:
			raise Exception("Internal error: unexpected " + operator)
	def parse_expression(self, prec=2):
		if prec <= 0: # simple term
			if self.accept("symbol"):
				return ("var", self.last_value)
			elif self.accept("integer"):
				return ("const", self.last_value)
			else:
				self.expect("string")
				return ("const", self.last_value)
		else:
			head = self.parse_expression(prec - 1)
			while self.accept_any(self.operators[prec]):
				operator = self.last_token
				head = self.produce_operator(head, operator, prec)
			return head
	def parse_statement(self):
		if self.accept("import"):
			typename = self.expect("symbol")
			objname = self.expect("symbol");
			self.expect(";")
			return ("import", typename, objname)
		else:
			expr = self.parse_expression()
			out = ("discard", expr)
			self.expect(";")
			return out
	def parse_block(self):
		out = []
		while not self.accept("eof"):
			out.append(self.parse_statement())
		return out
	def parse(self):
		out = self.parse_block()
		self.expect("eof")
		return out
def parse(tokens):
	return Parser(tokens).parse()
def mangle(name): # _, $, ~
	return name.replace("_", "__").replace("$", "_D").replace("~", "_T")
def escape(name): # "
	return name.replace("\\", "\\\\").replace('"', '\\"').replace('\n', '\\n')
def generate_expr(expr):
	if expr[0] == "call":
		return "invoke(%d, %s, (AO[]) {%s})" % (len(expr[2:]), generate_expr(expr[1]), ", ".join(generate_expr(e) for e in expr[2:]))
	elif expr[0] == "deref":
		return 'deref(%s, "%s")' % (generate_expr(expr[1]), escape(expr[2]))
	elif expr[0] == "var":
		if expr[1] == "THIS":
			return 'aththis()'
		return mangle(expr[1])
	elif expr[0] == "const":
		return "athint(%d)" % expr[1] if type(expr[1]) == int else 'athstr("%s")' % escape(expr[1])
	else:
		raise Exception("Internal error: unknown expr %s" % expr[0])
def generate(tree):
	out = []
	p = out.append
	p('#include "~ath.h"')
	p("void athmain() {")
	# [('import', 'ostream', 'stdout'), ('discard', ('call', ('deref', ('var', 'stdout'), 'write'), ('const', 'Hello, World.'))), ('discard', ('call', ('deref', ('var', 'THIS'), 'DIE')))]
	for stmt in tree:
		if stmt[0] == "import":
			p('\tAO %s = import("%s", "%s");' % (mangle(stmt[2]), escape(stmt[1]), escape(stmt[2])))
		elif stmt[0] == "discard":
			p('\t%s;' % generate_expr(stmt[1]))
		else:
			raise Exception("Internal error: unknown %s" % stmt)
	p("}")
	return "\n".join(out)
#with open("example.~ath", "r") as fin:
#	print(*tokenize(fin))
#with open("example.~ath", "r") as fin:
#	print(parse(tokenize(fin)))
with open("example.~ath", "r") as fin:
	print(generate(parse(tokenize(fin))))

