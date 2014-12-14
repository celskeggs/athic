from graph_coloring import color_graph


def mangle_char(c):
	if c.isalnum() or c == ".":
		return c
	elif c == "_":
		return "__"
	else:
		return "_%x" % ord(c)


def mangle(name):  # _, $, ~
	return "".join(map(mangle_char, name))


def escape(name):  # "
	return name.replace("\\", "\\\\").replace('"', '\\"').replace('\n', '\\n')

eax, ebx, ecx, edx = "eax", "ebx", "ecx", "edx"
edi, esi, esp, ebp = "edi", "esi", "esp", "ebp"


class InstructionOutput:
	def __init__(self):
		self.buffer = []

	def raw(self, line):
		self.buffer.append(line)

	def add_from(self, instr):
		self.buffer += instr.get()

	def mov(self, dst, src):
		self.raw("\tmov %s, %s" % (dst, src))

	def get(self):
		return self.buffer

	def put_dword(self, dst, field, src):
		self.mov("dword [%s+%s]" % (dst, field), src)

	def get_dword(self, dst, src, field):
		self.mov(dst, "dword [%s+%s]" % (src, field))

	def label(self, name):
		self.raw("%s:" % name)

	def call(self, param):
		self.raw("\tcall %s" % param)

	def push(self, param):
		self.raw("\tpush %s" % param)

	def pop(self, param):
		self.raw("\tpop %s" % param)

	def ret(self):
		self.raw('\tret')


class FieldOutput(InstructionOutput):
	def __init__(self):
		InstructionOutput.__init__(self)
		self.field_ids = set()

	def field_ref(self, field):
		assert field != "SELF"
		self.field_ids.add(field)
		return "fid_%s" % mangle(field)

	def put_field(self, field, object_reg, source_reg):
		self.put_dword(object_reg, self.field_ref(field), source_reg)

	def get_field(self, field, object_reg, dst_reg):
		self.get_dword(dst_reg, object_reg, self.field_ref(field))


