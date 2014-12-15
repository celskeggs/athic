
; max_alloc_size is the maximum number of data-words used.
; an object is 4 bytes of method ptr plus 1 byte of flags plus 4 bytes times the number of data-words.
; so we have one allocator list per possible such size
; for 0 data-words, 1 data-words, 2 data-words, ..., max_alloc_size data-words.
;
; in reality, we don't want max_alloc_size, but instead the number of pages needed to store it.
; so we actually have max_alloc_size_in_pages, which is the number of 4096-byte pages needed.
;
; we have a global direct address table for looking up the free lists
; -------------------------------------------------------------------
; | head_ptr_0dw | head_ptr_1dw | head_ptr_2dw | ... | head_ptr_ndw |
; -------------------------------------------------------------------
;     4 bytes        4 bytes        4 bytes              4 bytes
;
; the head_ptr points to the first element of a linked list of free elements.
; each element is the memory it provides.
;    the first four bytes are also a pointer to the next element in the free list,
;    when it's part of the free list (and so does not need its contents)

section .data

; pointer to the array. head_ptr[max_alloc_size+1]
allocator_direct_table:
    dd 0

section .text

global _ath_alloc_init
extern max_alloc_size
extern max_alloc_size_in_pages
extern anonymous_mmap2

_ath_alloc_init: ; trashes all registers
    mov ecx, max_alloc_size_in_pages
    call anonymous_mmap2
    mov dword [allocator_direct_table], eax
    mov ecx, max_alloc_size+1
.adt_initialize_loop: ; set all head ptrs to zero.
    mov dword [4*ecx+eax-4], 0
    loop .adt_initialize_loop
    ret

global ath_alloc
ath_alloc: ; takes data-word count in ecx, must preserve ebx, returns pointer in eax.
    ; data-word count cannot be larger than max_alloc_size
    mov edx, dword [allocator_direct_table]
    mov eax, dword [edx+4*ecx]
    cmp eax, 0
    je expand_allocation
post_expand_allocation:
    ; remove first element of the free list
    mov esi, dword [eax]
    mov dword [edx+4*ecx], esi
    ret

expand_allocation:
    ; here, the free list is empty, so we get more memory
    ; preserve edx and ecx, [edx+4*ecx] is the head of the free list, ecx is the data-word count
    push ecx
    push edx
    lea ecx, [5+4*ecx] ; actual memory size of object
    push ecx
    call anonymous_mmap2 ; implicitly multiplies size by 4096 - so we have 4096 of the object.
    pop ecx
    mov edx, ecx

    shl edx, 12
    sub edx, ecx ; ecx*4095: the offset of the last entry in the allocated space

    mov dword [eax+edx], 0

.init_loop:
    lea esi, [eax+edx]
    sub edx, ecx
    mov dword [eax+edx], esi
    cmp edx, 0
    jne .init_loop

    pop edx
    pop ecx
    mov [edx+4*ecx], eax ; put the new list head into the slot
    ; return new free list head in eax
    jmp post_expand_allocation
