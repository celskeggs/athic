
; we have a fixed limit of 255 data-words used in the largest loop.
; an object is 4 bytes of method ptr plus 1 byte of flags plus 4 bytes times the number of data-words.
; so we have one allocator list per possible such size
; for 0 data-words, 1 data-words, 2 data-words, ..., 255 data-words.
;
; we have a global direct address table for looking up the free lists
; ---------------------------------------------------------------------
; | head_ptr_0dw | head_ptr_1dw | head_ptr_2dw | ... | head_ptr_255dw |
; ---------------------------------------------------------------------
;     4 bytes        4 bytes        4 bytes                4 bytes
;
; the head_ptr points to the first element of a linked list of free elements.
; each element is the memory it provides.
;    the first four bytes are also a pointer to the next element in the free list,
;    when it's part of the free list (and so does not need its contents)

section .data

global max_data_words
max_data_words equ 255

allocator_table:
    times max_data_words+1 dd 0 ; all filled with zeroes

section .text

extern anonymous_mmap2

global ath_alloc
ath_alloc: ; takes data-word count in ecx, must preserve ebx, returns pointer in eax.
    ; data-word count cannot be larger than max_alloc_size
    mov eax, dword [allocator_table+4*ecx]
    cmp eax, 0
    je expand_allocation
post_expand_allocation:
    ; remove first element of the free list
    mov esi, dword [eax]
    mov dword [allocator_table+4*ecx], esi
    call ATH_ALLOC_TRACEPOINT
    ret

ATH_ALLOC_TRACEPOINT:
    ret

expand_allocation:
    ; here, the free list is empty, so we get more memory
    ; preserve ecx, [allocator_table+4*ecx] is the head of the free list, ecx is the data-word count
    push ecx
    lea ecx, [5+4*ecx] ; actual memory size of object
    push ecx
    push ebx
    call anonymous_mmap2 ; implicitly multiplies size by 4096 - so we have 4096 of the object.
    pop ebx
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

    pop ecx
    mov [allocator_table+4*ecx], eax ; put the new list head into the slot
    ; return new free list head in eax
    jmp post_expand_allocation
