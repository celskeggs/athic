def mangle(name):  # _, $, ~
	return name.replace("_", "__").replace("$", "_D").replace("~", "_T")


def escape(name):  # "
	return name.replace("\\", "\\\\").replace('"', '\\"').replace('\n', '\\n')


class Generator:
	def __init__(self):
		self.instructions = []
		self.externals = {"ath_alloc"}
		self.provided = []
		self.strings = []
		self.blocks = []
		self.field_ids = set()
		self.block_var_map = {}
		self.next_block = 0
		self.ctor = []
		self.data = []

	def string(self, string):
		if string not in self.strings:
			self.strings.append(string)
		return "string_%d ; %s" % (self.strings.index(string), escape(string))

	def line(self, line):
		self.instructions.append(line)

	def gen_alloc(self, length_info_ref, name, out=None):
		out = out or self.line
		out('\tmov eax, %s' % length_info_ref)
		out('\tcall ath_alloc')
		out('\tmov dword [eax], %s' % name)

	def process(self, cond, body, module_name):
		assert not self.blocks
		lenvar, name = self.build_block(cond, body)
		while self.blocks:
			self.gen_block(*self.blocks.pop())
		self.gen_alloc(lenvar, name, self.ctor.append)
		self.data += ["ctor_ptr_%s: dd 0" % mangle(module_name)]
		self.provided.append("ctor_ptr_%s" % mangle(module_name))
		self.ctor.append('\tmov [ctor_ptr_%s], eax' % mangle(module_name))

	def put_field(self, field, object_reg, source_reg):
		assert field != "SELF"
		self.field_ids.add(field)
		self.line("\tmov dword [%s+fid_%s], %s" % (object_reg, mangle(field), source_reg))

	def get_field(self, field, object_reg, dest_reg):
		assert field != "SELF"
		self.field_ids.add(field)
		self.line("\tmov %s, dword [%s+fid_%s]" % (dest_reg, object_reg, mangle(field)))

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
		self.line('%s:' % name)
		if type(block) == str:
			for line in str.split("\n"):
				self.line(line)
		else:
			self.line('\tpush ebx')
			self.line('\tmov ebx, eax')
			for stmt in block:
				if stmt[0] == "import":
					ptr = "ctor_ptr_%s" % mangle(stmt[1])
					self.externals.add(ptr)
					self.line('\tmov eax, [%s]' % ptr)
					self.put_field("LOOKUP", "eax", self.string(stmt[2]))
					self.line('\tcall [eax]')
					self.get_field("EXPORT", "eax", "eax")
					self.put_field(stmt[2], "ebx", "eax")
				elif stmt[0] == "execute":
					self.gen_expr(stmt[1])
					self.line('\tpush eax')
					self.gen_expr(stmt[2])
					self.line('\tmov ecx, eax')
					self.line('\tpop eax')
					self.put_field("THIS", "eax", "ecx")
					self.line('\tcall [eax]')
				elif stmt[0] == "direct":
					self.gen_expr(stmt[1])
					self.line('\tcall [eax]')
				elif stmt[0] == "discard":
					self.gen_expr(stmt[1])
				elif stmt[0] == "put":
					self.gen_expr(stmt[2])
					self.put_field(stmt[1], "ebx", "eax")
				elif stmt[0] == "putref":  # object, field, value
					self.gen_expr(stmt[1])
					self.line('\tpush eax')
					self.gen_expr(stmt[3])
					self.line('\tpop ecx')
					self.put_field(stmt[2], "ecx", "eax")
				else:
					raise Exception("Internal error: unknown %s" % (stmt,))
			self.line('\tpop ebx')
			self.line('\tret')

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
			self.get_field(expr[2], "eax", "eax")
		elif expr[0] == "var":
			if expr[1] != "SELF":
				self.get_field(expr[1], "ebx", "eax")
			else:
				self.line('\tmov eax, ebx')
		elif expr[0] == "const":
			if type(expr[1]) == int:
				self.line('\tmov eax, %d' % expr[1])
			elif type(expr[1]) == str:
				self.line('\tmov eax, %s' % self.string(expr[1]))
		elif expr[0] == "tildeath":
			length_info_ref, name = self.build_block(expr[1], expr[2])
			self.gen_alloc(length_info_ref, name)
		elif expr[0] in self.arithmetic:
			self.gen_expr(expr[1])
			self.line('\tpush eax')
			self.gen_expr(expr[2])
			self.line('\tmov ecx, eax')
			self.line('\tpop eax')
			self.line('\t%s eax, ecx' % expr[0])
		else:
			raise Exception("Internal error: unknown expr %s in %s" % (expr[0], expr[1:]))

	def string_define(self, i, string):
		byte_values = [str(ord(x)) for x in string] + ["0"]
		return 'string_%d: db %s ; %s' % (i, ", ".join(byte_values), escape(string))

	def basic_graph_color(self, variable_set, conflict_map, preallocated=None):
		colors = dict(preallocated) if preallocated else {}
		for v in variable_set:  # greedy algorithm
			if preallocated and v in preallocated:
				continue
			assert v not in colors
			existing = [colors[x] for x in conflict_map[v] if x in colors]
			color = min(x for x in range(len(existing) + 1) if x not in existing)
			colors[v] = color
		return colors

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

	def solve_variables(self, preallocated=None):
		conflict_map = self.calculate_conflict_map()
		remaps = {}
		# find any locations where the conflict map of one entry is a subset (inclusive) of another entry
		for k1, m1 in conflict_map.items():
			for k2, m2 in conflict_map.items():
				if k1 == k2:
					continue
				if m1.issubset(m2) and k1 not in m2 and k2 not in m1:
					remaps[k1] = k2
					break
		for ent in tuple(remaps):
			if ent not in remaps:
				continue
			target = remaps[ent]
			recent = []
			while target in remaps and target not in recent:
				recent.append(target)
				target = remaps[target]
			remaps[ent] = target
			if target in recent:  # we've got a loop. kill the loop. (we can kill it anywhere and it'll fix the problem.)
				del remaps[target]
		for ent in remaps:
			assert remaps[ent] not in remaps
		real_vars = set(conflict_map.keys()) - set(remaps.keys())
		new_preallocated = {}
		for key, value in preallocated.items():
			new_preallocated[remaps.get(key, key)] = value
		colors = self.basic_graph_color(real_vars, conflict_map, new_preallocated)
		for src, dst in remaps.items():
			colors[src] = colors[dst]
		return colors

	def solve_and_apply_variables(self, preallocated=None):
		colors = self.solve_variables(preallocated)
		for ent in self.field_ids:
			assert ent in colors, "ERROR: Never had a definition for field: %s" % ent  # Should be undefined behavior?
		block_length_map = {}
		for key, variables in self.block_var_map.items():
			ids = [colors[x] for x in variables]
			assert len(ids) == len(set(ids)), "Somehow, an ID was duplicated in a block! Oops: %s => %s" % (
				variables, ids)
			words = 1  # for header
			words += max([0] + [1 + n for n in ids])  # add enough fields so that all of the fields have a place to go.
			block_length_map[key] = 4 * words
		out = ["fid_%s equ %d" % (mangle(key), value) for key, value in colors.items()]
		out += ["%s equ %d" % (key, value) for key, value in block_length_map.items()]
		return out

	def output(self, pretext=(), preallocated=None):
		out = self.solve_and_apply_variables(preallocated) + list(pretext)
		if self.instructions or self.externals:
			out += ["section .text"]
			out += ["extern %s" % x for x in self.externals if x not in self.provided] + self.instructions
		if self.strings:
			out += ["section .rodata"] + [self.string_define(i, string) for i, string in enumerate(self.strings)]
		if self.data:
			out += ["section .data"] + self.data
		if self.ctor:
			out += ["section .init"] + self.ctor
		return "\n".join(out)
