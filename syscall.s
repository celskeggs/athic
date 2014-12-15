
section .data
global gate_ref
gate_ref: dd 0xBEEFD1E7

section .text

global _ath_load
global anonymous_mmap2

AT_NULL equ 0
AT_SYSINFO equ 32

_ath_load: ; replacement for _start - if you see an error that _start cannot be found - you're using the wrong linker script.
    mov ecx, [esp]
    lea eax, [esp+4*ecx+4]
    ; dword [eax] is now at the NULL at the end of the arguments
.skip_env_loop:
    add eax, 4
    cmp dword [eax], 0
    jne .skip_env_loop
    add eax, 4
.auxv_iter_loop:
    cmp dword [eax], AT_SYSINFO
    je .sysinfo_found
    add eax, 8
    cmp dword [eax-8], AT_NULL
    jne .auxv_iter_loop
    ; DID NOT FIND AT_SYSINFO ENTRY
    mov ecx, sysinfo_error_str
    mov edx, sysinfo_error_str_len
    jmp panic
.sysinfo_found:
    mov eax, [eax+4]
    mov [gate_ref], eax
    jmp _ath_load_2

PROT_READ equ 0x1
PROT_WRITE equ 0x2
PROT_EXEC equ 0x4

MAP_PRIVATE equ 0x02
MAP_ANONYMOUS equ 0x20

; assume to trash all registers
; args:
;         ecx = length, in 4096-byte pages
; return:
;         eax = offset
; does not return on failure
anonymous_mmap2:
    mov eax, 192
    mov ebx, 0 ; addr
    shl ecx, 12 ; length
    mov edx, PROT_READ | PROT_WRITE ; prot
    mov esi, MAP_PRIVATE | MAP_ANONYMOUS ; flags
    mov edi, -1 ; fd (IGNORED, but -1 suggested)
    mov ebp, 0 ; offset >> 12 (IGNORED)
    call dword [gate_ref]
    cmp eax, 4096
    jb mmap_panic
    ret
; recordings:
; eax            0xc0	    192        ; mmap_2 syscall
; ecx            0xcaca2222	-892722654 ; length
; edx            0xcaca3333	-892718285 ; prot
; ebx            0xcaca1111	-892727023 ; addr
; esp            0xffffd99c	0xffffd99c
; ebp            0xc6666	0xc6666    ; offset >> 12
; esi            0xcaca4444	-892713916 ; flags
; edi            0xcaca5555	-892709547 ; fd
; eip            0xf7eda611	0xf7eda611 <mmap+49>


mmap_panic:
    mov ecx, error_str
    mov edx, error_str_len
; set ecx to string, edx to length. does not return.
panic:
    mov eax, 4
    mov ebx, 2
    int 0x80
    mov eax, 0x01
    mov ebx, 0xCA
    int 0x80

section .rodata
sysinfo_error_str:
    db "AT_SYSINFO detect failure", 10
sysinfo_error_str_len equ $ - sysinfo_error_str
error_str:
    db "OOM mmap failure", 10
error_str_len equ $ - error_str
