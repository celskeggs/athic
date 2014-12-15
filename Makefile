test: core.o alloc.o syscall.o
	ld -T ~ath.lds -o $@

%.o: %.s
	nasm $< -o $@ -f elf

clean:
	rm core.o alloc.o syscall.o