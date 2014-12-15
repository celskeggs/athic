from graph_coloring import color_graph

import math


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
arithmetic = ["add", "sub"]


class InstructionOutput:
	def __init__(self):
		self.buffer = []

	def raw(self, line):
		self.buffer.append(line)

	def add_from(self, instr):
		self.buffer += instr.get()

	def mov(self, dst, src):
		self.raw("\tmov %s, %s" % (dst, src))

	def movzx(self, dst, src):
		self.raw("\tmovzx %s, %s" % (dst, src))

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

	def jmp(self, name):
		self.raw('\tjmp %s' % name)

	def cmp(self, a, b):
		self.raw('\tcmp %s, %s' % (a, b))

	def je(self, target):
		self.raw("\tje %s" % target)

	def jne(self, target):
		self.raw("\tjne %s" % target)

	def jb(self, target):
		self.raw("\tjb %s" % target)


class FieldOutput(InstructionOutput):
	def __init__(self):
		InstructionOutput.__init__(self)
		self.field_set = set()
		self.local_vars = None

	def field_ref(self, field):
		assert field != "SELF"
		self.field_set.add(field)
		return "fid_%s" % mangle(field)

	def put_field(self, field, object_reg, source_reg):
		self.put_dword(object_reg, "5+4*" + self.field_ref(field), source_reg)

	def get_field(self, field, object_reg, dst_reg):
		self.get_dword(dst_reg, object_reg, "5+4*" + self.field_ref(field))

	def reset_local_vars(self):
		self.local_vars = set()

	def put_self_field(self, field, source_reg):
		self.local_vars.add(field)
		self.put_field(field, ebx, source_reg)

	def get_self_field(self, field, dst_reg):
		self.local_vars.add(field)
		self.get_field(field, ebx, dst_reg)

	def get_local_vars(self):
		out = self.local_vars
		self.local_vars = None
		return out


class ObjectOutput(InstructionOutput):
	def __init__(self):
		InstructionOutput.__init__(self)

	def gen_alloc(self, length, name):
		self.mov(ecx, length)
		self.call("ath_alloc")
		self.mov("dword [eax]", name)
		self.set_alive(eax)

	def jump_alive(self, target):  # if object in eax is alive, jump to target
		self.cmp(eax, 256)
		self.jb(target)
		self.cmp("byte [eax+4]", 0)
		self.jne(target)

	def set_alive(self, target):
		self.mov("byte [%s+4]" % target, 1)

	def set_dead(self, target):
		self.mov("byte [%s+4]" % target, 0)


class StringOutput(InstructionOutput):
	def __init__(self):
		InstructionOutput.__init__(self)
		self.string_set = set()

	def string(self, string):
		self.string_set.add(string)
		return "string_" + mangle(string)


class TreeOutput(FieldOutput, StringOutput, ObjectOutput):
	def __init__(self, loop_build_callback):
		FieldOutput.__init__(self)
		StringOutput.__init__(self)
		ObjectOutput.__init__(self)
		self.loop_build_callback = loop_build_callback
		self.external_refs = {"ath_alloc"}

	def get_external_refs(self):
		return self.external_refs

	def gen_expr(self, expr):  # produces result in eax, SELF is in ebx (preserve)
		if expr[0] == "deref":
			if expr[1] == ("var", "SELF"):
				self.get_self_field(expr[2], eax)
			else:
				self.gen_expr(expr[1])
				self.get_field(expr[2], eax, eax)
		elif expr[0] == "var":
			if expr[1] != "SELF":
				self.get_self_field(expr[1], eax)
			else:
				self.mov(eax, ebx)
		elif expr[0] == "const":
			if type(expr[1]) == int:
				self.mov(eax, expr[1])
			elif type(expr[1]) == str:
				self.mov(eax, self.string(expr[1]))
		elif expr[0] == "tildeath":
			length, name = self.loop_build_callback(expr[1], expr[2])
			self.gen_alloc(length, name)
		elif expr[0] == "unptr":
			self.gen_expr(expr[1])
			self.movzx(eax, "byte [eax]")
		elif expr[0] in arithmetic:
			self.gen_expr(expr[1])
			self.push(eax)
			self.gen_expr(expr[2])
			self.mov(ecx, eax)
			self.pop(eax)
			self.raw('\t%s eax, ecx' % expr[0])
		else:
			raise Exception("Internal error: unknown expr %s with %s" % (expr[0], expr[1:]))

	def gen_stmt(self, stmt):
		if stmt[0] == "import":
			ptr = "ctor_ptr_%s" % mangle(stmt[1])
			self.external_refs.add(ptr)
			self.mov(eax, "[%s]" % ptr)
			self.put_field("LOOKUP", eax, self.string(stmt[2]))
			self.call("[eax]")
			self.get_field("EXPORT", eax, eax)
			self.put_self_field(stmt[2], eax)
		elif stmt[0] == "execute":
			self.gen_expr(stmt[1])
			self.push(eax)
			self.gen_expr(stmt[2])
			self.mov(ecx, eax)
			self.pop(eax)
			self.put_field("THIS", eax, ecx)
			self.call("[eax]")
		elif stmt[0] == "direct":
			self.gen_expr(stmt[1])
			self.call("[eax]")
		elif stmt[0] == "discard":
			self.gen_expr(stmt[1])
		elif stmt[0] == "put":
			self.gen_expr(stmt[2])
			self.put_self_field(stmt[1], eax)
		elif stmt[0] == "putref":  # object, field, value
			if stmt[1] == ("var", "SELF"):
				self.gen_expr(stmt[3])
				self.put_self_field(stmt[2], eax)
			else:
				self.gen_expr(stmt[1])
				self.push(eax)
				self.gen_expr(stmt[3])
				self.pop(ecx)
				self.put_field(stmt[2], ecx, eax)
		else:
			raise Exception("Internal error: unknown %s" % (stmt,))

	def gen_block(self, name, cond, body):
		self.label(name)
		self.push(ebx)
		self.mov(ebx, eax)
		self.set_alive(eax)

		if cond:
			self.jmp(".loop_check")

			self.label(".loop_top")
			for stmt in body:
				self.gen_stmt(stmt)

			self.label(".loop_check")
			self.gen_expr(cond)
			self.jump_alive(".loop_top")
		else:
			for stmt in body:
				self.gen_stmt(stmt)

		self.set_dead(ebx)
		self.pop(ebx)
		self.ret()


