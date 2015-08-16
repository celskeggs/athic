OUTPUT_FORMAT("elf32-i386")
OUTPUT_ARCH(i386)
ENTRY(_ath_load)

SECTIONS
{
	. = 0x08048000;

    .start : {
        core.o (.text);
        syscall.o (.text);
        alloc.o (.text);
    }

    .text : {
        * (.text);
_ATH_INIT_START = .;
        * (.init);
        core.o (.init.end);
    }

    .data : {
        * (.data);
    }

    .rodata : {
        * (.rodata);
    }
}
