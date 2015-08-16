fid_write equ 7
fid_edx equ 4
fid_EXPORT equ 5
fid_DIE equ 8
fid_THIS equ 0
fid_eax equ 1
fid_ecx equ 3
fid_NULL equ 0
fid_ebx equ 2
fid_LOOKUP equ 6
bsize_0 equ 8
; IDs: {'write': 7, 'edx': 4, 'EXPORT': 5, 'DIE': 8, 'THIS': 0, 'eax': 1, 'ecx': 3, 'NULL': 0, 'ebx': 2, 'LOOKUP': 6}
global max_alloc_size
max_alloc_size equ 8
global max_alloc_size_in_pages
max_alloc_size_in_pages equ 1
section .text
extern ctor_ptr_native
extern ath_alloc
exec_0:
	push ebx
	mov ebx, eax
	mov byte [eax+4], 1
	mov eax, [ctor_ptr_native]
	mov dword [eax+5+4*fid_LOOKUP], string_write
	push eax
	call [eax]
	pop eax
	mov eax, dword [eax+5+4*fid_EXPORT]
	mov dword [ebx+5+4*fid_write], eax
	mov eax, dword [ebx+5+4*fid_write]
	push eax
	mov eax, 4
	pop ecx
	mov dword [ecx+5+4*fid_eax], eax
	mov eax, dword [ebx+5+4*fid_write]
	push eax
	mov eax, 1
	pop ecx
	mov dword [ecx+5+4*fid_ebx], eax
	mov eax, dword [ebx+5+4*fid_write]
	push eax
	mov eax, string_HELLO_20WORLD_a
	pop ecx
	mov dword [ecx+5+4*fid_ecx], eax
	mov eax, dword [ebx+5+4*fid_write]
	push eax
	mov eax, 12
	pop ecx
	mov dword [ecx+5+4*fid_edx], eax
	mov eax, dword [ebx+5+4*fid_write]
	push eax
	mov eax, dword [ebx+5+4*fid_NULL]
	mov ecx, eax
	pop eax
	mov dword [eax+5+4*fid_THIS], ecx
	call [eax]
	mov byte [ebx+4], 0
	pop ebx
	ret
section .rodata
string_write: db 119, 114, 105, 116, 101, 0 ; write
string_HELLO_20WORLD_a: db 72, 69, 76, 76, 79, 32, 87, 79, 82, 76, 68, 10, 0 ; HELLO WORLD\n
section .data
global ctor_ptr_allocator__test
ctor_ptr_allocator__test: dd 0
global main_ptr
main_ptr equ ctor_ptr_allocator__test
section .init
	mov ecx, bsize_0
	call ath_alloc
	mov dword [eax], exec_0
	mov byte [eax+4], 1
	mov [ctor_ptr_allocator__test], eax
