import sys

from codegen import Generator

from parser import parse

# object model:
# +0: fptr to EXECUTE target - must preserve ebx.
#     eax should be the object - must preserve.
# +4: byte for alive or not: 0 is dead, anything else is alive
# +5, +9, +13, ...: object fields
#     each field name has a globally-assigned index, which applies to any object that it is in.
#     this removes the need for runtime type checking
# IMPORT methods should preserve ebx, and return result in eax.
#     The object name will be provided in esi, and should be preserved.
# ath_alloc allocates 4*eax bytes, which it returns in eax.


def get_module_name(name):
	return ".".join(name.split(".")[:-1])

gen = Generator()
assert sys.argv[1:], "Expected arguments."

if len(sys.argv) < 2:
	print("no input files")
	sys.exit(1)

for file in sys.argv[1:]:
	with open(file, "r") as inp:
		gen.add_module(None, parse(inp), get_module_name(file))
print(gen.finish(get_module_name(sys.argv[1]), {"THIS": 0, "eax": 1, "ebx": 2, "ecx": 3, "edx": 4, "EXPORT": 5, "LOOKUP": 6, "write": 7, "DIE": 8}))
