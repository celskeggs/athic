

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
				elif c in ";,.!=(){}-+@":
					yield (c, c)
				elif c == "`":
					mode = 2
					layers = 1
				elif c in " \t\r\n":
					pass
				elif c == "/" and line[0:1] == "/":
					if "\n" in line:
						line = line[line.index("\n"):]
					else:
						line = ''
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
					elif current == "~ATH":
						yield ("tildeath", current)
					elif current == "EXECUTE":
						yield ("execute", current)
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

	operators = {1: ".", 3: "+-"}
	unary_ops = {2: "@"}
	arith_map = {"+": "add", "-": "sub"}

	def produce_operator(self, a, operator, prec):
		if operator == ".":
			b = self.expect("symbol")
			return ("deref", a, b)
		elif operator in "+-":
			b = self.parse_expression(prec - 1)
			return (self.arith_map[operator], a, b)
		else:
			raise Exception("Internal error: unexpected %s" % (operator,))

	def produce_operator_unary(self, operator, expr):
		if operator == "@":
			return ("unptr", expr)
		else:
			raise Exception("Internal error: unexpected %s" % (operator,))

	def parse_expression(self, prec=max(operators.keys())):
		if prec <= 0:  # simple term
			if self.accept("symbol"):
				return ("var", self.last_value)
			elif self.accept("integer"):
				return ("const", self.last_value)
			elif self.accept("string"):
				return ("const", self.last_value)
			elif self.accept("tildeath"):
				condition = self.parse_expression()
				self.expect("{")
				body = self.parse_block("}")
				return ("tildeath", condition, body)
			else:
				self.expect("(")
				out = self.parse_expression()
				self.expect(")")
				return out
		else:
			uops = []
			while self.accept_any(self.unary_ops.get(prec, ())):
				uops.append(self.last_token)
			head = self.parse_expression(prec - 1)
			uops.reverse()
			for op in uops:
				head = self.produce_operator_unary(op, head)
			while self.accept_any(self.operators.get(prec, ())):
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
			if self.accept("execute"):
				arg = self.parse_expression()
				self.expect(";")
				return ("execute", expr, arg)
			elif self.accept("("):
				self.expect(")")
				self.expect(";")
				return ("direct", expr)
			elif expr[0] == "var" and self.accept("="):
				arg = self.parse_expression()
				self.expect(";")
				return ("put", expr[1], arg)
			elif expr[0] == "deref" and self.accept("="):
				arg = self.parse_expression()
				self.expect(";")
				return ("putref", expr[1], expr[2], arg)
			else:
				self.expect(";")
				return ("discard", expr)

	def parse_block(self, end="eof"):
		out = []
		while not self.accept(end):
			out.append(self.parse_statement())
		return out

	def parse(self):
		out = self.parse_block()
		self.expect("eof")
		return out


def parse(inp):
	return Parser(tokenize(inp)).parse()
