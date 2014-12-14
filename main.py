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


gen = Generator()
assert sys.argv[1:], "Expected arguments."
for file in sys.argv[1:]:
	with open(file, "r") as inp:
		gen.add_module(None, parse(inp), ".".join(file.split(".")[:-1]))
print(gen.finish([], {"THIS": 0, "eax": 1, "ebx": 2, "ecx": 3, "edx": 4, "EXPORT": 5, "LOOKUP": 6, "write": 7, "DIE": 8}))
