python main.py example.~ath ostream.~ath >out.s && nasm -f elf out.s && nasm -f elf core.s && ld -melf_i386 out.o core.o
