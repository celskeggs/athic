OUTPUT_FORMAT("elf32-i386")
OUTPUT_ARCH(i386)
ENTRY(_ath_load)

SECTIONS
{
    . = 0x400000;

    .start : {
        core.o (.text);
        syscall.o (.text);
        alloc.o (.text);
    }

    .text : ALIGN(0x1000) {
        * (.text);
_ATH_INIT_START = .;
        * (.init);
        core.o (.init.end);
    }

    .data : ALIGN(0x1000) {
        * (.data);
    }

    .rodata : ALIGN(0x1000) {
        * (.rodata);
    }
}