
;extern ath_alloc
ath_alloc equ mmap_panic
extern anonymous_mmap2
extern mmap_panic

section .text
extern main_ptr

global _ath_load_2
extern _ATH_INIT_START
extern _ath_alloc_init

_ath_load_2:

    call _ath_alloc_init

    call _ATH_INIT_START

    ;mov eax, [main_ptr]
    mov dword [eax+29], string_main
    call [eax]
    mov eax, 0x01
    mov ebx, 0xCA
    int 0x80

native_syscall:
    push ebx
    push eax
    mov edx, dword [eax+21]
    mov ecx, dword [eax+17]
    mov ebx, dword [eax+13]
    mov eax, dword [eax+9]
    int 0x80
    pop ebx
    mov dword [ebx+5], eax
    pop ebx
    ret

native_syscall_wrap:
    push eax
    ; blockcounts used in this file must be <= 6, as that's what's specified in codegen.py.
    mov ecx, 5 ; ptr, alive, THIS, eax, ebx, ecx, edx
    call ath_alloc
    mov dword [eax], native_syscall
    mov byte [eax+4], 1
    pop ebx
    mov dword [ebx+25], eax
    ret

section .data
global ctor_ptr_native
ctor_ptr_native: dd 0

section .rodata
string_main: db "~ATH_MAIN", 0

section .init
    ; blockcounts used in this file must be <= 6, as that's what's specified in codegen.py.
    mov ecx, 6 ; ptr, alive, ..., EXPORT
    call ath_alloc
    mov dword [eax], native_syscall_wrap
    mov byte [eax+4], 1
    mov [ctor_ptr_native], eax

section .init.end
    ret
