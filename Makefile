allocator_test: allocator_test.o core.o alloc.o syscall.o
	ld -T ~ath.lds $< -o $@ -ggdb

.SECONDARY: *.s

%.o: %.s
	nasm $< -o $@ -f elf -ggdb

%.s: %.~ath
	python main.py $< >$@

clean:
	rm *.o