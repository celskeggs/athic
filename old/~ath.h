#ifndef TILDE_ATH_H
#define TILDE_ATH_H

#include <stdio.h>

enum AOT {
	A_NULL, A_THIS, A_INTEGER, A_CONST_STRING, A_DYN_STRING, A_OSTREAM, A_METHOD
};

typedef struct _AO_ (*mptr)(int acount, struct _AO_ bound, struct _AO_* args);

union AOU {
	int integer;
	const char *string;
	FILE *fptr;
	struct {
		struct _AO_ *bound;
		mptr ptr;
	} method;
};

typedef struct _AO_ {
	enum AOT type;
	union AOU value;
} AO;

extern void athmain();
extern AO deref(AO obj, const char *name);
extern AO invoke(int acount, AO obj, AO args[]);
extern AO import(const char *type, const char *name);
extern AO athint(int x);
extern AO athstr(const char *value);
extern AO athmethod(AO *bound, mptr method);
extern AO aththis();
extern AO athnull();

#endif
