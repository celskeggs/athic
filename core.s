
extern ath_alloc

section .text
extern main_ptr
global _start

_start:
    ; TODO: make sure that constructors get called
    mov eax, [main_ptr]
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
    mov eax, 5+4*5 ; ptr, alive, THIS, eax, ebx, ecx, edx
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
    mov eax, 5+4*6 ; ptr, alive, ..., EXPORT
    call ath_alloc
    mov dword [eax], native_syscall_wrap
    mov byte [eax+4], 1
    mov [ctor_ptr_native], eax
