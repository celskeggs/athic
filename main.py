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
				elif c in ";,.!=(){}":
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
	operators = {1: "."}
	def produce_operator(self, a, operator, prec):
		if operator == ".":
			#b = self.parse_expression(prec - 1)
			b = self.expect("symbol")
			return ("deref", a, b)
		else:
			raise Exception("Internal error: unexpected " + operator)
	def parse_expression(self, prec=1):
		if prec <= 0: # simple term
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
def parse(tokens):
	return Parser(tokens).parse()
def mangle(name): # _, $, ~
	return name.replace("_", "__").replace("$", "_D").replace("~", "_T")
def escape(name): # "
	return name.replace("\\", "\\\\").replace('"', '\\"').replace('\n', '\\n')
class Generator:
	def __init__(self):
		self.instructions = []
		self.externs = set()
		self.strings = []
		self.blocks = []
		self.next_block = 0
	def string(self, string):
		if string not in self.strings:
			self.strings.append(string)
		return "string_%d ; %s" % (self.strings.index(string), escape(string))
	def line(self, line):
		self.instructions.append(line)
	def add_block(self, name, cond, block):
		self.blocks.append((name, None, block))
	def process(self, name, block):
		assert not self.blocks
		self.add_block(name, block)
		while self.blocks:
			self.gen_block(*self.blocks.pop())
	def gen_block(self, name, cond, block):
		self.line('%s:' % name)
		if type(block) == str:
			for line in str.split("\n"):
				self.line(line)
		else:
			self.line('\tpush ebx')
			self.line('\tmov ebx, eax')
			for stmt in block:
				if stmt[0] == "import":
					self.line("\tmov esi, %s" % self.string(stmt[2]))
					importee = 'import_%s' % mangle(stmt[1])
					self.externs.add(importee)
					self.line('\tcall %s' % importee)
					self.line('\tmov eax, ebx')
					# esi is preserved through import_*.
					self.line('\tcall [eax+8]')
				elif stmt[0] == "execute":
					self.gen_expr(stmt[1])
					self.line('\tpush eax')
					self.gen_expr(stmt[2])
					self.line('\tmov ecx, eax')
					self.line('\tpop eax')
					self.line('\tmov esi, %s' % self.string("THIS"))
					self.line('\tcall [eax+8]')
					self.line('\tcall [eax]')
				elif stmt[0] == "direct":
					self.gen_expr(stmt[1])
					self.line('\tcall [eax]')
				elif stmt[0] == "discard":
					self.gen_expr(stmt[1])
				elif stmt[0] == "put":
					self.gen_expr(stmt[2])
					self.line('\tmov eax, ebx')
					self.line('\tmov esi, %s' % self.string(stmt[1]))
					self.line('\tcall [eax+8]')
				else:
					raise Exception("Internal error: unknown %s" % (stmt,))
			self.line('\tpop ebx')
			self.line('\tret')
	def anonymous_block(self):
		bid = self.next_block
		self.next_block += 1
		return ".exec_%d" % bid, ".get_%d" % bid, ".put_%d" % bid
	def gen_expr(self, expr): # produces result in eax, SELF is in ebx (preserve)
		if expr[0] == "deref":
			self.gen_expr(expr[1])
			self.line('\tmov esi, %s' % self.string(expr[2]))
			self.line('\tcall [eax+4]')
		elif expr[0] == "var":
			self.line('\tmov eax, ebx')
			if expr[1] != "SELF":
				self.line('\tmov esi, %s' % self.string(expr[1]))
				self.line('\tcall [eax+4]')
		elif expr[0] == "const":
			if type(expr[1]) == int:
				self.line('\tmov eax, %d' % expr[1])
			elif type(expr[1]) == str:
				self.line('\tmov eax, %s' % self.string(expr[1]))
		elif expr[0] == "tildeath":
			ex, get, put = self.anonymous_block()
			self.add_block(ex, expr[1], expr[2])
			varnames = self.get_vars(expr[2])
			get_code, put_code = self.generate_get_put_code(varnames)
			self.add_block(get, None, get_code)
			self.add_block(put, None, put_code)
			self.line('\tmov eax, %d' % (self.get_vars(expr[2]) + 3)) # three entries from object model plus one entry per variable.
			self.line('\tcall ath_alloc')
			self.line('\tmov [ecx+0], %s' % ex)
			self.line('\tmov [ecx+4], %s' % get)
			self.line('\tmov [ecx+8], %s' % put)
		else:
			raise Exception("Internal error: unknown expr %s in %s" % (expr[0], expr[1:]))
	def generate_get_put_code(self, varnames):
		get, put = [""], [""]
		WORKING HERE...
		return "\n".join(get), "\n".join(put)
	def string_define(self, i, string):
		byteval = [str(ord(x)) for x in string] + ["0"]
		return 'string_%d: db %s ; %s' % (i, ", ".join(byteval), escape(string))
	def output(self):
		out = ["section .text"] + ["extern %s" % x for x in self.externs] + self.instructions + ["section .rodata"] + [self.string_define(i, string) for i, string in enumerate(self.strings)]
		return "\n".join(out)
# object model:
# +0: fptr to EXECUTE target - must preserve ebx.
#     eax should be the object - must preserve.
# +4: fptr to DEREF-GET target - must preserve ebx.
#     eax should be the object - not preserved
#     esi should point to the deref name.
#     return result in eax
# +8: fptr to DEREF-PUT target - must preserve ebx.
#     eax should be the object - must preserve.
#     esi should point to the deref name.
#     ecx should be the new value.
# IMPORT methods should preserve ebx, and return result in eax. The object name will be provided in esi, and should be preserved.
# ath_alloc allocates 4*eax bytes, which it returns in eax.
def generate(block):
	gen = Generator()
	gen.process("ath_main", block)
	return gen.output()
#with open("example.~ath", "r") as fin:
print(generate(parse(tokenize(sys.stdin))))

