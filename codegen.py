def mangle(name):  # _, $, ~
	return name.replace("_", "__").replace("$", "_D").replace("~", "_T")


def escape(name):  # "
	return name.replace("\\", "\\\\").replace('"', '\\"').replace('\n', '\\n')


class Generator:
	def __init__(self):
		self.instructions = []
		self.externs = {"ath_alloc"}
		self.provided = []
		self.strings = []
		self.blocks = []
		self.fieldids = set()
		self.lenvars = {}
		self.next_block = 0
		self.ctor = []
		self.data = []

	def string(self, string):
		if string not in self.strings:
			self.strings.append(string)
		return "string_%d ; %s" % (self.strings.index(string), escape(string))

	def line(self, line):
		self.instructions.append(line)

	def gen_alloc(self, lenvar, name, out=None):
		out = out or self.line
		out('\tmov eax, %s' % lenvar)
		out('\tcall ath_alloc')
		out('\tmov dword [eax], %s' % name)

	def process(self, cond, body, allocname):
		assert not self.blocks
		lenvar, name = self.build_block(cond, body)
		while self.blocks:
			self.gen_block(*self.blocks.pop())
		# self.ctor.append('%s:' % allocname)
		self.gen_alloc(lenvar, name, self.ctor.append)
		self.data += ["ctor_ptr_%s: dd 0" % mangle(allocname)]
		self.provided.append("ctor_ptr_%s" % mangle(allocname))
		self.ctor.append('\tmov [ctor_ptr_%s], eax' % mangle(allocname))

	# self.ctor.append('\tret')
	def putfield(self, source, srcreg, valreg):
		assert source != "SELF"
		self.fieldids.add(source)
		self.line("\tmov dword [%s+fid_%s], %s" % (srcreg, mangle(source), valreg))

	def getfield(self, source, srcreg, destreg):
		assert source != "SELF"
		self.fieldids.add(source)
		self.line("\tmov %s, dword [%s+fid_%s]" % (destreg, srcreg, mangle(source)))

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
					self.externs.add(ptr)
					self.line('\tmov eax, [%s]' % ptr)
					self.putfield("LOOKUP", "eax", self.string(stmt[2]))
					self.line('\tcall [eax]')
					self.getfield("EXPORT", "eax", "eax")
					self.putfield(stmt[2], "ebx", "eax")
				elif stmt[0] == "execute":
					self.gen_expr(stmt[1])
					self.line('\tpush eax')
					self.gen_expr(stmt[2])
					self.line('\tmov ecx, eax')
					self.line('\tpop eax')
					self.putfield("THIS", "eax", "ecx")
					self.line('\tcall [eax]')
				elif stmt[0] == "direct":
					self.gen_expr(stmt[1])
					self.line('\tcall [eax]')
				elif stmt[0] == "discard":
					self.gen_expr(stmt[1])
				elif stmt[0] == "put":
					self.gen_expr(stmt[2])
					self.putfield(stmt[1], "ebx", "eax")
				elif stmt[0] == "putref":  # object, field, value
					self.gen_expr(stmt[1])
					self.line('\tpush eax')
					self.gen_expr(stmt[3])
					self.line('\tpop ecx')
					self.putfield(stmt[2], "ecx", "eax")
				else:
					raise Exception("Internal error: unknown %s" % (stmt,))
			self.line('\tpop ebx')
			self.line('\tret')

	def build_block(self, cond, body):
		name, lenvar = self.anonymous_block()
		self.blocks.append((name, cond, body))
		assert lenvar not in self.lenvars
		self.lenvars[lenvar] = set(self.get_vars(body))
		return lenvar, name

	def anonymous_block(self):
		bid = self.next_block
		self.next_block += 1
		return "exec_%d" % bid, "bsize_%d" % bid

	arithmetic = ["add", "sub"]

	def gen_expr(self, expr):  # produces result in eax, SELF is in ebx (preserve)
		if expr[0] == "deref":
			self.gen_expr(expr[1])
			self.getfield(expr[2], "eax", "eax")
		elif expr[0] == "var":
			if expr[1] != "SELF":
				self.getfield(expr[1], "ebx", "eax")
			else:
				self.line('\tmov eax, ebx')
		elif expr[0] == "const":
			if type(expr[1]) == int:
				self.line('\tmov eax, %d' % expr[1])
			elif type(expr[1]) == str:
				self.line('\tmov eax, %s' % self.string(expr[1]))
		elif expr[0] == "tildeath":
			lenvar, name = self.build_block(expr[1], expr[2])
			self.gen_alloc(lenvar, name)
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
		byteval = [str(ord(x)) for x in string] + ["0"]
		return 'string_%d: db %s ; %s' % (i, ", ".join(byteval), escape(string))

	def basic_graph_color(self, vars, conflictmap, prealloced=None):
		colors = dict(prealloced) if prealloced else {}
		for v in vars:  # greedy algorithm
			if prealloced and v in prealloced: continue
			assert v not in colors
			existing = [colors[x] for x in conflictmap[v] if x in colors]
			color = min(x for x in range(len(existing) + 1) if x not in existing)
			colors[v] = color
		return colors

	def solve_variables(self, prealloced=None):
		conflicts = set()
		order_pair = lambda a, b: (min(a, b), max(a, b))
		conflictmap = {}
		for varset in self.lenvars.values():
			for var in varset:
				conflictmap[var] = set()  # to be used later
				for var2 in varset:
					conflicts.add(order_pair(var, var2))
		for a, b in conflicts:
			conflictmap[a].add(b)
			conflictmap[b].add(a)
		remaps = {}
		# find any locations where the conflict map of one entry is a subset (inclusive) of another entry
		for k1, m1 in conflictmap.items():
			for k2, m2 in conflictmap.items():
				if k1 == k2: continue
				if m1.issubset(m2) and k1 not in m2 and k2 not in m1:
					remaps[k1] = k2
					break
		for ent in tuple(remaps):
			if ent not in remaps: continue
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
		real_vars = set(conflictmap.keys()) - set(remaps.keys())
		new_prealloced = {}
		for key, value in prealloced.items():
			new_prealloced[remaps.get(key, key)] = value
		colors = self.basic_graph_color(real_vars, conflictmap, new_prealloced)
		for src, dst in remaps.items():
			colors[src] = colors[dst]
		return colors

	def solve_and_apply_variables(self, prealloced=None):
		colors = self.solve_variables(prealloced)
		for ent in self.fieldids:
			assert ent in colors, "ERROR: Never had a definition for field: %s" % ent  # Should be undefined behavior?
		lenvarout = {}
		for key, vars in self.lenvars.items():
			ids = [colors[x] for x in vars]
			assert len(ids) == len(set(ids)), "Somehow, an ID was duplicated in a block! Oops: %s => %s" % (vars, ids)
			words = 1  # for header
			words += max([0] + [1 + n for n in ids])  # add enough fields so that all of the fields have a place to go.
			lenvarout[key] = 4 * words
		return ["fid_%s equ %d" % (mangle(key), value) for key, value in colors.items()] + ["%s equ %d" % (key, value)
																							for key, value in
																							lenvarout.items()]

	def output(self, pretext=[], prealloced=None):
		out = self.solve_and_apply_variables(prealloced) + pretext
		if self.instructions or self.externs:
			out += ["section .text"] + ["extern %s" % x for x in self.externs if
										x not in self.provided] + self.instructions
		if self.strings:
			out += ["section .rodata"] + [self.string_define(i, string) for i, string in enumerate(self.strings)]
		if self.data:
			out += ["section .data"] + self.data
		if self.ctor:
			out += ["section .init"] + self.ctor
		return "\n".join(out)
