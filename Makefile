allocator_test: allocator_test.o core.o alloc.o syscall.o
	ld -T ~ath.lds $< -o $@ -ggdb

.SECONDARY: allocator_test.s

%.o: %.s
	nasm $< -o $@ -f elf -ggdb

%.s: %.~ath main.py
	python main.py $< >$@

clean:
	rm -f *.o allocator_test.s allocator_test