class Generator:
	def __init__(self):
		self.out = TreeOutput(self.build_block)
		self.ctor = TreeOutput(self.build_block)
		self.provided = []
		self.blocks = []
		self.block_var_map = {}
		self.next_block = 0
		self.data = []

	def add_module(self, cond, body, module_name):
		length_ref, name = self.build_block(cond, body)
		self.ctor.gen_alloc(length_ref, name)
		self.data += ["global ctor_ptr_%s" % mangle(module_name)]
		self.data += ["ctor_ptr_%s: dd 0" % mangle(module_name)]
		self.provided.append("ctor_ptr_%s" % mangle(module_name))
		self.ctor.mov("[ctor_ptr_%s]" % mangle(module_name), eax)

	def gen_block(self, name, length_ref, cond, body):
		self.out.reset_local_vars()

		self.out.gen_block(name, cond, body)

		assert length_ref not in self.block_var_map
		self.block_var_map[length_ref] = self.out.get_local_vars()

	def build_block(self, cond, body):
		name, length_ref = self.anonymous_block()
		self.blocks.append((name, length_ref, cond, body))
		return length_ref, name

	def anonymous_block(self):
		bid = self.next_block
		self.next_block += 1
		return "exec_%d" % bid, "bsize_%d" % bid

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
		for ent in self.out.field_set:
			assert ent in colors, "ERROR: Never had a definition for field: %s" % ent  # Should be undefined behavior?
		block_length_map = {}
		for key, variables in self.block_var_map.items():
			ids = [colors[x] for x in variables]
			assert len(ids) == len(set(ids)), "Somehow, an ID was duplicated in a block! Oops: %s => %s" % (
				variables, ids)
			words = max([0] + [1 + n for n in ids])  # add enough fields so that all of the fields have a place to go.
			block_length_map[key] = words
		out = ["%s equ %d" % (self.out.field_ref(key), value) for key, value in colors.items()]
		out += ["%s equ %d" % (key, value) for key, value in block_length_map.items()]
		return out, max(block_length_map.values())

	def finish(self, main_module=None, preallocated=None):
		while self.blocks:
			self.gen_block(*self.blocks.pop())
		out, max_length = self.solve_and_apply_variables(preallocated)
		max_length = max(max_length, 6)
		out += ["global max_alloc_size", "max_alloc_size equ %d" % max_length]
		out += ["global max_alloc_size_in_pages", "max_alloc_size_in_pages equ %d" % math.ceil(4 * (max_length + 1) / 4096.0)]
		if self.out.get() or self.out.get_external_refs():
			out += ["section .text"]
			out += ["extern %s" % x for x in self.out.get_external_refs() if x not in self.provided] + self.out.get()
		if self.out.string_set:
			out += ["section .rodata"] + [self.string_define(string) for string in self.out.string_set]
			out
		if self.data:
			out += ["section .data"] + self.data
			if main_module:
				out += ["global main_ptr", "main_ptr equ ctor_ptr_%s" % mangle(main_module)]
		if self.ctor.get():
			out += ["section .init"] + self.ctor.get()
		return "\n".join(out)