class Generator:
	def __init__(self):
		self.out = FieldOutput()
		self.externals = {"ath_alloc"}
		self.provided = []
		self.string_set = set()
		self.blocks = []
		self.block_var_map = {}
		self.next_block = 0
		self.ctor = InstructionOutput()
		self.data = []

	def string(self, string):
		self.string_set.add(string)
		return "string_" + mangle(string)

	def gen_alloc(self, length_info_ref, name, out=None):
		out = out or self.out
		out.mov(eax, length_info_ref)
		out.call("ath_alloc")
		out.mov("dword [eax]", name)

	def process(self, cond, body, module_name):
		assert not self.blocks
		length_info_ref, name = self.build_block(cond, body)
		while self.blocks:
			self.gen_block(*self.blocks.pop())
		self.gen_alloc(length_info_ref, name, self.ctor)
		self.data += ["ctor_ptr_%s: dd 0" % mangle(module_name)]
		self.provided.append("ctor_ptr_%s" % mangle(module_name))
		self.ctor.mov("[ctor_ptr_%s]" % mangle(module_name), eax)

	def get_expr_vars(self, expr):
		if expr[0] == "deref":
			if expr[1][0] == "var" and expr[1][1] == "SELF":
				return [expr[2]]
			else:
				return self.get_expr_vars(expr[1])
		elif expr[0] == "var":
			if expr[1] != "SELF":
				return [expr[1]]
			else:
				return []
		elif expr[0] == "const":
			return []
		elif expr[0] == "tildeath":
			return []
		elif expr[0] in self.arithmetic:
			return self.get_expr_vars(expr[1]) + self.get_expr_vars(expr[1])
		else:
			raise Exception("Internal error: unknown expr %s in %s" % (expr[0], expr[1:]))

	def get_vars(self, block):
		found = []
		for stmt in block:
			if stmt[0] == "import":
				found.append(stmt[2])
			elif stmt[0] == "execute":
				found += self.get_expr_vars(stmt[1])
				found += self.get_expr_vars(stmt[2])
			elif stmt[0] == "direct":
				found += self.get_expr_vars(stmt[1])
			elif stmt[0] == "discard":
				found += self.get_expr_vars(stmt[1])
			elif stmt[0] == "put":
				found += self.get_expr_vars(stmt[2])
				found.append(stmt[1])
			elif stmt[0] == "putref":
				if stmt[1][0] == "var" and stmt[1][1] == "SELF":
					found.append(stmt[2])
				found += self.get_expr_vars(stmt[1])
				found += self.get_expr_vars(stmt[3])
			else:
				raise Exception("Internal error: unknown stmt %s" % (stmt,))
		return found

	def gen_block(self, name, cond, block):
		self.out.label(name)
		if type(block) == str:
			for line in str.split("\n"):
				self.out.raw(line)
		else:
			self.out.push(ebx)
			self.out.mov(ebx, eax)
			for stmt in block:
				if stmt[0] == "import":
					ptr = "ctor_ptr_%s" % mangle(stmt[1])
					self.externals.add(ptr)
					self.out.mov(eax, "[%s]" % ptr)
					self.out.put_field("LOOKUP", eax, self.string(stmt[2]))
					self.out.call("[eax]")
					self.out.get_field("EXPORT", eax, eax)
					self.out.put_field(stmt[2], ebx, eax)
				elif stmt[0] == "execute":
					self.gen_expr(stmt[1])
					self.out.push(eax)
					self.gen_expr(stmt[2])
					self.out.mov(ecx, eax)
					self.out.pop(eax)
					self.out.put_field("THIS", eax, ecx)
					self.out.call("[eax]")
				elif stmt[0] == "direct":
					self.gen_expr(stmt[1])
					self.out.call("[eax]")
				elif stmt[0] == "discard":
					self.gen_expr(stmt[1])
				elif stmt[0] == "put":
					self.gen_expr(stmt[2])
					self.out.put_field(stmt[1], ebx, eax)
				elif stmt[0] == "putref":  # object, field, value
					self.gen_expr(stmt[1])
					self.out.push(eax)
					self.gen_expr(stmt[3])
					self.out.pop(ecx)
					self.out.put_field(stmt[2], ecx, eax)
				else:
					raise Exception("Internal error: unknown %s" % (stmt,))
			self.out.pop(ebx)
			self.out.ret()

	def build_block(self, cond, body):
		name, lenvar = self.anonymous_block()
		self.blocks.append((name, cond, body))
		assert lenvar not in self.block_var_map
		self.block_var_map[lenvar] = set(self.get_vars(body))
		return lenvar, name

	def anonymous_block(self):
		bid = self.next_block
		self.next_block += 1
		return "exec_%d" % bid, "bsize_%d" % bid

	arithmetic = ["add", "sub"]

	def gen_expr(self, expr):  # produces result in eax, SELF is in ebx (preserve)
		if expr[0] == "deref":
			self.gen_expr(expr[1])
			self.out.get_field(expr[2], "eax", "eax")
		elif expr[0] == "var":
			if expr[1] != "SELF":
				self.out.get_field(expr[1], "ebx", "eax")
			else:
				self.out.mov(eax, ebx)
		elif expr[0] == "const":
			if type(expr[1]) == int:
				self.out.mov(eax, expr[1])
			elif type(expr[1]) == str:
				self.out.mov(eax, self.string(expr[1]))
		elif expr[0] == "tildeath":
			length_info_ref, name = self.build_block(expr[1], expr[2])
			self.gen_alloc(length_info_ref, name)
		elif expr[0] in self.arithmetic:
			self.gen_expr(expr[1])
			self.out.push(eax)
			self.gen_expr(expr[2])
			self.out.mov(ecx, eax)
			self.out.pop(eax)
			self.out.raw('\t%s eax, ecx' % expr[0])
		else:
			raise Exception("Internal error: unknown expr %s in %s" % (expr[0], expr[1:]))

	def string_define(self, string):
		byte_values = [str(ord(x)) for x in string] + ["0"]
		return 'string_%s: db %s ; %s' % (mangle(string), ", ".join(byte_values), escape(string))

	def calculate_conflict_map(self):
		variables = set()
		for var_set in self.block_var_map.values():
			variables.update(var_set)
		conflict_map = {}
		for var1 in variables:
			conflict_map[var1] = set()
		for block_vars in self.block_var_map.values():
			for var1 in block_vars:
				for var2 in block_vars:
					if var1 != var2:
						conflict_map[var1].add(var2)
		return conflict_map

	def solve_and_apply_variables(self, forced=None):
		colors = color_graph(self.calculate_conflict_map(), forced or {})
		for ent in self.out.field_ids:
			assert ent in colors, "ERROR: Never had a definition for field: %s" % ent  # Should be undefined behavior?
		block_length_map = {}
		for key, variables in self.block_var_map.items():
			ids = [colors[x] for x in variables]
			assert len(ids) == len(set(ids)), "Somehow, an ID was duplicated in a block! Oops: %s => %s" % (
				variables, ids)
			words = 1  # for header
			words += max([0] + [1 + n for n in ids])  # add enough fields so that all of the fields have a place to go.
			block_length_map[key] = 4 * words
		out = ["%s equ %d" % (self.out.field_ref(key), value) for key, value in colors.items()]
		out += ["%s equ %d" % (key, value) for key, value in block_length_map.items()]
		return out

	def output(self, pretext=(), preallocated=None):
		out = self.solve_and_apply_variables(preallocated) + list(pretext)
		if self.out.get() or self.externals:
			out += ["section .text"]
			out += ["extern %s" % x for x in self.externals if x not in self.provided] + self.out.get()
		if self.string_set:
			out += ["section .rodata"] + [self.string_define(string) for string in self.string_set]
		if self.data:
			out += ["section .data"] + self.data
		if self.ctor.get():
			out += ["section .init"] + self.ctor.get()
		return "\n".join(out)
